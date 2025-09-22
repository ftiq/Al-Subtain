# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    sch_points_count = fields.Integer(
        string='عدد النقاط (Schmidt)',
        default=10,
        help='Number of points to be measured for Schmidt Hammer Test'
    )

    sch_a = fields.Float(
        string='المعامل A',
        digits=(16, 3),
        help='Coefficient A for converting R.N average to MPa (Simple: f = A*R + B)'
    )

    sch_b = fields.Float(
        string='المعامل B',
        digits=(16, 3),
        help='Coefficient B for converting R.N average to MPa (Simple: f = A*R + B)'
    )

    sch_manual_override = fields.Boolean(
        string='تمكين الإدخال اليدوي للمقاومة',
        default=False,
        help='عند التفعيل يمكنك إدخال مقاومة الانضغاط يدوياً لكل نقطة، وسيتم استخدام هذه القيم عند إنشاء العينة.'
    )

    schmidt_point_ids = fields.One2many(
        'project.task.schmidt.point',
        'task_id',
        string='نقاط Schmid'
    )

    show_schmidt_ui = fields.Boolean(
        string='عرض واجهة Schmid',
        compute='_compute_show_schmidt_ui',
        store=False
    )

    @api.depends('form_line_ids.product_id.product_tmpl_id', 'is_core_ui')
    def _compute_show_schmidt_ui(self):
        for task in self:

            show = False
            try:
                sample_tmpl = self.env.ref('appointment_products.product_schmidt_hammer_sample', raise_if_not_found=False)
                if sample_tmpl:
                    for line in task.form_line_ids:
                        if line.product_id and line.product_id.product_tmpl_id == sample_tmpl:
                            show = True
                            break
            except Exception:
                show = False
            task.show_schmidt_ui = show and not bool(getattr(task, 'is_core_ui', False))

    def action_fill_schmidt_points(self):
        """Create points P1..PN quickly based on sch_points_count if not already existing"""
        for task in self:
            existing_nos = set(task.schmidt_point_ids.mapped('point_no'))
            to_create = []
            for i in range(1, (task.sch_points_count or 0) + 1):
                if i not in existing_nos:
                    to_create.append({
                        'task_id': task.id,
                        'point_no': i,
                        'rn_avg': 0.0,
                    })
            if to_create:
                self.env['project.task.schmidt.point'].create(to_create)
        return True

    def action_generate_schmidt_sample_and_results(self):
        """Create Schmidt Hammer Test sample and results set and fill values from the task interface."""
        self.ensure_one()
        task = self

        sch_type = self.env.ref('appointment_products.schmidt_hammer_sample_type', raise_if_not_found=False)
        if not sch_type:
            raise ValidationError(_('Schmidt Hammer Test sample type not found. Please install the template first.'))

        has_schmidt = any(
            line.product_id and line.product_id.product_tmpl_id.sample_type_id == sch_type
            for line in task.form_line_ids
        )
        if not has_schmidt:
            raise ValidationError(_('No form line found for "Schmidt Hammer Test" sample in this task.'))


        sample_tmpl = self.env.ref('appointment_products.product_schmidt_hammer_sample', raise_if_not_found=False)
        if not sample_tmpl:
            raise ValidationError(_('Product "Schmidt Hammer Test" sample not found.'))


        existing_sample = self.env['lab.sample'].search([
            ('task_id', '=', task.id),
            ('product_id.product_tmpl_id', '=', sample_tmpl.id),
        ], limit=1)
        if existing_sample:
            raise ValidationError(_('تم إنشاء عينة مطرقة شميدت سابقاً لهذه المهمة: %s\nلا يمكن إنشاء عينة جديدة.') % (existing_sample.display_name,))

        sample_product = self.env['product.product'].search([('product_tmpl_id', '=', sample_tmpl.id)], limit=1)
        if not sample_product:
            raise ValidationError(_('Product (product.product) for "Schmidt Hammer Test" sample not found.'))


        sample = self.env['lab.sample'].create({
            'name': _('New'),
            'task_id': task.id,
            'product_id': sample_product.id,
            'quantity': 1.0,
        })


        template = self.env['lab.test.template'].search([('code', '=', 'SCHMIDT_HAMMER_TEST')], limit=1)
        if not template:
            raise ValidationError(_('Template "Schmidt Hammer Test" not found.'))

        points = task.schmidt_point_ids.sorted('point_no')
        if not points:
            raise ValidationError(_('No points found. Please fill the points first.'))

        rs = self.env['lab.result.set'].create({
            'sample_id': sample.id,
            'template_id': template.id,
            'number_of_samples': len(points),
        })


        for p in points:
            line_rn = rs.result_line_ids.filtered(lambda l: l.sample_no == p.point_no and l.criterion_id.code == 'SCH_RN')[:1]
            if line_rn:
                line_rn.value_numeric = float(p.rn_avg or 0.0)






        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الإنشاء'),
                'message': _('تم إنشاء عينة مطرقة شميدت ومجموعة النتائج بنجاح.'),
                'type': 'success',
                'sticky': False,
            }
        }


class ProjectTaskSchmidtPoint(models.Model):
    _name = 'project.task.schmidt.point'
    _description = 'Schmidt Hammer Points for Task'
    _order = 'task_id, point_no'

    task_id = fields.Many2one('project.task', string='المهمة', required=True, ondelete='cascade', index=True)
    point_no = fields.Integer(string='رقم النقطة', required=True, help='P1..PN')
    point_name = fields.Char(string='النقطة', compute='_compute_point_name', store=True)
    rn_avg = fields.Float(string='معدل رقم الارتداد R.N', digits=(16, 2))

    direction = fields.Selection([
        ('up', 'اعلى'),
        ('down', 'اسفل'),
        ('side', 'جانبي'),
    ], string='الاتجاه', default='up', help='اتجاه السطح عند القياس لكل نقطة')

    rn_readings_json = fields.Text(string='قراءات R.N (JSON)', help='حفظ آخر 10 قراءات مُدخلة لهذه النقطة كـ JSON للاطلاع.')


    comp_manual_mpa = fields.Float(string='مقاومة مدخلة (MPa)', digits=(16, 2))
    comp_est_mpa = fields.Float(string='مقاومة تقديرية (MPa)', digits=(16, 2), compute='_compute__compat_comp_est', store=False)

    manual_input_enabled = fields.Boolean(
        related='task_id.sch_manual_override',
        string='تمكين الإدخال اليدوي',
        store=False
    )

    _sql_constraints = [
        ('unique_point_per_task', 'unique(task_id, point_no)', 'Cannot repeat the same point number within the task.')
    ]

    @api.depends('point_no')
    def _compute_point_name(self):
        for rec in self:
            rec.point_name = f"P{rec.point_no}" if rec.point_no else ''

    def action_open_rn_readings_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'schmidt.readings.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_point_id': self.id,
            }
        }

    def _compute__compat_comp_est(self):
        """حقل توافق فقط لمنع مشاكل التحميل في العروض"""
        for rec in self:
            try:
                a = float(getattr(rec.task_id, 'sch_a', 0.0) or 0.0)
                b = float(getattr(rec.task_id, 'sch_b', 0.0) or 0.0)
                r = float(rec.rn_avg or 0.0)
                if a or b:
                    rec.comp_est_mpa = round(a * r + b, 2)
                else:
                    rec.comp_est_mpa = 0.0
            except Exception:
                rec.comp_est_mpa = 0.0

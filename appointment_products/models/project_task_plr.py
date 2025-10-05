# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import math

class ProjectTask(models.Model):
    _inherit = 'project.task'
    show_plr_ui = fields.Boolean(string='عرض واجهة الاستوائية', compute='_compute_show_plr_ui', store=False)
    plr_course_type = fields.Selection([
        ('surface', 'طبقة سطحية'),
        ('binder', 'طبقة رابطة'),
        ('base', 'طبقة أساس'),

    ], string='نوع الطبقة', default='surface', help='حدد نوع الطبقة لتطبيق حدود المعيار المناسبة.')
    
    plr_segment_ids = fields.One2many('project.task.plr.segment', 'task_id', string='مقاطع 300 م')
    plr_reading_step = fields.Integer(string='خطوة القراءة', default=50, help='المسافة بين القراءات الفردية (افتراضياً 50 م).')
    plr_window_length = fields.Integer(string='طول المقطع للحساب', default=300, help='طول النافذة المنزلقة لحساب المقطع (افتراضياً 300 م).')
    plr_reading_ids = fields.One2many('project.task.plr.reading', 'task_id', string='قراءات كل 50 م')

    plr_road_type = fields.Selection([
        ('main', 'شارع رئيسي'),
        ('secondary', 'شارع فرعي'),
    ], string='نوع الشارع')
    plr_street_length = fields.Float(string='طول الشارع')
    plr_street_name = fields.Char(string='اسم الشارع')

    @api.depends('form_line_ids.product_id.product_tmpl_id')
    def _compute_show_plr_ui(self):
        for task in self:
            show = False
            try:
                plr_tmpl = self.env.ref('appointment_products.product_plr_sample', raise_if_not_found=False)
                tmpl_ids = {plr_tmpl.id if plr_tmpl else 0}
                for line in task.form_line_ids:
                    if line.product_id and line.product_id.product_tmpl_id and line.product_id.product_tmpl_id.id in tmpl_ids:
                        show = True
                        break
            except Exception:
                show = False
            task.show_plr_ui = show
    def action_fill_plr_readings(self):
        """إنشاء صفوف قراءات كل 50 م (أو حسب خطوة القراءة) تلقائياً من 0 حتى طول الشارع"""
        for task in self:
            step = int(task.plr_reading_step or 50)
            length = float(task.plr_street_length or 0)
            if step <= 0:
                raise ValidationError(_('خطوة القراءة غير صحيحة.'))
            if length <= 0:
                raise ValidationError(_('فضلاً أدخل طول الشارع أولاً.'))

            count = int(math.ceil(length / step))
            existing_indexes = set(task.plr_reading_ids.mapped('reading_index'))
            to_create = []
            for i in range(1, count + 1):
                if i in existing_indexes:
                    continue
                start = (i - 1) * step
                end = min(i * step, int(length))
                to_create.append({
                    'task_id': task.id,
                    'reading_index': i,
                    'station_label': f"{start}-{end}",
                    'irr_459_count': 0,
                    'irr_610_count': 0,
                    'irr_gt10_count': 0,
                })
            if to_create:
                self.env['project.task.plr.reading'].create(to_create)
        return True

    def _format_station(self, meters):
        """صيغة 0+XXX للعرض."""
        m = int(meters or 0)
        return f"{m // 1000}+{m % 1000:03d}"

    def action_fill_plr_segments(self):
        """توليد مقاطع 300 م غير متداخلة + مقطع باقي، مع تسميات محطات بنمط 0+000-0+300."""
        for task in self:
            length = int(task.plr_street_length or 0)
            if length <= 0:
                raise ValidationError(_('فضلاً أدخل طول الشارع أولاً.'))


            task.plr_segment_ids.unlink()

            step = 50  
            window = 300
            seg_no = 1
            start = 0
            vals_list = []
            while start < length:
                end = min(start + window, length)
                vals_list.append({
                    'task_id': task.id,
                    'segment_no': seg_no,
                    'start_m': start,
                    'end_m': end,
                    'station_range': f"{self._format_station(start)}-{self._format_station(end)}",
                    'irr_459_count': 0,
                    'irr_610_count': 0,
                    'irr_gt10_count': 0,
                })
                seg_no += 1
                start += window
            if vals_list:
                self.env['project.task.plr.segment'].create(vals_list)
        return True
    def action_generate_plr_sample_and_results(self):
        """إنشاء عينة فحص الاستوائية ومجموعة النتائج وملء القيم من قراءات 50 م بنافذة 300 م."""
        self.ensure_one()
        task = self
        if not task.plr_segment_ids:
            task.action_fill_plr_segments()

        window = 300
        step = 50

        segments = []
        for seg in task.plr_segment_ids.sorted('segment_no'):
            seg_len = max(0, int(seg.end_m or 0) - int(seg.start_m or 0))
            ratio = (seg_len / float(window)) if window else 1.0
            segments.append({
                'no': seg.segment_no,
                'sum_459': float(seg.irr_459_count or 0),
                'sum_610': float(seg.irr_610_count or 0),
                'sum_gt10': float(seg.irr_gt10_count or 0),
                'ratio': ratio,
            })

        sample_tmpl = self.env.ref('appointment_products.product_plr_sample', raise_if_not_found=False)
        template = self.env['lab.test.template'].search([('code', '=', 'PAVEMENT_LONG_REG')], limit=1)

        if not sample_tmpl:
            raise ValidationError(_('تعذر العثور على منتج عينة فحص الاستوائية لنوع الطبقة المحدد.'))
        if not template:
            raise ValidationError(_('تعذر العثور على قالب فحص الاستوائية. يرجى تثبيت بيانات القالب أولاً.'))

        existing_sample = self.env['lab.sample'].search([
            ('task_id', '=', task.id),
            ('product_id.product_tmpl_id', '=', sample_tmpl.id),
        ], limit=1)
        if existing_sample:
            raise ValidationError(_('تم إنشاء عينة فحص الاستوائية سابقاً لهذه المهمة: %s') % (existing_sample.display_name,))

        sample_product = self.env['product.product'].search([('product_tmpl_id', '=', sample_tmpl.id)], limit=1)
        if not sample_product:
            raise ValidationError(_('تعذر العثور على (product.product) لعينة فحص الاستوائية.'))

        sample = self.env['lab.sample'].create({
            'name': _('New'),
            'task_id': task.id,
            'product_id': sample_product.id,
            'quantity': 1.0,
        })

        rs = self.env['lab.result.set'].create({
            'sample_id': sample.id,
            'template_id': template.id,
            'number_of_samples': len(segments),
        })

        for seg in segments:
            i = seg['no']
            line_459 = rs.result_line_ids.filtered(lambda l: l.sample_no == i and l.criterion_id.code == 'PLR_4_59')[:1]
            line_610 = rs.result_line_ids.filtered(lambda l: l.sample_no == i and l.criterion_id.code == 'PLR_6_10')[:1]
            line_gt10 = rs.result_line_ids.filtered(lambda l: l.sample_no == i and l.criterion_id.code == 'PLR_GT10')[:1]
            line_ratio = rs.result_line_ids.filtered(lambda l: l.sample_no == i and l.criterion_id.code == 'PLR_SEG_RATIO')[:1]
            if line_459:
                line_459.value_numeric = seg['sum_459']
            if line_610:
                line_610.value_numeric = seg['sum_610']
            if line_gt10:
                line_gt10.value_numeric = seg['sum_gt10']
            if line_ratio:
                line_ratio.value_numeric = seg.get('ratio', 1.0)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الإنشاء'),
                'message': _('تم إنشاء عينة فحص الاستوائية ومجموعة النتائج بنجاح.'),
                'type': 'success',
                'sticky': False,
            }
        }
class ProjectTaskPLRReading(models.Model):
    _name = 'project.task.plr.reading'
    _description = 'PLR 50m Readings for Task'

    task_id = fields.Many2one('project.task', string='المهمة', required=True, ondelete='cascade', index=True)
    reading_index = fields.Integer(string='رقم القراءة', required=True, help='الترتيب المتسلسل للقراءة (كل 50 م).')
    station_label = fields.Char(string='المحطة (كل خطوة)')

    irr_459_count = fields.Integer(string='4.0–5.9 مم', default=0)
    irr_610_count = fields.Integer(string='6.0–10.0 مم', default=0)
    irr_gt10_count = fields.Integer(string='> 10 مم', default=0)

    _sql_constraints = [
        ('unique_reading_per_task', 'unique(task_id, reading_index)', 'لا يمكن تكرار نفس رقم القراءة داخل نفس المهمة.'),
    ]

class ProjectTaskPLRSegment(models.Model):
    _name = 'project.task.plr.segment'
    _description = 'PLR 300m Segments for Task'
    _order = 'task_id, segment_no'

    task_id = fields.Many2one('project.task', string='المهمة', required=True, ondelete='cascade', index=True)
    segment_no = fields.Integer(string='رقم المقطع', required=True, help='P1..PN')
    start_m = fields.Integer(string='البداية (متر)', required=True, default=0)
    end_m = fields.Integer(string='النهاية (متر)', required=True, default=0)
    station_range = fields.Char(string='المحطة (كل 300 م)')

    irr_459_count = fields.Integer(string='عدد الانحرافات 4.0–5.9 مم', default=0)
    irr_610_count = fields.Integer(string='عدد الانحرافات 6.0–10.0 مم', default=0)
    irr_gt10_count = fields.Integer(string='عدد الانحرافات > 10 مم', default=0)

    _sql_constraints = [
        ('unique_segment_per_task', 'unique(task_id, segment_no)', 'لا يمكن تكرار نفس رقم المقطع داخل نفس المهمة.'),
    ]

    def action_open_input_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('إدخال بيانات المقطع'),
            'res_model': 'plr.segment.input.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_segment_id': self.id,
                'default_irr_459_count': self.irr_459_count,
                'default_irr_610_count': self.irr_610_count,
                'default_irr_gt10_count': self.irr_gt10_count,
            }
        }

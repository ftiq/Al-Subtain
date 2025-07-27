# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class LabTestFlowTemplate(models.Model):
    """قالب يحدد تسلسل مراحل الفحص وعدد العينات لكل مرحلة"""
    _name = 'lab.test.flow.template'
    _description = 'قالب خطة الفحص'
    _order = 'name'

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )

    name = fields.Char(string='اسم القالب', required=True)
    description = fields.Text(string='الوصف')
    
    allow_parallel_tests = fields.Boolean(
        string='تجاوز الترتيب',
        default=False,
        help='عند تفعيله، يتم تجاهل الترتيب المتبع ويمكن العمل على كل الفحوصات دفعة واحدة'
    )
    
    line_ids = fields.One2many(
        'lab.test.flow.template.line',
        'template_id',
        string='المراحل'
    )
    
    def action_view_details(self):
        """فتح نموذج التفاصيل الكاملة لقالب خطة الفحص"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lab.test.flow.template',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


class LabTestFlowTemplateLine(models.Model):
    """مرحلة داخل القالب"""
    _name = 'lab.test.flow.template.line'
    _description = 'مرحلة قالب خطة فحص'
    _order = 'sequence, id'

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )

    template_id = fields.Many2one('lab.test.flow.template', ondelete='cascade')
    sequence = fields.Integer(string='التسلسل', default=10)
    test_template_id = fields.Many2one('lab.test.template', string='قالب الفحص', required=True)
    sample_qty = fields.Integer(string='عدد العينات', default=1, required=True)


class LabTestFlow(models.Model):
    """سجل يمثل تنفيذ خطة فحص لمعيار/عينة معينة بتسلسل صارم"""
    _name = 'lab.test.flow'
    _description = 'خطة الفحص'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )

    name = fields.Char(string='الاسم', required=True, copy=False, default=lambda self: _('خطة فحص جديدة'))

    sample_id = fields.Many2one('lab.sample', string='العينة', required=True, ondelete='cascade')
    template_id = fields.Many2one('lab.test.flow.template', string='قالب الخطة', required=True, ondelete='restrict')

    current_step = fields.Integer(string='المرحلة الحالية', default=0, tracking=True)

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتملة')
    ], string='الحالة', default='draft', tracking=True)

    allow_parallel_tests = fields.Boolean(
        string='تجاوز الترتيب',
        related='template_id.allow_parallel_tests',
        store=True,
        readonly=True,
        help='عند تفعيله، يتم تجاهل الترتيب المتبع ويمكن العمل على كل الفحوصات دفعة واحدة'
    )

    line_ids = fields.One2many('lab.test.flow.line', 'flow_id', string='المراحل')

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id and not self.line_ids:
            self._apply_template_lines()

    def _apply_template_lines(self):
        """نسخ المراحل من القالب إلى الخطة (يستدعى من onchange و create)"""
        self.ensure_one()
        lines_vals = []
        for tmpl_line in self.template_id.line_ids:
            lines_vals.append((0, 0, {
                'sequence': tmpl_line.sequence,
                'test_template_id': tmpl_line.test_template_id.id,
                'sample_qty': tmpl_line.sample_qty,
            }))
        if lines_vals:
            self.line_ids = lines_vals

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if vals.get('name', _('خطة فحص جديدة')) in (_('خطة فحص جديدة'), _('New')):
                vals['name'] = self.env['ir.sequence'].next_by_code('lab.test.flow') or _('خطة فحص جديدة')
        
        records = super().create(vals_list)
        
        for record in records:
            if record.template_id and not record.line_ids:
                record._apply_template_lines()
        
        return records

    def action_next_step(self):
        self.ensure_one()
        lines = self.line_ids.sorted('sequence')
        if not lines:
            raise UserError(_('لا توجد مراحل محددة للخطة!'))

        if self.allow_parallel_tests and self.state == 'draft':
            self.state = 'in_progress'
            self.current_step = 1  
            
            for line in lines:
                line._launch_result_set()
            
            self.message_post(body=_('تم بدء كل المراحل معاً (وضع تجاوز الترتيب)'))
            
            return lines[0]._open_result_set()

        if self.current_step == 0:
            target_line = lines[0]
            return self._start_line(target_line)

        curr_line = lines.filtered(lambda l: l.sequence == self.current_step)
        if not curr_line:
            raise UserError(_('تعذر إيجاد المرحلة الحالية!'))
        curr_line = curr_line[0]

        if curr_line.state != 'done':
            raise UserError(_('المرحلة الحالية لم تنته بعد.'))


        next_line = lines.filtered(lambda l: l.sequence > self.current_step)[:1]
        if not next_line:
            self.state = 'completed'
            self.message_post(body=_('تم إنهاء جميع المراحل 🎉'))
            return
        return self._start_line(next_line)

    def _start_line(self, line):
        """إنشاء مجموعة نتائج لهذه المرحلة وفتحها"""
        self.ensure_one()
        line._launch_result_set()
        self.current_step = line.sequence
        self.state = 'in_progress'

        self.message_post(body=_('تم بدء المرحلة %s') % line.sequence)
        return line._open_result_set()


class LabTestFlowLine(models.Model):
    """سطر يمثل مرحلة واحدة داخل خطة فحص"""
    _name = 'lab.test.flow.line'
    _description = 'مرحلة خطة فحص'
    _order = 'sequence, id'

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )

    flow_id = fields.Many2one('lab.test.flow', string='الخطة', ondelete='cascade')
    sequence = fields.Integer(string='التسلسل', default=lambda self: self._get_default_sequence())
    
    _sql_constraints = [
        ('unique_sequence_per_flow', 'unique(flow_id, sequence)', 
         'Sequence must be unique per flow!'),
    ]
    
    def _get_default_sequence(self):
        """حساب التسلسل التلقائي التالي لتجنب التضارب"""
        if self.flow_id:
            max_sequence = self.search([
                ('flow_id', '=', self.flow_id.id)
            ], order='sequence desc', limit=1)
            if max_sequence:
                return max_sequence.sequence + 10
        return 10
    
    @api.constrains('sequence', 'flow_id')
    def _check_unique_sequence_per_flow(self):
        """Python constraint to ensure unique sequence per flow"""
        for line in self:
            if line.flow_id and line.sequence:
                duplicate = self.search([
                    ('id', '!=', line.id),
                    ('flow_id', '=', line.flow_id.id),
                    ('sequence', '=', line.sequence)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        _('Sequence %s is already used in flow %s. '
                          'Please choose a different sequence number.') % 
                        (line.sequence, line.flow_id.name)
                    )

    test_template_id = fields.Many2one('lab.test.template', string='قالب الفحص', required=True)
    sample_qty = fields.Integer(string='عدد العينات', default=1)
    
    @api.model
    def create(self, vals):
        """حساب التسلسل التلقائي عند الإنشاء"""
        if vals.get('flow_id') and 'sequence' not in vals:

            max_sequence = self.search([
                ('flow_id', '=', vals['flow_id'])
            ], order='sequence desc', limit=1)
            vals['sequence'] = (max_sequence.sequence + 10) if max_sequence else 10
        elif 'sequence' not in vals:
            vals['sequence'] = 10
            
        return super().create(vals)

    result_set_id = fields.Many2one('lab.result.set', string='مجموعة النتائج')
    state = fields.Selection([
        ('pending', 'بالانتظار'),
        ('running', 'قيد التنفيذ'),
        ('review', 'مراجعة'),
        ('done', 'منتهية')
    ], string='حالة المرحلة', default='pending', tracking=True)

    def _launch_result_set(self):
        self.ensure_one()
        if self.result_set_id:
            return

        rs = self.env['lab.result.set'].create({
            'name': f"{self.flow_id.name} / مرحلة {self.sequence}",
            'sample_id': self.flow_id.sample_id.id,
            'template_id': self.test_template_id.id,
            'number_of_samples': self.sample_qty,
            'state': 'draft',
        })
        rs.action_generate_result_lines()

        self.result_set_id = rs.id
        self.state = 'running'

    def _open_result_set(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lab.result.set',
            'view_mode': 'form',
            'res_id': self.result_set_id.id,
            'target': 'current',
        }

    def action_open_result_set(self):

        self.ensure_one()
        return self._open_result_set()

    def mark_done(self):
        self.write({'state': 'done'})
        if all(self.flow_id.line_ids.mapped(lambda l: l.state == 'done')):
            self.flow_id.state = 'completed'
            self.flow_id.message_post(body=_('اكتملت جميع المراحل')) 
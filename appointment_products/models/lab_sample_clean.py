# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


class LabSample(models.Model):
    _name = 'lab.sample'
    _description = _('Lab Sample')
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'
    _rec_name = 'name'

    
    name = fields.Char(
        string=_('Sample Number'),
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
        help=_('Unique reference number for the sample')
    )
    
    
    task_id = fields.Many2one(
        'project.task',
        string=_('Task'),
        required=False,
        ondelete='cascade',
        tracking=True,
        help=_('Task related to this sample')
    )
    
    product_id = fields.Many2one(
        'product.product',
        string=_('Product (Sample)'),
        required=True,
        domain=[('product_tmpl_id.is_sample_product', '=', True)],
        tracking=True,
        help=_('Product that represents the sample type')
    )
    
    lab_test_template_id = fields.Many2one(
        'lab.test.template',
        string=_('Test Template'),
        domain=[('state', '=', 'active')],
        tracking=True,
        help=_('Test template applied to this sample')
    )
    
    quality_check_id = fields.Many2one(
        'quality.check',
        string=_('Quality Check'),
        readonly=True,
        help=_('Quality check related to this sample')
    )
    
    
    collection_date = fields.Date(
        string=_('Collection Date'),
        default=fields.Date.today,
        tracking=True,
        help=_('Date when sample was collected from site')
    )
    
    received_date = fields.Datetime(
        string=_('Received Date'),
        default=fields.Datetime.now,
        tracking=True,
        help=_('Date and time when sample was received in laboratory')
    )
    
    quantity = fields.Float(
        string=_('Quantity'),
        default=1.0,
        required=True,
        digits=(12, 3),
        help=_('Quantity of received sample')
    )
    
    
    state = fields.Selection([
        ('draft', _('Draft')),
        ('received', _('Received')),
        ('testing', _('Testing')),
        ('completed', _('Completed')),
        ('rejected', _('Rejected'))
    ], string=_('State'), default='draft', tracking=True, required=True)
    
    overall_result = fields.Selection([
        ('pass', _('Pass')),
        ('fail', _('Fail')),
        ('pending', _('Pending'))
    ], string=_('Overall Result'), compute='_compute_overall_result', store=True)
    
    
    result_set_ids = fields.One2many(
        'lab.result.set',
        'sample_id',
        string=_('Dynamic Result Sets'),
        help=_('Result sets related to this sample')
    )
    
    test_flow_ids = fields.One2many(
        'lab.test.flow',
        'sample_id',
        string=_('Test Flows')
    )
    
    
    result_set_count = fields.Integer(
        string=_('Result Sets Count'),
        compute='_compute_result_set_count',
        store=True
    )
    
    total_criteria = fields.Integer(
        string=_('Total Criteria'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    completed_criteria = fields.Integer(
        string=_('Completed Criteria'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    criteria_progress_percentage = fields.Float(
        string=_('Criteria Progress Percentage'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    
    project_id = fields.Many2one(
        related='task_id.project_id',
        string=_('Project'),
        store=True,
        readonly=True
    )
    
    sale_order_id = fields.Many2one(
        related='task_id.sale_order_id',
        string=_('Sale Order'),
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        related='task_id.partner_id',
        string=_('Customer'),
        store=True,
        readonly=True
    )
    
    
    notes = fields.Html(
        string=_('Notes'),
        help=_('General notes about the sample')
    )
    
    
    color = fields.Integer(
        string=_('Color'),
        default=0,
        help=_('Color for kanban view')
    )
    
    priority = fields.Selection([
        ('0', _('Normal')),
        ('1', _('High'))
    ], string=_('Priority'), default='0')
    
    activity_state = fields.Selection([
        ('overdue', _('Overdue')),
        ('today', _('Today')),
        ('planned', _('Planned'))
    ], string=_('Activity State'), compute='_compute_activity_state')
    
    
    @api.depends('result_set_ids')
    def _compute_result_set_count(self):
        """حساب عدد مجموعات النتائج"""
        for sample in self:
            sample.result_set_count = len(sample.result_set_ids)
    
    @api.depends('result_set_ids.result_line_ids', 'result_set_ids.state')
    def _compute_criteria_progress(self):
        """حساب تقدم المعايير"""
        for sample in self:
            total = sum(len(rs.result_line_ids) for rs in sample.result_set_ids)
            completed = sum(
                len(rs.result_line_ids.filtered(lambda l: l.result_value))
                for rs in sample.result_set_ids
            )
            
            sample.total_criteria = total
            sample.completed_criteria = completed
            sample.criteria_progress_percentage = (
                (completed / total * 100) if total > 0 else 0
            )
    
    @api.depends('result_set_ids.overall_result')
    def _compute_overall_result(self):
        """حساب النتيجة العامة"""
        for sample in self:
            result_sets = sample.result_set_ids.filtered(lambda rs: rs.state == 'completed')
            if not result_sets:
                sample.overall_result = 'pending'
            elif any(rs.overall_result == 'fail' for rs in result_sets):
                sample.overall_result = 'fail'
            else:
                sample.overall_result = 'pass'
    
    @api.depends('activity_ids.date_deadline')
    def _compute_activity_state(self):
        """حساب حالة الأنشطة"""
        today = fields.Date.today()
        for sample in self:
            activities = sample.activity_ids.filtered(lambda a: not a.done)
            if not activities:
                sample.activity_state = 'planned'
            else:
                overdue = activities.filtered(lambda a: a.date_deadline < today)
                today_activities = activities.filtered(lambda a: a.date_deadline == today)
                
                if overdue:
                    sample.activity_state = 'overdue'
                elif today_activities:
                    sample.activity_state = 'today'
                else:
                    sample.activity_state = 'planned'

    
    @api.model
    def create(self, vals):
        """إنشاء العينة مع رقم متسلسل"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.sample') or _('New')
        return super().create(vals)
    
    
    
    def action_start_testing(self):
        """بدء الفحص - إنشاء مجموعة نتائج ديناميكية مع حماية من Race Conditions"""
        self.ensure_one()
        
        with self.env.cr.savepoint():
            if self.state == 'testing':
                if self.result_set_ids:
                    latest_result_set = self.result_set_ids.sorted('id', reverse=True)[0]
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Result Set'),
                        'res_model': 'lab.result.set',
                        'res_id': latest_result_set.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                else:
                    self.state = 'draft'
            
            active_result_sets = self.result_set_ids.filtered(lambda rs: rs.state in ('draft', 'in_progress'))
            active_flows = self.test_flow_ids.filtered(lambda tf: tf.state in ('draft', 'in_progress'))
            
            if active_result_sets or active_flows:
                if active_result_sets:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Result Set'),
                        'res_model': 'lab.result.set',
                        'res_id': active_result_sets[0].id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                elif active_flows:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Test Flow'),
                        'res_model': 'lab.test.flow',
                        'res_id': active_flows[0].id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
            
            flow_template = self.product_id.product_tmpl_id.test_flow_template_id

            if flow_template:
                flow = self.env['lab.test.flow'].create({
                    'name': _("Flow %s") % self.name,
                    'sample_id': self.id,
                    'template_id': flow_template.id,
                })

                action = flow.action_next_step()

                self.state = 'testing'

                self.message_post(body=_(
                    "🧪 <b>Test flow started</b><br/>"
                    "📋 Template: <em>%s</em>"
                ) % flow_template.name)

                return action or {
                    'type': 'ir.actions.act_window',
                    'name': _('Test Flow'),
                    'res_model': 'lab.test.flow',
                    'res_id': flow.id,
                    'view_mode': 'form',
                    'target': 'current',
                }

            if not self.lab_test_template_id:
                raise UserError(_('You must specify a test template or test flow first!'))

            result_set = self.env['lab.result.set'].create({
                'name': _("Results %s - %s") % (self.name, self.lab_test_template_id.name),
                'sample_id': self.id,
                'template_id': self.lab_test_template_id.id,
                'state': 'draft'
            })

            result_set.action_generate_result_lines()

            self.state = 'testing'

            self.message_post(body=_(
                "🧪 <b>Testing started</b><br/>"
                "📊 Result set: <em>%s</em><br/>"
                "🔬 Test template: <em>%s</em>"
            ) % (result_set.name, self.lab_test_template_id.name))

            return {
                'type': 'ir.actions.act_window',
                'name': _('Result Set'),
                'res_model': 'lab.result.set',
                'res_id': result_set.id,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_view_result_sets(self):
        """📊 عرض مجموعات النتائج"""
        if len(self.result_set_ids) == 1:

            return {
                'type': 'ir.actions.act_window',
                'name': _('Result Set'),
                'res_model': 'lab.result.set',
                'res_id': self.result_set_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            action = self.env.ref('appointment_products.action_lab_result_sets').read()[0]
            action['domain'] = [('sample_id', '=', self.id)]
            action['context'] = {'default_sample_id': self.id}
            return action
    
    def action_complete(self):
        """✅ إكمال العينة"""
        if not self.result_set_ids:
            raise UserError(_('No result sets for the sample!'))
        
        uncompleted_sets = self.result_set_ids.filtered(lambda rs: rs.state != 'completed')
        if uncompleted_sets:
            for result_set in uncompleted_sets:
                if result_set.state in ('draft', 'in_progress', 'calculated'):
                    result_set.action_calculate_results()

                try:
                    incomplete_lines = result_set.result_line_ids.filtered(
                        lambda l: not l._is_value_complete()
                    )
                    
                    if not incomplete_lines:
                        result_set.action_approve_results()
                        self.message_post(body=_(
                            "✅ تم إكمال مجموعة النتائج تلقائياً: %s"
                        ) % result_set.name)
                    else:

                        criteria_names = ', '.join(incomplete_lines.mapped('criterion_id.name'))
                        raise UserError(_(
                            'Cannot complete result set "%s"!\n'
                            'Missing data for criteria: %s\n\n'
                            'Please complete all required data before finishing the sample.'
                        ) % (result_set.name, criteria_names))
                        
                except Exception as e:
                    raise UserError(_(
                        'Cannot automatically complete result set "%s"!\n'
                        'Error: %s\n\n'
                        'Please manually complete the result set first.'
                    ) % (result_set.name, str(e)))
        
        still_uncompleted = self.result_set_ids.filtered(lambda rs: rs.state != 'completed')
        if still_uncompleted:
            raise UserError(_(
                'All result sets must be completed first!\n'
                'Uncompleted result sets: %s'
            ) % ', '.join(still_uncompleted.mapped('name')))
        
        self.write({'state': 'completed'})
        self.message_post(body=_("✅ <b>Sample completed successfully</b>"))
    
    def action_reject(self):
        """❌ رفض العينة"""
        self.write({'state': 'rejected'})
        self.message_post(body=_("❌ <b>Sample rejected</b>"))
    
    
    
    @api.constrains('quantity')
    def _check_quantity(self):
        """التحقق من الكمية"""
        for sample in self:
            if sample.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero!'))
    
    @api.constrains('collection_date', 'received_date')
    def _check_dates(self):
        """التحقق من التواريخ"""
        for sample in self:
            if sample.collection_date and sample.received_date:
                if sample.collection_date > sample.received_date.date():
                    raise ValidationError(_('Collection date cannot be after received date!'))
    


    test_count = fields.Integer(
        string=_('Test Count (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system - use result_set_count')
    )
    
    completed_tests = fields.Integer(
        string=_('Completed Tests (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system')
    )
    
    progress_percentage = fields.Float(
        string=_('Progress Percentage (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system - use criteria_progress_percentage')
    )
    
    @api.depends('result_set_ids', 'result_set_ids.state')
    def _compute_legacy_compat(self):
        """حساب الحقول للتوافق مع النظام القديم"""
        for sample in self:
            total_sets = len(sample.result_set_ids)
            completed_sets = len(sample.result_set_ids.filtered(lambda rs: rs.state == 'completed'))
            
            sample.test_count = total_sets
            sample.completed_tests = completed_sets
            sample.progress_percentage = (
                (completed_sets / total_sets * 100) if total_sets > 0 else 0
            ) 
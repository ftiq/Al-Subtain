# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


STATE_TO_QC_STATUS = {
    'draft': 'pending',
    'received': 'pending',
    'testing': 'in_progress',
    'completed': 'completed',
    'rejected': 'failed',
}

QC_TO_STATE_STATUS = {v: k for k, v in STATE_TO_QC_STATUS.items()}


class LabSample(models.Model):
    _name = 'lab.sample'
    _description = _('Lab Sample')
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'
    _rec_name = 'name'

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )
    

    _sql_constraints = [
        ('positive_quantity', 'check(quantity > 0)', 'الكمية يجب أن تكون أكبر من الصفر!'),
        ('unique_name', 'unique(name)', 'رقم العينة يجب أن يكون فريداً!'),
    ]

    
    name = fields.Char(
        string=_('Sample Number'),
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
        help=_('Unique reference number for the sample'),
        index=True 
    )
    
    
    task_id = fields.Many2one(
        'project.task',
        string=_('Task'),
        required=False,
        ondelete='cascade',
        tracking=True,
        help=_('Task related to this sample'),
        index=True 
    )
    
    product_id = fields.Many2one(
        'product.product',
        string=_('Product (Sample)'),
        required=True,
        domain=[('product_tmpl_id.is_sample_product', '=', True)],
        tracking=True,
        help=_('Product that represents the sample type'),
        index=True 
    )
    

    sample_subtype_id = fields.Many2one(
        'lab.sample.subtype',
        string=_('Sample Subtype'),
        tracking=True,
        help=_('Specific subtype of the sample (e.g. Type A, Type B, Type C)'),
        index=True
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
    ], string=_('State'), default='draft', tracking=True, required=True, index=True)  # فهرس لفلترة الحالات
    
    overall_result = fields.Selection([
        ('pass', _('Pass')),
        ('fail', _('Fail')),
        ('pending', _('Pending'))
    ], string=_('Overall Result'), compute='_compute_overall_result', store=True, tracking=True)
    
    
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
        

        if vals.get('task_id') and not vals.get('sample_subtype_id'):
            task = self.env['project.task'].browse(vals.get('task_id'))
            product_id = vals.get('product_id')
            
            if task and product_id:

                form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product_id)
                if form_line and form_line.sample_subtype_id:
                    vals['sample_subtype_id'] = form_line.sample_subtype_id.id
                    
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



    def write(self, vals):
        """تحديث حالة فحص الجودة عند تغيير حالة العينة والعكس"""
        

        if (vals.get('task_id') or vals.get('product_id')) and not vals.get('sample_subtype_id'):
            for rec in self:
                task_id = vals.get('task_id', rec.task_id.id)
                product_id = vals.get('product_id', rec.product_id.id)
                
                if task_id and product_id:
                    task = self.env['project.task'].browse(task_id)

                    form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product_id)
                    if form_line and form_line.sample_subtype_id:
                        vals['sample_subtype_id'] = form_line.sample_subtype_id.id
        
        res = super().write(vals)

        if 'state' in vals:
            target_qc_status = STATE_TO_QC_STATUS.get(vals['state'])
            for rec in self.filtered(lambda s: s.quality_check_id):
                if target_qc_status and rec.quality_check_id.lab_test_status != target_qc_status:
                    rec.quality_check_id.sudo().write({'lab_test_status': target_qc_status})

        return res
    
    
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
        """حساب الحقول"""
        for sample in self:
            total_sets = len(sample.result_set_ids)
            completed_sets = len(sample.result_set_ids.filtered(lambda rs: rs.state == 'completed'))
            
            sample.test_count = total_sets
            sample.completed_tests = completed_sets
            sample.progress_percentage = (
                (completed_sets / total_sets * 100) if total_sets > 0 else 0
            ) 

    cube_ids = fields.One2many('lab.sample.cube', 'sample_id', string='المكعبات')

    def action_generate_concrete_cubes(self, total_volume_m3, truck_ids):
        """يُنشئ عينات ومكعبات وفق خطة نوع العينة وحجم الصبّ"""
        self.ensure_one()
        sample_type = self.product_id.product_tmpl_id.sample_type_id or self.env.ref('appointment_products.lab_sample_type_concrete')
        if not sample_type:
            raise UserError(_('يجب تحديد نوع عينة يملك خطة أخذ عينات!'))


        if self.cube_ids:
            self.cube_ids.unlink()


        first_stage_sets = sample_type.sets_first_stage
        repeat = sample_type.repeat_volume_m3
        extra_sets = 0
        if total_volume_m3 > sample_type.initial_volume_m3:
            extra_sets = int(((total_volume_m3 - sample_type.initial_volume_m3) + repeat - 1) / repeat)
        total_sets = first_stage_sets + extra_sets


        cube_per_set = sample_type.cubes_per_set
        extra_cubes = sample_type.extra_cubes_per_set
        age_days_list = [int(a.strip()) for a in (sample_type.age_days_list or '7,28').split(',') if a.strip()]

        trucks = self.env['lab.concrete.truck'].browse(truck_ids)
        truck_cycle = list(trucks) if trucks else []
        truck_idx = 0

        for s in range(1, total_sets + 1):

            for i in range(1, cube_per_set + 1):
                truck = False
                if truck_cycle:
                    truck = truck_cycle[truck_idx % len(truck_cycle)]

                    truck_idx += 1
                self.env['lab.sample.cube'].create({
                    'sample_id': self.id,
                    'set_no': s,
                    'cube_index': i,
                    'cube_type': 'core',
                    'age_days': 28,
                    'truck_id': truck.id if truck else False,
                })

            for j in range(1, extra_cubes + 1):
                age_val = age_days_list[j-1] if j-1 < len(age_days_list) else 28
                self.env['lab.sample.cube'].create({
                    'sample_id': self.id,
                    'set_no': s,
                    'cube_index': cube_per_set + j,
                    'cube_type': 'extra',
                    'age_days': age_val,
                    'truck_id': False,
                })

        self.message_post(body=_('تم إنشاء %s عينة فرعية بـ %s مكعب لكلٍّ منها وفق الخطة.', total_sets, cube_per_set + extra_cubes)) 

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """تحديث مجال النوع الفرعي عند تغيير المنتج"""
        if self.product_id:
            product_code = self.product_id.default_code or ''
            if 'MASONRY' in product_code.upper() or 'BRICK' in product_code.upper():
                masonry_type = self.env['lab.sample.type'].search([('code', '=', 'MASONRY')], limit=1)
                if masonry_type:
                    return {'domain': {'sample_subtype_id': [('sample_type_id', '=', masonry_type.id)]}}
            
        return {'domain': {'sample_subtype_id': []}}
    
    @api.onchange('sample_subtype_id')
    def _onchange_sample_subtype_id(self):
        """تحديث قالب الفحص المناسب عند تغيير النوع الفرعي"""
        if self.sample_subtype_id and self.sample_subtype_id.sample_type_id.code == 'MASONRY':
            efflorescence_template = self.env['lab.test.template'].search([('code', '=', 'BRICK_EFFLOR')], limit=1)
            if efflorescence_template:
                self.lab_test_template_id = efflorescence_template.id 

    @api.onchange('task_id', 'product_id')
    def _onchange_task_product(self):
        """تحديث النوع الفرعي للعينة عند تغيير المهمة أو المنتج"""
        if self.task_id and self.product_id and not self.sample_subtype_id:
            form_line = self.task_id.form_line_ids.filtered(lambda l: l.product_id.id == self.product_id.id)
            if form_line and form_line.sample_subtype_id:
                self.sample_subtype_id = form_line.sample_subtype_id 
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
        ('draft', 'مسودة'),
        ('received', 'مستلمة'),
        ('testing', 'قيد الفحص'),
        ('completed', 'مكتملة'),
        ('rejected', 'مرفوضة')
    ], string='الحالة', default='draft', tracking=True, required=True, index=True)  # فهرس لفلترة الحالات
    
    overall_result = fields.Selection([
        ('pass', 'ناجح'),
        ('fail', 'فاشل'),
        ('pending', 'قيد الانتظار')
    ], string='النتيجة النهائية', compute='_compute_overall_result', store=True, tracking=True)
    
    
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
    
    lab_code = fields.Char(
        string=_('الرمز المختبري'),
        tracking=True,
        help=_('الرمز المختبري المخصص للعينة'),
        index=True
    )
    
    field_serial = fields.Char(
        string=_('الرمز الحقلي'),
        tracking=True,
        help=_('الرقم التسلسلي الحقلي المخصص للعينة'),
        index=True
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
    
    @api.depends('activity_ids.state')
    def _compute_activity_state(self):
        """حساب حالة النشاط"""

        if not self:
            return
        for record in self:
            if not record.activity_ids:
                record.activity_state = False
            else:

                latest_activity = record.activity_ids.sorted('date_deadline')[0]
                if latest_activity.date_deadline:
                    from datetime import date
                    today = date.today()
                    if latest_activity.date_deadline < today:
                        record.activity_state = 'overdue'
                    elif latest_activity.date_deadline == today:
                        record.activity_state = 'today'
                    else:
                        record.activity_state = 'planned'
                else:
                    record.activity_state = 'planned'

    testers_with_states = fields.Html(
        string='المكلفون مع الحالات',
        compute='_compute_testers_with_states',
        help='عرض المكلفين مع حالة كل نتيجة',
        sanitize=False
    )
    
    @api.depends('result_set_ids.testers_ids', 'result_set_ids.state')
    def _compute_testers_with_states(self):
        """حساب المكلفين مع حالاتهم - يجمع حالات المكلف الواحد في باج واحد"""

        if not self:
            return
        for sample in self:
            testers_dict = {}
            
            for result_set in sample.result_set_ids:
                if result_set.testers_ids:
                    state_color = {
                        'draft': 'secondary',
                        'in_progress': 'warning', 
                        'calculated': 'info',
                        'review': 'primary',
                        'approved': 'success',
                        'completed': 'success',
                        'cancelled': 'danger'
                    }.get(result_set.state, 'secondary')
                    
                    state_text = {
                        'draft': 'مسودة',
                        'received': 'مستلمة',
                        'testing': 'قيد الفحص',
                        'completed': 'مكتملة',
                        'rejected': 'مرفوضة',
                        'in_progress': 'قيد العمل',
                        'calculated': 'محسوبة', 
                        'review': 'مراجعة',
                        'approved': 'معتمد',
                        'cancelled': 'ملغي'
                    }.get(result_set.state, 'غير محدد')
                    
                    template_name = result_set.template_id.name[:12] if result_set.template_id else 'نتيجة'
                    
                    for tester in result_set.testers_ids:
                        if tester.id not in testers_dict:
                            testers_dict[tester.id] = {
                                'name': tester.name,
                                'states': [],
                                'colors': [],
                                'templates': []
                            }
                        
                        testers_dict[tester.id]['states'].append(state_text)
                        testers_dict[tester.id]['colors'].append(state_color)
                        testers_dict[tester.id]['templates'].append(template_name)
            
            if testers_dict:
                html_content = '<div class="d-flex flex-wrap gap-1">'
                tester_count = 0
                
                for tester_id, tester_data in testers_dict.items():
                    if tester_count >= 4:  
                        break
                        
                    priority_colors = ['danger', 'warning', 'primary', 'info', 'success', 'secondary']
                    badge_color = 'secondary'
                    for color in priority_colors:
                        if color in tester_data['colors']:
                            badge_color = color
                            break
                    
                    unique_states = list(dict.fromkeys(tester_data['states']))  
                    states_text = ', '.join(unique_states[:2])
                    if len(unique_states) > 2:
                        states_text += f' +{len(unique_states) - 2}'
                    
                    unique_templates = list(dict.fromkeys(tester_data['templates']))[:3]
                    tooltip = f"{tester_data['name']} - {', '.join(unique_templates)}"
                    
                    html_content += f'<span class="badge bg-{badge_color} text-white small" title="{tooltip}">'
                    html_content += f'<i class="fa fa-user me-1"></i>{tester_data["name"]} ({states_text})'
                    html_content += '</span>'
                    
                    tester_count += 1
                
                if len(testers_dict) > 4:
                    html_content += f'<span class="badge bg-secondary text-white small">+{len(testers_dict) - 4} آخرين</span>'
                    
                html_content += '</div>'
                sample.testers_with_states = html_content
            else:
                sample.testers_with_states = '<small class="text-muted"><i class="fa fa-user-o me-1"></i>غير معيّن</small>'
    
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
            # احتساب النتيجة العامة بناءً على المجموعات المكتملة أو المعتمدة
            result_sets = sample.result_set_ids.filtered(lambda rs: rs.state in ('completed', 'approved'))
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
        
        if vals.get('quality_check_id') and not (vals.get('lab_code') or vals.get('field_serial')):
            quality_check = self.env['quality.check'].browse(vals.get('quality_check_id'))
            if quality_check and quality_check.picking_id:
                move_line = quality_check.picking_id.move_line_ids.filtered(
                    lambda ml: ml.product_id.id == vals.get('product_id')
                )
                if move_line:
                    move_line = move_line[0] if move_line else False
                    if move_line and move_line.field_code and not vals.get('lab_code'):
                        vals['lab_code'] = move_line.field_code
                    if move_line and move_line.field_serial and not vals.get('field_serial'):
                        vals['field_serial'] = move_line.field_serial
        
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
            

            forced_template_id = self.env.context.get('force_flow_template_id')
            if forced_template_id:
                flow_template = self.env['lab.test.flow.template'].browse(forced_template_id)
            else:
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
                'name': f'نتيجة {self.name}',
                'res_model': 'lab.result.set',
                'res_id': self.result_set_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'sample_id': self.id,
                    'sample_name': self.name,
                    'breadcrumb_parent_action': 'appointment_products.action_lab_result_sets_sample_filtered',
                },
            }
        else:
            action = self.env.ref('appointment_products.action_lab_result_sets_sample_filtered').read()[0]
            action['domain'] = [('sample_id', '=', self.id)]
            action['name'] = f'نتائج العينة: {self.name}'
            action['context'] = {
                'default_sample_id': self.id,
                'sample_name': self.name,
                'active_id': self.id,
                'create': True,
            }
            return action
    
    def action_complete(self):
        """✅ إكمال العينة"""
        if not self.result_set_ids:
            raise UserError(_('لا توجد مجموعات نتائج للعينة!'))
        
        unapproved_names = [rs.name for rs in self.result_set_ids if rs.state != 'approved']
        if unapproved_names:
            raise UserError(_(
                'لا يمكن إكمال العينة حتى يتم اعتماد جميع مجموعات النتائج!\n'
                'المجموعات غير المعتمدة: %s\n\n'
                'يرجى اعتماد جميع النتائج أولاً قبل إكمال العينة.'
            ) % ', '.join(unapproved_names))
        
        self.write({'state': 'completed'})
        self.message_post(body=_("✅ <b>تم إكمال العينة بنجاح</b>"))
    
    def action_reject(self):
        """رفض العينة"""
        self.write({'state': 'rejected'})
        self.message_post(body=_("<b>Sample rejected</b>"))



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
                (completed_sets / total_sets) if total_sets > 0 else 0
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

        for s in range(1, total_sets + 1):

            for i in range(1, cube_per_set + 1):
                self.env['lab.sample.cube'].create({
                    'sample_id': self.id,
                    'set_no': s,
                    'cube_index': i,
                    'cube_type': 'core',
                    'age_days': 28,
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
        if self.sample_subtype_id:
            if self.sample_subtype_id.sample_type_id.code == 'MASONRY':
                efflorescence_template = self.env['lab.test.template'].search([('code', '=', 'BRICK_EFFLOR')], limit=1)
                if efflorescence_template:
                    self.lab_test_template_id = efflorescence_template.id
            elif self.sample_subtype_id.default_test_template_id:
                self.lab_test_template_id = self.sample_subtype_id.default_test_template_id.id
    


    @api.onchange('task_id', 'product_id')
    def _onchange_task_product(self):
        """تحديث النوع الفرعي للعينة عند تغيير المهمة أو المنتج"""
        if self.task_id and self.product_id and not self.sample_subtype_id:
            form_line = self.task_id.form_line_ids.filtered(lambda l: l.product_id.id == self.product_id.id)
            if form_line and form_line.sample_subtype_id:
                self.sample_subtype_id = form_line.sample_subtype_id


    is_assigned_to_me = fields.Boolean(
        string='مكلف ',
        compute='_compute_is_assigned_to_me',
        search='_search_is_assigned_to_me',
        help='يحدد ما إذا كان المستخدم الحالي مكلف بأي فحص في هذه العينة'
    )
    

    assigned_emails = fields.Char(
        string='إيميلات المكلفين',
        compute='_compute_assigned_users',
        help='إيميلات جميع الفنيين المكلفين - للاستخدام في قوالب الإيميل'
    )
    
    assigned_names = fields.Char(
        string='أسماء المكلفين',
        compute='_compute_assigned_users',
        help='أسماء جميع الفنيين المكلفين - للاستخدام في قوالب الإيميل'
    )
    
    @api.depends('result_set_ids.testers_ids')
    def _compute_assigned_users(self):
        """حساب إيميلات وأسماء جميع الفنيين المكلفين"""
        for sample in self:
            assigned_users = sample.result_set_ids.mapped('testers_ids')
            
            emails = assigned_users.mapped('email')
            sample.assigned_emails = ','.join(filter(None, emails))
            
            names = assigned_users.mapped('name')
            sample.assigned_names = ' و '.join(filter(None, names))
    
    @api.depends('result_set_ids.testers_ids')
    def _compute_is_assigned_to_me(self):
        """حساب ما إذا كان المستخدم الحالي مكلف بأي فحص في هذه العينة"""
        for sample in self:
            assigned_users = sample.result_set_ids.mapped('testers_ids')
            sample.is_assigned_to_me = self.env.user in assigned_users
    
    def _search_is_assigned_to_me(self, operator, value):
        """تمكين البحث على حقل is_assigned_to_me"""
        if operator == '=' and value:
            return [('result_set_ids.testers_ids', 'in', [self.env.uid])]
        elif operator == '=' and not value:
            return [('result_set_ids.testers_ids', 'not in', [self.env.uid])]
        elif operator == '!=' and value:
            return [('result_set_ids.testers_ids', 'not in', [self.env.uid])]
        elif operator == '!=' and not value:
            return [('result_set_ids.testers_ids', 'in', [self.env.uid])]
        else:
            return []
    
    all_results_approved = fields.Boolean(
        string='جميع النتائج معتمدة',
        compute='_compute_all_results_approved',
        help='حقل محسوب يبين ما إذا كانت جميع مجموعات النتائج معتمدة'
    )
    
    @api.depends('result_set_ids.state', 'test_flow_ids.line_ids.result_set_id.state')
    def _compute_all_results_approved(self):
        """حساب ما إذا كانت جميع النتائج معتمدة"""
        for sample in self:

            direct_result_sets = sample.result_set_ids
            flow_result_sets = sample.test_flow_ids.mapped('line_ids.result_set_id')
            all_result_sets = direct_result_sets + flow_result_sets
            
            if not all_result_sets:
                sample.all_results_approved = False
            else:
                sample.all_results_approved = all(
                    rs.state in ('approved', 'completed') for rs in all_result_sets
                )
    
    def action_export_to_excel(self):
        """📊 فتح معالج تصدير Excel للعينة"""
        self.ensure_one()
        
        if not self.result_set_ids:
            raise UserError(_('لا توجد مجموعات نتائج لتصديرها لهذه العينة.'))
        
        # إنشاء وعرض معالج التصدير
        wizard = self.env['lab.sample.excel.export.wizard'].create({
            'sample_id': self.id,
            'include_summary': True,
        })
        
        return {
            'name': _('تصدير نتائج العينة إلى Excel'),
            'type': 'ir.actions.act_window',
            'res_model': 'lab.sample.excel.export.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
 
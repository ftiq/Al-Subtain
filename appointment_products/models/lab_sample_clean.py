# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


STATE_TO_QC_STATUS = {
    'draft': 'pending',
    'received': 'pending',
    'testing': 'in_progress',
    'completed': 'completed',
    'approved': 'completed',
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
        ('approved', 'مصادق علية'),
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
    

    reference_general_limit = fields.Float(
        related='task_id.reference_general_limit',
        string='المعدل',
        readonly=True,
        store=False,
        help='المعيار العام للمقارنة من المهمة المرتبطة'
    )

    core_compaction_ratio = fields.Float(
        string='نسبة الحدل (%)',
        help='النسبة المرجعية المطلوبة للحدل لعينة الكور الخرساني (٪)'
    )
    
    concrete_sample_type_id = fields.Many2one(
        related='task_id.concrete_sample_type_id',
        string='نوع عينة الخرسانة',
        store=True,
        readonly=True,
        help='نوع العينة للخرسانة (أبنية، أساسات، جسور)'
    )
    
    is_concrete_sample = fields.Boolean(
        string='عينة خرسانية',
        compute='_compute_is_concrete_sample',
        store=True,
        help='هل هذه عينة خرسانية؟'
    )

    is_core_ui = fields.Boolean(
        string='Is Core UI',
        compute='_compute_is_core_ui',
        store=False
    )
    
    bitumen_type = fields.Char(
        string='نوع القير',
        compute='_compute_bitumen_type',
        store=False,
        help='يظهر نوع القير (أساس أو تسطيح) إذا كان المنتج قير'
    )
    
    bitumen_results_summary = fields.Html(
        string='ملخص نتائج القير',
        compute='_compute_bitumen_results_summary',
        store=False,
        help='عرض جدولي لجميع نتائج متوسطات القير والمستويات المطبقة'
    )
    
    bitumen_comparison_level = fields.Selection(
        selection=[
            ('1', 'المستوى الأول'),
            ('2', 'المستوى الثاني'),
            ('3', 'المستوى الثالث'),
            ('4', 'المستوى الرابع'),
        ],
        string='مستوى المقارنة (قير)',
        help='اختر مستوى المقارنة المطلوب تطبيقه على جميع فحوصات القير لهذه العينة.\nلقير التسطيح: 4 مستويات.\nلقير الأساس: 3 مستويات (يتم تجاهل الرابع).'
    )

    @api.onchange('bitumen_type')
    def _onchange_bitumen_type_set_default_level(self):
        for rec in self:
            if not rec.bitumen_type:
                rec.bitumen_comparison_level = False
            else:
                # اضبط افتراضياً على المستوى الأول إن لم يحدد
                if not rec.bitumen_comparison_level:
                    rec.bitumen_comparison_level = '1'
                # منع اختيار المستوى الرابع لقير الأساس
                if rec.bitumen_type == 'قير أساس' and rec.bitumen_comparison_level == '4':
                    rec.bitumen_comparison_level = '3'

    @api.onchange('bitumen_comparison_level')
    def _onchange_bitumen_comparison_level(self):
        for rec in self:
            if rec.bitumen_type == 'قير أساس' and rec.bitumen_comparison_level == '4':
                rec.bitumen_comparison_level = '3'
                return {
                    'warning': {
                        'title': _('تنبيه'),
                        'message': _('لقير الأساس توجد 3 مستويات فقط. تم تعيين المستوى الثالث تلقائياً.'),
                    }
                }
    
    
    notes = fields.Html(
        string=_('Notes'),
        help=_('General notes about the sample')
    )

    exec_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    exec_signer_id = fields.Many2one(
        'res.partner',
        string='اختيار المسؤول',
        domain=[('is_company', '=', False)]
    )
    exec_signer_name = fields.Char(
        string='اسم المسؤول',
        related='exec_signer_id.name',
        store=True,
        readonly=True
    )
    exec_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_exec_is_signed',
        store=True,
        readonly=True
    )
    exec_signed_at = fields.Datetime(
        string='تاريخ توقيع ممثل الجهة المنفذة',
        readonly=True
    )
    exec_signature_locked = fields.Boolean(
        string='قفل التوقيع (منفذ)',
        compute='_compute_signature_locks',
        readonly=True
    )

    super_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    super_signer_id = fields.Many2one(
        'res.partner',
        string='اختيار المسؤول',
        domain=[('is_company', '=', False)]
    )
    super_signer_name = fields.Char(
        string='اسم المسؤول',
        related='super_signer_id.name',
        store=True,
        readonly=True
    )
    super_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_super_is_signed',
        store=True,
        readonly=True
    )
    super_signed_at = fields.Datetime(
        string='تاريخ توقيع ممثل الجهة المشرفة',
        readonly=True
    )
    super_signature_locked = fields.Boolean(
        string='قفل التوقيع (مشرف)',
        compute='_compute_signature_locks',
        readonly=True
    )

    company_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    company_signer_id = fields.Many2one(
        'res.users',
        string='اختيار المدير التنفيذي'
    )
    company_signer_name = fields.Char(
        string='اسم المدير التنفيذي',
        related='company_signer_id.name',
        store=True,
        readonly=True
    )
    company_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_company_is_signed',
        store=True,
        readonly=True
    )
    company_signed_at = fields.Datetime(
        string='تاريخ توقيع المدير التنفيذي',
        readonly=True
    )
    company_signature_locked = fields.Boolean(
        string='قفل التوقيع (المدير التنفيذي)',
        compute='_compute_signature_locks',
        readonly=True
    )
    
    # Field to check if all three signatures are present
    all_signatures_signed = fields.Boolean(
        string='جميع التوقيعات مكتملة',
        compute='_compute_all_signatures_signed',
        store=True,
        help='يتم تفعيل هذا الحقل عندما تكون جميع التوقيعات الثلاثة موجودة'
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


        now = fields.Datetime.now()
        if vals.get('exec_signature'):
            vals['exec_signed_at'] = now
        if vals.get('super_signature'):
            vals['super_signed_at'] = now
        if vals.get('company_signature'):
            vals['company_signed_at'] = now
        

        try:
            if vals.get('task_id') and 'core_compaction_ratio' not in vals:
                task = self.env['project.task'].browse(vals['task_id'])
                if task and task.core_compaction_ratio:
                    vals['core_compaction_ratio'] = task.core_compaction_ratio
        except Exception:
            pass

        return super().create(vals)

    @api.depends('task_id.stock_receipt_id.concrete_sample_type_id', 'task_id.main_sample_is_concrete_core', 'task_id.is_concrete_core_type_selected', 'concrete_sample_type_id')
    def _compute_is_core_ui(self):
        for rec in self:
            is_core = False
            try:
                code = (rec.task_id.stock_receipt_id.concrete_sample_type_id.code or '').upper() if rec.task_id and rec.task_id.stock_receipt_id and rec.task_id.stock_receipt_id.concrete_sample_type_id else ''
                if code == 'CONCRETE_CORE':
                    is_core = True
                if not is_core and getattr(rec.task_id, 'main_sample_is_concrete_core', False):
                    is_core = True
                if not is_core and getattr(rec.task_id, 'is_concrete_core_type_selected', False):
                    is_core = True
                if not is_core and rec.concrete_sample_type_id and (rec.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                    is_core = True
            except Exception:
                is_core = False
            rec.is_core_ui = is_core
    
    
    
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
                    "<b>Test flow started</b><br/>"
                    "Template: <em>%s</em>"
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

            # عند عدم استخدام خطة الفحص (Flow)، ننشئ عدة مجموعات نتائج بحسب عدد المجموعات في المهمة
            try:
                total_count = int(self.task_id.total_samples_count or 1)
            except Exception:
                total_count = 1
            total_count = max(1, total_count)

            created_sets = self.env['lab.result.set']
            for group_no in range(1, total_count + 1):
                rs = self.env['lab.result.set'].create({
                    'name': _("Results %s - %s (مجموعة %s)") % (self.name, self.lab_test_template_id.name, group_no),
                    'sample_id': self.id,
                    'template_id': self.lab_test_template_id.id,
                    'test_group_no': group_no,
                    'number_of_samples': 1,
                    'state': 'draft'
                })
                rs.action_generate_result_lines()
                created_sets |= rs

            self.state = 'testing'

            first_name = created_sets and created_sets[0].name or ''
            self.message_post(body=_(
                "<b>Testing started</b><br/>"
                "Created result sets: <em>%s مجموعة</em><br/>"
                "First: <em>%s</em><br/>"
                "Test template: <em>%s</em>"
            ) % (len(created_sets), first_name, self.lab_test_template_id.name))

            # افتح أول مجموعة ناتجة
            return {
                'type': 'ir.actions.act_window',
                'name': _('Result Set'),
                'res_model': 'lab.result.set',
                'res_id': created_sets and created_sets[0].id or False,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_view_result_sets(self):
        """عرض مجموعات النتائج"""
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
        """إكمال العينة - مع استثناء العينات التجريبية"""
        if not self.result_set_ids:
            raise UserError(_('لا توجد مجموعات نتائج للعينة!'))
        

        non_experimental_sets = []
        for rs in self.result_set_ids:
            if self._is_result_set_experimental(rs):
                continue
            non_experimental_sets.append(rs)
        

        unapproved_names = [rs.name for rs in non_experimental_sets if rs.state != 'approved']
        if unapproved_names:
            raise UserError(_(
                'لا يمكن إكمال العينة حتى يتم اعتماد جميع مجموعات النتائج غير التجريبية!\n'
                'المجموعات غير المعتمدة: %s\n\n'
                'يرجى اعتماد جميع النتائج أولاً قبل إكمال العينة. (تم استثناء عينات 7 أيام والاحتياط)'
            ) % ', '.join(unapproved_names))
        
        self.write({'state': 'completed'})
        self.message_post(body=_('<b>تم إكمال العينة بنجاح</b>'))
    
    def action_approve(self):
        """ اعتماد العينة"""
        self.write({'state': 'approved'})
        self.message_post(body=_("<b>تم اعتماد العينة بنجاح</b>"))
    
    def action_reject(self):
        """رفض العينة"""
        self.write({'state': 'rejected'})
        self.message_post(body=_("<b>Sample rejected</b>"))


    def action_clear_exec_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.exec_signature and rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'exec_signature': False, 'exec_signer_id': False, 'exec_signed_at': False})
        return True

    def action_clear_super_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.super_signature and rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'super_signature': False, 'super_signer_id': False, 'super_signed_at': False})
        return True

    def action_clear_company_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.company_signature and rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'company_signature': False, 'company_signer_id': False, 'company_signed_at': False})
        return True
    
    def action_approve_test(self):
        """مصادقة على الفحص - تغيير الحالة إلى مصادق عليه"""
        self.ensure_one()
        

        if not self.all_signatures_signed:
            from odoo.exceptions import UserError
            raise UserError(_('لا يمكن المصادقة على الفحص قبل إكمال جميع التوقيعات الثلاثة.'))
        

        if self.state != 'completed':
            raise UserError(_('لا يمكن المصادقة إلا على الفحوصات المكتملة.'))
        

        self.write({
            'state': 'approved'
        })
        

        self.message_post(
            body=_('تم المصادقة على الفحص بواسطة %s') % self.env.user.name,
            message_type='notification'
        )
        
        return True


    @api.depends('exec_signature')
    def _compute_exec_is_signed(self):
        for rec in self:
            rec.exec_is_signed = bool(rec.exec_signature)

    @api.depends('super_signature')
    def _compute_super_is_signed(self):
        for rec in self:
            rec.super_is_signed = bool(rec.super_signature)

    @api.depends('company_signature')
    def _compute_company_is_signed(self):
        for rec in self:
            rec.company_is_signed = bool(rec.company_signature)
    
    @api.depends('exec_signature', 'super_signature', 'company_signature')
    def _compute_all_signatures_signed(self):
        """حساب ما إذا كانت جميع التوقيعات الثلاثة موجودة"""
        for rec in self:
            rec.all_signatures_signed = bool(
                rec.exec_signature and 
                rec.super_signature and 
                rec.company_signature
            )

    @api.depends('exec_signed_at', 'super_signed_at', 'company_signed_at')
    def _compute_signature_locks(self):
        """يحسِب قفل التوقيع إذا مرَّ 24 ساعة على آخر توقيع."""
        now = fields.Datetime.now()
        for rec in self:
            rec.exec_signature_locked = bool(rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600)
            rec.super_signature_locked = bool(rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600)
            rec.company_signature_locked = bool(rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600)


    def write(self, vals):
        """تحديث حالة فحص الجودة عند تغيير حالة العينة والعكس + حماية التوقيع بعد 24 ساعة"""


        if any(rec.state == 'approved' for rec in self):

            allowed_fields = {'message_follower_ids', 'message_ids', 'activity_ids', 'activity_state'}
            if not set(vals.keys()).issubset(allowed_fields):
                from odoo.exceptions import UserError
                raise UserError(_('لا يمكن تعديل الفحص بعد المصادقة عليه نهائياً.'))

        now = fields.Datetime.now()


        if 'exec_signature' in vals:
            for rec in self:
                if rec.exec_signature and rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع ممثل الجهة المنفذة بعد مرور 24 ساعة من التوقيع.'))
        if 'super_signature' in vals:
            for rec in self:
                if rec.super_signature and rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع مسؤول الجودة بعد مرور 24 ساعة من التوقيع.'))
        if 'company_signature' in vals:
            for rec in self:
                if rec.company_signature and rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع المدير التنفيذي بعد مرور 24 ساعة من التوقيع.'))

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


        for rec in self:
            updates = {}
            if 'exec_signature' in vals:
                if rec.exec_signature:
                    updates['exec_signed_at'] = now
                else:
                    updates['exec_signed_at'] = False
            if 'super_signature' in vals:
                if rec.super_signature:
                    updates['super_signed_at'] = now
                else:
                    updates['super_signed_at'] = False
            if 'company_signature' in vals:
                if rec.company_signature:
                    updates['company_signed_at'] = now
                else:
                    updates['company_signed_at'] = False
            if updates:
                rec.write(updates)

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
        """حساب ما إذا كانت جميع النتائج معتمدة - مع استثناء العينات التجريبية"""
        for sample in self:
            # جمع جميع مجموعات النتائج
            direct_result_sets = sample.result_set_ids
            flow_result_sets = sample.test_flow_ids.mapped('line_ids.result_set_id')
            all_result_sets = direct_result_sets + flow_result_sets
            
            if not all_result_sets:
                sample.all_results_approved = False
                continue
            

            non_experimental_sets = []
            for rs in all_result_sets:
                if sample._is_result_set_experimental(rs):
                    continue 
                non_experimental_sets.append(rs)
            

            if not non_experimental_sets:
                sample.all_results_approved = True 
            else:
                sample.all_results_approved = all(
                    rs.state in ('approved', 'completed') for rs in non_experimental_sets
                )
    
    def _is_result_set_experimental(self, result_set):
        """فحص إذا كانت مجموعة النتائج من عينة تجريبية (7 أيام أو احتياط)"""
        self.ensure_one()
        

        if not result_set.is_concrete_sample:
            return False
            

        sample = result_set.sample_id
        if not sample:
            return False
            
        move_lines = self.env['stock.move.line']
        
        if sample.lab_code:
            move_lines = self.env['stock.move.line'].search([
                ('field_code', '=', sample.lab_code),
                ('age_days', 'in', ['7', 'reserve'])
            ])
        
        if not move_lines and sample.field_serial:
            move_lines = self.env['stock.move.line'].search([
                ('field_serial', '=', sample.field_serial),
                ('age_days', 'in', ['7', 'reserve'])
            ])
            

        return bool(move_lines)
    
    def action_export_to_excel(self):
        """📊 فتح معالج تصدير Excel للعينة"""
        self.ensure_one()
        
        if not self.result_set_ids:
            raise UserError(_('لا توجد مجموعات نتائج لتصديرها لهذه العينة.'))
        

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
    

    
    consecutive_groups_count = fields.Integer(
        string='عدد المجموعات المتعاقبة',
        compute='_compute_consecutive_groups_data',
        help='عدد المجموعات المتعاقبة المتاحة لحساب المتوسطات'
    )
    
    consecutive_groups_data = fields.Html(
        string='بيانات المجموعات المتعاقبة',
        compute='_compute_consecutive_groups_data',
        help='جدول يعرض متوسطات المجموعات المتعاقبة',
        sanitize=False
    )
    
    show_consecutive_groups = fields.Boolean(
        string='عرض المجموعات المتعاقبة',
        compute='_compute_show_consecutive_groups',
        help='يحدد ما إذا كان يجب عرض المجموعات المتعاقبة للخرسانة'
    )
    
    @api.depends('concrete_sample_type_id')
    def _compute_is_concrete_sample(self):
        """تحديد ما إذا كانت هذه عينة خرسانية"""
        concrete_codes = ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES', 'CONCRETE_CORE']
        for sample in self:
            sample.is_concrete_sample = bool(
                sample.concrete_sample_type_id and 
                sample.concrete_sample_type_id.code in concrete_codes
            )
    
    @api.depends('concrete_sample_type_id', 'result_set_ids')
    def _compute_show_consecutive_groups(self):
        """تحديد ما إذا كان يجب عرض المجموعات المتعاقبة"""
        for sample in self:

            if (sample.concrete_sample_type_id and 
                sample.concrete_sample_type_id.code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS']):

                concrete_sets = sample.result_set_ids.filtered(
                    lambda rs: rs.is_concrete_sample and rs.concrete_age_days == '28'
                )
                sample.show_consecutive_groups = len(concrete_sets) >= 4
            else:
                sample.show_consecutive_groups = False
    
    @api.depends('result_set_ids.result_line_ids.value_numeric', 'concrete_sample_type_id')
    def _compute_consecutive_groups_data(self):
        """حساب بيانات المجموعات المتعاقبة"""
        for sample in self:
            if not sample.show_consecutive_groups:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            

            result_sets = sample.result_set_ids.filtered(
                lambda rs: (rs.is_concrete_sample and 
                           rs.concrete_age_days == '28' and 
                           rs.concrete_group_no)
            ).sorted('concrete_group_no')
            
            if len(result_sets) < 4:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            
            group_averages = []
            for rs in result_sets:
                avg_lines = rs.result_line_ids.filtered(
                    lambda l: l.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append({
                        'group_no': rs.concrete_group_no,
                        'average': avg_lines[0].value_numeric
                    })
            
            if len(group_averages) < 4:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            
            consecutive_data = []
            window_size = 4
            
            ref_general = 0
            ref_min = 0
            general_margin = 3.0
            min_margin = 3.0
            
            if sample.task_id:
                ref_general = float(sample.task_id.reference_general_limit or 0)
                ref_min = float(sample.task_id.reference_min_limit or 0)
            
            for i in range(len(group_averages) - window_size + 1):
                window_groups = group_averages[i:i + window_size]
                window_avg = sum(g['average'] for g in window_groups) / window_size
                
                is_failed = False
                if ref_general and window_avg < (ref_general + general_margin):
                    is_failed = True
                
                consecutive_data.append({
                    'groups': f"{window_groups[0]['group_no']}-{window_groups[-1]['group_no']}",
                    'average': window_avg,
                    'is_failed': is_failed
                })
            
            sample.consecutive_groups_count = len(consecutive_data)
            
            if consecutive_data:
                html = '<div class="consecutive-groups-table">'
                html += '<h5 style="color: #4F81BD; margin-bottom: 10px;">📊 متوسطات المجموعات المتعاقبة</h5>'
                html += '<table class="table table-sm table-bordered" style="font-size: 12px;">'
                html += '<thead style="background-color: #305496; color: white;">'
                html += '<tr><th style="text-align: center; padding: 4px;">المجموعات</th>'
                html += '<th style="text-align: center; padding: 4px;">متوسط القوة (N/mm²)</th>'
                html += '<th style="text-align: center; padding: 4px;">الحالة</th></tr></thead><tbody>'
                
                for data in consecutive_data:
                    bg_color = '#FFC7CE' if data['is_failed'] else '#C6EFCE'
                    status = 'فاشل' if data['is_failed'] else 'ناجح'
                    
                    html += f'<tr style="background-color: {bg_color};">'
                    html += f'<td style="text-align: center; padding: 4px;">{data["groups"]}</td>'
                    html += f'<td style="text-align: center; padding: 4px; font-weight: bold;">{data["average"]:.2f}</td>'
                    html += f'<td style="text-align: center; padding: 4px;">{status}</td>'
                    html += '</tr>'
                
                html += '</tbody></table>'
                
                if ref_general or ref_min:
                    html += '<div style="margin-top: 10px; font-size: 11px; color: #666;">'
                    html += '<strong>المرجع:</strong> '
                    if ref_general:
                        html += f'المعدل: {ref_general:.2f} N/mm² '
                html += '</div>'
            
            sample.consecutive_groups_data = html or False
    
    @api.depends('product_id.default_code', 'product_id.name')
    def _compute_bitumen_type(self):
        """تحديد نوع القير من المنتج"""
        for record in self:
            if record.product_id:
                product_code = record.product_id.default_code or ''
                product_name = record.product_id.name or ''
                
                if 'BASE' in product_code or 'أساس' in product_name:
                    record.bitumen_type = 'قير أساس'
                elif 'SURFACE' in product_code or 'تسطيح' in product_name:
                    record.bitumen_type = 'قير تسطيح'
                else:
                    record.bitumen_type = False
            else:
                record.bitumen_type = False
    
    @api.depends('product_id', 'bitumen_type',
                 'bitumen_comparison_level',
                 'result_set_ids.result_line_ids.value_numeric',
                 'result_set_ids.result_line_ids.value_text',
                 'result_set_ids.result_line_ids.value_selection')
    def _compute_bitumen_results_summary(self):
        """حساب ملخص نتائج القير الجدولي لجميع النتائج المرتبطة بالعينة"""
        for record in self:
            if not record.bitumen_type or record.bitumen_type not in ['قير أساس', 'قير تسطيح']:
                record.bitumen_results_summary = False
                continue
                
            result_sets = self.env['lab.result.set'].search([('sample_id', '=', record.id)])
            
            if not result_sets:
                record.bitumen_results_summary = '<p>لا توجد نتائج فحص مرتبطة بالعينة بعد</p>'
                continue
                
            html = f"""
            <div class="bitumen-results-summary">
                <h4>ملخص نتائج {record.bitumen_type} - العينة {record.name}</h4>
            """
            
            for result_set in result_sets:
                template_name = result_set.template_id.name if result_set.template_id else "غير محدد"
                
                overall_status = "ناجح" if result_set.overall_result == 'pass' else "فاشل"
                status_color = "#28a745" if result_set.overall_result == 'pass' else "#dc3545"
                
                html += f"""
                <div class="mt-3">
                    <h5 style="color: {status_color}; border-bottom: 2px solid {status_color}; padding-bottom: 5px;">
                        {template_name} - {overall_status}
                    </h5>
                    <table class="table table-sm table-bordered">
                        <thead style="background-color: #f8f9fa;">
                            <tr>
                                <th style="width: 50%;">المعيار</th>
                                <th style="width: 25%;">القيمة</th>
                                <th style="width: 25%;">الوحدة</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                

                for line in result_set.result_line_ids.sorted('sequence'):
                    if line.criterion_id and line.is_filled and 'نتيجة فحص الليونة' not in line.criterion_id.name:

                        display_value = ""
                        if line.criterion_id.test_type == 'numeric':
                            display_value = f"{line.value_numeric or 0:.2f}" if line.value_numeric else "0"
                        elif line.criterion_id.test_type == 'text':
                            display_value = line.value_text or ""
                        elif line.criterion_id.test_type == 'selection':
                            display_value = line.value_selection or ""
                        elif line.criterion_id.test_type == 'boolean':
                            display_value = "نعم" if line.value_boolean else "لا"
                        elif line.criterion_id.test_type == 'date':
                            display_value = line.value_date.strftime('%Y-%m-%d') if line.value_date else ""
                        elif line.criterion_id.test_type == 'computed':
                            display_value = f"{line.value_numeric or 0:.2f}" if line.value_numeric else "0"
                        
                        html += f"""
                            <tr>
                                <td><strong>{line.criterion_id.name}</strong></td>
                                <td>{display_value}</td>
                                <td>{line.criterion_id.uom_id.name if line.criterion_id.uom_id else ""}</td>
                            </tr>
                        """
                
                html += """
                        </tbody>
                    </table>
                """
                
                penetration_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id.code == 'PENTEST_AVG')
                if penetration_line:
                    current_value = penetration_line.value_numeric or 0
                    html += record._generate_levels_table('penetration', current_value)
                
                ductility_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id.code == 'DUCTILITY_TEST_AVG')
                if ductility_line:
                    current_value = ductility_line.value_numeric or 0
                    html += record._generate_levels_table('ductility', current_value)
                
                softening_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id.code == 'SOFTENING_AVG')
                if softening_line:
                    current_value = softening_line.value_numeric or 0
                    html += record._generate_levels_table('softening', current_value)
                
                flash_point_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id.code in ['FLASH_POINT', 'FLASH_IGNITION_POINT'])
                if flash_point_line:
                    current_value = flash_point_line.value_numeric or 0
                    html += record._generate_levels_table('flash_point', current_value)
                
                html += """
                </div>
                """
            
            html += """
                <div class="mt-3">
                    <small class="text-muted">
                        <strong>ملاحظة:</strong> يتم عرض جميع المعايير المملوءة لكل قالب فحص مع نتائج المطابقة
                    </small>
                </div>
            </div>
            """
            
            record.bitumen_results_summary = html
    
    def _get_penetration_level(self, value):
        """تحديد مستوى الاختراق حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':

            if 18 <= value <= 60:
                return "النوع الأول", "18-60"
            elif 15 <= value <= 35:
                return "النوع الثاني", "15-35"
            elif 12 <= value <= 25:
                return "النوع الثالث", "12-25"
            else:
                return "خارج المواصفات", f"القيمة {value} خارج النطاقات المقبولة"
                
        elif self.bitumen_type == 'قير أساس':
            if 50 <= value <= 100:
                return "المستوى الأول", "50-100"
            elif 25 <= value <= 50:
                return "المستوى الثاني", "25-50"
            elif 20 <= value <= 40:
                return "المستوى الثالث", "20-40"
            else:
                return "خارج المواصفات", f"القيمة {value} خارج النطاقات المقبولة"
        
        return "غير محدد", ""
    
    def _get_ductility_level(self, value):
        """تحديد مستوى الاستطالة حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':
            if value >= 10:
                return "النوع الأول", "≥ 10 سم"
            elif value >= 3:
                return "النوع الثاني", "≥ 3 سم"
            elif value >= 2.5:
                return "النوع الثالث", "≥ 2.5 سم"
            elif value >= 1.5:
                return "النوع الرابع", "≥ 1.5 سم"
            else:
                return "خارج المواصفات", f"القيمة {value} أقل من 1.5 سم"
                
        elif self.bitumen_type == 'قير أساس':
            if value >= 30:
                return "المستوى الأول", "≥ 30 سم"
            elif value >= 10:
                return "المستوى الثاني", "≥ 10 سم"
            elif value >= 2:
                return "المستوى الثالث", "≥ 2 سم"
            else:
                return "خارج المواصفات", f"القيمة {value} أقل من 2 سم"
        
        return "غير محدد", ""
    
    def _get_softening_level(self, value):
        """تحديد مستوى الليونة حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':

            if 57 <= value <= 66:
                return "النوع الأول", "57-66°م"
            elif 70 <= value <= 80:
                return "النوع الثاني", "70-80°م"
            elif 85 <= value <= 96:
                return "النوع الثالث", "85-96°م"
            elif 99 <= value <= 107:
                return "النوع الرابع", "99-107°م"
            else:
                return "خارج المواصفات", f"القيمة {value}°م خارج النطاقات المقبولة"
                
        elif self.bitumen_type == 'قير أساس':
            if 46 <= value <= 60:
                return "المستوى الأول", "46-60°م"
            elif 63 <= value <= 77:
                return "المستوى الثاني", "63-77°م"
            elif 83 <= value <= 93:
                return "المستوى الثالث", "83-93°م"
            else:
                return "خارج المواصفات", f"القيمة {value}°م خارج النطاقات المقبولة"
        
        return "غير محدد", ""
    
    def _get_all_penetration_levels(self):
        """الحصول على جميع مستويات الاختراق للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "18-60", "0.1 مم"),
                ("النوع الثاني", "15-35", "0.1 مم"),
                ("النوع الثالث", "12-25", "0.1 مم"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "50-100", "0.1 مم"),
                ("المستوى الثاني", "25-50", "0.1 مم"),
                ("المستوى الثالث", "20-40", "0.1 مم"),
            ]
        return []
    
    def _get_all_ductility_levels(self):
        """الحصول على جميع مستويات الاستطالة للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "≥ 10", "سم"),
                ("النوع الثاني", "≥ 3", "سم"),
                ("النوع الثالث", "≥ 2.5", "سم"),
                ("النوع الرابع", "≥ 1.5", "سم"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "≥ 30", "سم"),
                ("المستوى الثاني", "≥ 10", "سم"),
                ("المستوى الثالث", "≥ 2", "سم"),
            ]
        return []
    
    def _get_all_softening_levels(self):
        """الحصول على جميع مستويات الليونة للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "57-66", "°م"),
                ("النوع الثاني", "70-80", "°م"),
                ("النوع الثالث", "85-96", "°م"),
                ("النوع الرابع", "99-107", "°م"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "46-60", "°م"),
                ("المستوى الثاني", "63-77", "°م"),
                ("المستوى الثالث", "83-93", "°م"),
            ]
        return []
    
    def _get_all_flash_point_levels(self):
        """الحصول على مستويات نقطة الوميض للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [("الحد الأدنى المطلوب", "≥ 302", "°م")]
        elif self.bitumen_type == 'قير أساس':
            return [("الحد الأدنى المطلوب", "≥ 232", "°م")]
        return []
    
    def _generate_levels_table(self, test_type, current_value=None):
        """إنشاء جدول المستويات مع تمييز المستوى المطبق"""
        levels = []
        applied_level = ""
        chosen_level_name = ""
        
        if test_type == 'penetration':
            levels = self._get_all_penetration_levels()
            if current_value is not None:
                applied_level, _ = self._get_penetration_level(current_value)
        elif test_type == 'ductility':
            levels = self._get_all_ductility_levels()
            if current_value is not None:
                applied_level, _ = self._get_ductility_level(current_value)
        elif test_type == 'softening':
            levels = self._get_all_softening_levels()
            if current_value is not None:
                applied_level, _ = self._get_softening_level(current_value)
        elif test_type == 'flash_point':
            levels = self._get_all_flash_point_levels()
            if current_value is not None:
                if self.bitumen_type == 'قير تسطيح' and current_value >= 302:
                    applied_level = "الحد الأدنى المطلوب"
                elif self.bitumen_type == 'قير أساس' and current_value >= 232:
                    applied_level = "الحد الأدنى المطلوب"
        
        # تحديد مستوى المقارنة المختار من الحقل (إن وُجد)
        if levels and hasattr(self, 'bitumen_comparison_level'):
            try:
                idx = int(self.bitumen_comparison_level or '1')
            except Exception:
                idx = 1
            idx = max(1, min(idx, len(levels)))
            chosen_level_name = levels[idx - 1][0]
        
        if not levels:
            return ""
        
        html = f"""
        <div class="mt-2">
            <h6 style="color: #6c757d; margin-bottom: 8px;">📋 مستويات {test_type.replace('_', ' ').title()}:</h6>
            <table class="table table-sm table-bordered" style="font-size: 0.85em;">
                <thead style="background-color: #f8f9fa;">
                    <tr>
                        <th style="width: 40%;">المستوى</th>
                        <th style="width: 35%;">النطاق</th>
                        <th style="width: 20%;">الوحدة</th>
                        <th style="width: 5%;">✓</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for level_name, range_value, unit in levels:
            is_chosen = (level_name == chosen_level_name) if chosen_level_name else False
            meets_chosen = (applied_level == chosen_level_name) if chosen_level_name else False
            row_style = "background-color: #fff3cd;" if is_chosen else ""
            check_mark = "✅" if (is_chosen and meets_chosen) else ("❌" if is_chosen else "")
            
            html += f"""
                    <tr style="{row_style}">
                        <td><strong>{level_name}</strong></td>
                        <td>{range_value}</td>
                        <td>{unit}</td>
                        <td style="text-align: center;">{check_mark}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html
      
   # def unlink(self):
   #     """منع حذف العينات في حالة الاختبار أو المكتملة أو المصادق عليها"""
   #     for sample in self:
   #         if sample.state in ('testing', 'completed', 'approved'):
   #             from odoo.exceptions import UserError
   #             raise UserError(_('لا يمكن حذف العينة في حالة الاختبار أو بعد اكتمالها أو بعد المصادقة عليها.'))
   #     return super().unlink()

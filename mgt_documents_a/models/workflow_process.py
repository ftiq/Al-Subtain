# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class WorkflowProcess(models.Model):
    """نموذج العمليات المرنة - قابل للتخصيص لأي نوع من العمليات"""
    
    _name = 'workflow.process'
    _description = 'العمليات وسير العمل'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, sequence asc, name asc'
    _rec_name = 'name'
    

    name = fields.Char(
        string='اسم العملية',
        required=True,
        tracking=True,
        help='اسم مميز للعملية أو سير العمل'
    )
    
    description = fields.Html(
        string='وصف العملية',
        help='وصف تفصيلي للعملية وأهدافها'
    )
    
    code = fields.Char(
        string='رمز العملية',
        help='رمز مختصر للعملية للاستخدام في النظام'
    )
    
    category = fields.Selection([
        ('document_review', 'مراجعة الوثائق'),
        ('approval_workflow', 'سير عمل الموافقات'),
        ('document_routing', 'توجيه الوثائق'),
        ('task_assignment', 'تكليف المهام'),
        ('department_transfer', 'تحويل بين الأقسام'),
        ('automated_workflow', 'سير عمل تلقائي'),
        ('data_processing', 'معالجة البيانات'),
        ('communication', 'التواصل والمراسلات'),
        ('administrative', 'الأعمال الإدارية'),
        ('quality_control', 'ضبط الجودة'),
        ('custom', 'مخصص')
    ], string='فئة العملية', default='custom', tracking=True)
    
    process_type = fields.Selection([
        ('sequential', 'متتالي'),
        ('parallel', 'متوازي'),
        ('conditional', 'شرطي'),
        ('loop', 'دوري'),
        ('hybrid', 'مختلط')
    ], string='نوع سير العمل', default='sequential')
    

    expected_duration = fields.Float(
        string='المدة المتوقعة (ساعات)',
        default=24.0,
        help='المدة المتوقعة لإنجاز العملية بالساعات'
    )
    
    escalation_threshold = fields.Float(
        string='حد التصعيد (ساعات)',
        default=48.0,
        help='عدد الساعات قبل تصعيد العملية'
    )
    
    priority = fields.Selection([
        ('0', 'منخفض'),
        ('1', 'عادي'),
        ('2', 'مهم'),
        ('3', 'عاجل'),
        ('4', 'حرج')
    ], string='الأولوية', default='1')
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب العملية عند العرض'
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )
    
    applicable_to = fields.Selection([
        ('all_documents', 'جميع الوثائق'),
        ('specific_categories', 'فئات محددة'),
        ('specific_departments', 'أقسام محددة'),
        ('specific_roles', 'أدوار محددة'),
        ('custom_conditions', 'شروط مخصصة')
    ], string='نطاق التطبيق', default='all_documents')
    
    applicable_category_ids = fields.Many2many(
        'document.category',
        string='الفئات المشمولة',
        help='فئات الوثائق التي تنطبق عليها هذه العملية'
    )
    
    applicable_department_ids = fields.Many2many(
        'hr.department',
        string='الأقسام المشمولة',
        help='الأقسام التي تنطبق عليها هذه العملية'
    )
    
    step_ids = fields.One2many(
        'workflow.step',
        'process_id',
        string='خطوات العملية'
    )
    
    step_count = fields.Integer(
        string='عدد الخطوات',
        compute='_compute_step_count'
    )
    
    trigger_conditions = fields.Text(
        string='شروط التفعيل',
        help='اتركه فارغاً ليتم التفعيل بدون شروط. يمكن إدخال JSON مبسط عند الحاجة.'
    )
    
    auto_trigger = fields.Boolean(
        string='التفعيل التلقائي',
        default=True,
        help='تفعيل العملية تلقائياً عند توفر الشروط'
    )
    
    sla_hours = fields.Float(
        string='الوقت المعياري (ساعة)',
        help='الوقت المعياري لإنجاز العملية بالساعات'
    )
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('testing', 'قيد الاختبار'),
        ('deprecated', 'مهجور'),
        ('archived', 'مؤرشف')
    ], string='الحالة', default='draft', tracking=True)
    
    instance_ids = fields.One2many(
        'document.workflow.instance',
        'workflow_process_id',
        string='نسخ التنفيذ',
        help='جميع نسخ التنفيذ لهذه العملية'
    )
    
    instance_count = fields.Integer(
        string='عدد مرات التنفيذ',
        compute='_compute_instance_count',
        help='عدد المرات التي تم تنفيذ هذه العملية'
    )
    
    success_rate = fields.Float(
        string='معدل النجاح (%)',
        compute='_compute_success_rate',
        help='نسبة النجاح في تنفيذ العملية'
    )
    
    average_completion_time = fields.Float(
        string='متوسط وقت الإنجاز (ساعة)',
        compute='_compute_average_completion_time',
        store=True,
        aggregator='avg'
    )
    
    owner_id = fields.Many2one(
        'hr.employee',
        string='مالك العملية',
        tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    
    manager_ids = fields.Many2many(
        'hr.employee',
        'process_manager_rel',
        string='مديرو العملية',
        help='الموظفون المسؤولون عن إدارة هذه العملية'
    )
    
    allow_skip_steps = fields.Boolean(
        string='السماح بتخطي الخطوات',
        default=False,
        help='السماح للمستخدمين بتخطي خطوات معينة'
    )
    
    require_notes = fields.Boolean(
        string='مطالبة بالملاحظات',
        default=True,
        help='مطالبة المستخدمين بإدخال ملاحظات عند كل خطوة'
    )
    
    notification_enabled = fields.Boolean(
        string='تفعيل الإشعارات',
        default=True,
        help='إرسال إشعارات للمسؤولين عند تقدم العملية'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.depends('step_ids')
    def _compute_step_count(self):
        """حساب عدد خطوات العملية"""
        for process in self:
            process.step_count = len(process.step_ids)
    
    @api.depends('instance_ids')
    def _compute_instance_count(self):
        """حساب عدد مرات تنفيذ العملية"""
        for process in self:
            process.instance_count = self.env['document.workflow.instance'].search_count([
                ('workflow_process_id', '=', process.id)
            ])
    
    @api.depends('instance_ids')
    def _compute_success_rate(self):
        """حساب معدل نجاح العملية"""
        for process in self:
            instances = self.env['document.workflow.instance'].search([
                ('workflow_process_id', '=', process.id)
            ])
            
            if instances:
                completed = instances.filtered(lambda i: i.state == 'completed')
                process.success_rate = (len(completed) / len(instances)) * 100
            else:
                process.success_rate = 0.0
    
    @api.depends('instance_ids')
    def _compute_average_completion_time(self):
        """حساب متوسط وقت إنجاز العملية"""
        for process in self:
            completed_instances = self.env['document.workflow.instance'].search([
                ('workflow_process_id', '=', process.id),
                ('state', '=', 'completed'),
                ('start_date', '!=', False),
                ('completion_date', '!=', False)
            ])
            
            if completed_instances:
                total_hours = sum([
                    (instance.completion_date - instance.start_date).total_seconds() / 3600
                    for instance in completed_instances
                ])
                process.average_completion_time = total_hours / len(completed_instances)
            else:
                process.average_completion_time = 0.0
    
    def action_activate(self):
        """تفعيل العملية"""
        for process in self:
            if not process.step_ids:
                raise UserError(_('لا يمكن تفعيل عملية بدون خطوات'))
            
            process.write({'state': 'active'})
            process._create_activation_log()
    
    def action_test(self):
        """تشغيل العملية في وضع الاختبار"""
        for process in self:
            process.write({'state': 'testing'})

            test_instance = process._create_test_instance()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'document.workflow.instance',
                'res_id': test_instance.id,
                'view_mode': 'form',
                'target': 'new'
            }
    
    def action_deprecate(self):
        """عزل العملية"""
        for process in self:
            process.write({'state': 'deprecated'})

            active_instances = self.env['document.workflow.instance'].search([
                ('workflow_process_id', '=', process.id),
                ('state', 'in', ['running', 'waiting'])
            ])
            active_instances.action_cancel()
    
    def action_view_instances(self):
        """Open instances related to this process"""
        self.ensure_one()
        action = self.env.ref('mgt_documents.document_workflow_instance_action').read()[0]
        action['domain'] = [('workflow_process_id', '=', self.id)]
        action['context'] = {
            'default_workflow_process_id': self.id,
        }
        return action

    def action_view_steps(self):
        """Open steps related to this process"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('خطوات العملية'),
            'res_model': 'workflow.step',
            'view_mode': 'list,form',
            'domain': [('process_id', '=', self.id)],
            'context': {'default_process_id': self.id},
            'target': 'current',
        }

    def action_archive_process(self):
        """أرشفة العملية"""
        for process in self:
            process.write({
                'state': 'archived',
                'active': False
            })
    
    def create_instance(self, document_id=None, trigger_data=None):
        """إنشاء نسخة جديدة من العملية"""
        self.ensure_one()
        
        if self.state != 'active':
            raise UserError(_('العملية غير نشطة ولا يمكن تنفيذها'))
        
        if not self._check_trigger_conditions(trigger_data):
            return False
        
        instance = self.env['document.workflow.instance'].create({
            'workflow_process_id': self.id,
            'document_id': document_id,
            'name': f"{self.name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'trigger_data': json.dumps(trigger_data or {}),
            'state': 'running'
        })
        # Set initial step to the first by sequence, if any
        first_step = self.step_ids and self.step_ids.sorted(key=lambda s: (s.sequence, s.id))[:1]
        if first_step:
            instance.current_step_id = first_step.id
            # Update document linkage and visible current step if a document is attached
            if document_id:
                doc = self.env['document.document'].browse(document_id)
                try:
                    doc.write({'current_step': first_step.name})
                except Exception:
                    pass
            # Spawn tasks for the first step
            try:
                step_rec = first_step[0] if isinstance(first_step, list) else first_step
                instance._spawn_tasks_for_step(step_rec)
            except Exception:
                pass

        return instance
    
    def _check_trigger_conditions(self, trigger_data):
        """فحص شروط تفعيل العملية"""
        if not self.trigger_conditions:
            return True
        try:
            conditions = json.loads(self.trigger_conditions)
            return self._evaluate_conditions(conditions, trigger_data or {})
        except (json.JSONDecodeError, Exception) as e:
            _logger.error(f"Error evaluating trigger conditions: {str(e)}")
            return False
    
    def _evaluate_conditions(self, conditions, data):
        """تقييم الشروط المخصصة"""

        if not conditions or not isinstance(conditions, dict):
            return True
        
        for key, expected_value in conditions.items():
            if key not in data:
                return False
            if data[key] != expected_value:
                return False
        
        return True
    
    def _create_test_instance(self):
        """إنشاء نسخة تجريبية للاختبار"""
        return self.env['document.workflow.instance'].create({
            'workflow_process_id': self.id,
            'name': f"اختبار {self.name}",
            'state': 'running'
        })
    
    def _create_activation_log(self):
        """إنشاء سجل تفعيل العملية"""
        self.message_post(
            body=_('تم تفعيل العملية بواسطة %s') % self.env.user.name,
            message_type='notification'
        )
    

    @api.constrains('code')
    def _check_code_uniqueness(self):
        """التحقق من تفرد رمز العملية"""
        for process in self:
            if process.code:
                existing = self.search([
                    ('code', '=', process.code),
                    ('id', '!=', process.id),
                    ('company_id', '=', process.company_id.id)
                ])
                if existing:
                    raise ValidationError(_('رمز العملية يجب أن يكون فريداً داخل الشركة'))
    
    @api.constrains('sla_hours')
    def _check_sla_hours(self):
        """التحقق من صحة الوقت المعياري"""
        for process in self:
            if process.sla_hours and process.sla_hours <= 0:
                raise ValidationError(_('الوقت المعياري يجب أن يكون موجباً'))
    
    @api.constrains('expected_duration', 'escalation_threshold')
    def _check_duration_consistency(self):
        """التحقق من تناسق المدد الزمنية"""
        for process in self:
            if (process.escalation_threshold and process.expected_duration and 
                process.escalation_threshold <= process.expected_duration):
                raise ValidationError(_('حد التصعيد يجب أن يكون أكبر من المدة المتوقعة'))


class WorkflowStep(models.Model):
    """خطوات العملية"""
    
    _name = 'workflow.step'
    _description = 'خطوات العملية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'process_id, sequence, id'
    
    process_id = fields.Many2one(
        'workflow.process',
        string='العملية',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='اسم الخطوة',
        required=True
    )
    
    description = fields.Html(
        string='وصف الخطوة',
        help='تعليمات تفصيلية لتنفيذ الخطوة'
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب الخطوة في العملية'
    )
    
    step_type = fields.Selection([
        ('manual', 'خطوة يدوية'),
        ('automatic', 'خطوة تلقائية'),
        ('approval', 'موافقة'),
        ('review', 'مراجعة'),
        ('data_entry', 'إدخال بيانات'),
        ('notification', 'إشعار'),
        ('wait', 'انتظار'),
        ('condition', 'شرط')
    ], string='نوع الخطوة', default='manual', required=True)
    

    responsible_type = fields.Selection([
        ('specific_user', 'مستخدم محدد'),
        ('department', 'قسم'),
        ('role', 'دور وظيفي'),
        ('automatic', 'تلقائي')
    ], string='نوع المسؤول', default='specific_user')
    
    responsible_user_id = fields.Many2one('hr.employee', string='المستخدم المسؤول')
    responsible_department_id = fields.Many2one('hr.department', string='القسم المسؤول')
    responsible_role = fields.Char(string='الدور الوظيفي')
    
    estimated_hours = fields.Float(
        string='الوقت المُقدر (ساعة)',
        help='الوقت المُقدر لإنجاز الخطوة'
    )
    
    deadline_hours = fields.Float(
        string='المهلة القصوى (ساعة)',
        help='المهلة القصوى المسموحة لإنجاز الخطوة'
    )
    
    required_conditions = fields.Text(
        string='الشروط المطلوبة',
        help='الشروط التي يجب توفرها لتنفيذ الخطوة'
    )
    
    skip_conditions = fields.Text(
        string='شروط التخطي',
        help='الشروط التي تسمح بتخطي هذه الخطوة'
    )
    
    is_mandatory = fields.Boolean(
        string='إجبارية',
        default=True,
        help='هل يمكن تخطي هذه الخطوة'
    )
    
    requires_approval = fields.Boolean(
        string='تتطلب موافقة',
        default=False,
        help='هل تحتاج الخطوة لموافقة إضافية'
    )
    
    next_step_ids = fields.Many2many(
        'workflow.step',
        'step_next_rel',
        'step_id',
        'next_step_id',
        string='الخطوات التالية'
    )
    
    send_notification = fields.Boolean(
        string='إرسال إشعار',
        default=True
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='قالب الإشعار'
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True
    )
    
    hint_text = fields.Html(
        string='إرشادات الخطوة',
        compute='_compute_hint_text',
        sanitize=True
    )
    
    @api.constrains('next_step_ids')
    def _check_no_circular_reference(self):
        """منع المراجع الدائرية في الخطوات"""
        for step in self:
            if step in step.next_step_ids:
                raise ValidationError(_('لا يمكن للخطوة أن تشير لنفسها'))
    
    def action_toggle_active(self):
        """تبديل حالة النشاط للخطوة"""
        for step in self:
            step.active = not step.active

    @api.depends('step_type', 'responsible_type')
    def _compute_hint_text(self):
        """توليد تلميح نصي يشرح وظيفة كل نوع خطوة وكيفية استخدامها"""
        type_hints = {
            'manual': _("خطوة يدوية: تُنشئ مهام تنفيذية للمستخدم/القسم المسؤول، ويتم التقدم عند إكمال المهام."),
            'automatic': _("خطوة تلقائية: لا تُنشئ مهام. تُستخدم للانتقالات الآلية أو التحقق البرمجي."),
            'approval': _("خطوة موافقة: تُنشئ مهام موافقة للمسؤولين المحددين، ويتقدم المسار بعد الموافقة/الإكمال."),
            'review': _("خطوة مراجعة: تُنشئ مهام مراجعة وتقييم للوثيقة."),
            'data_entry': _("إدخال بيانات: تُنشئ مهام إدخال/استكمال بيانات مطلوبة."),
            'notification': _("إشعار: تُنشئ مهام متابعة بسيطة/تنبيه دون عمل مُعقّد."),
            'wait': _("انتظار: تُوقف المسار حتى اكتمال مهام المتابعة أو انتهاء مهلة."),
            'condition': _("شرط: تعتمد على شروط للانتقال، وقد تُنشئ مهام تحقق عند الحاجة."),
        }
        resp_hints = {
            'specific_user': _("المسؤول: مستخدم محدد. سيتم تكليف المهام مباشرة لهذا الموظف."),
            'department': _("المسؤول: قسم. سيتم تكليف المهام للقسم لتحديد المنفذ داخلياً."),
            'role': _("المسؤول: دور وظيفي. سيُختار موظف مناسب تلقائياً حسب الدور."),
            'automatic': _("المسؤول: تلقائي. لا يوجد تكليف يدوي للمهام."),
        }
        for rec in self:
            base = type_hints.get(rec.step_type or 'manual', '')
            resp = resp_hints.get(rec.responsible_type or 'specific_user', '')
            rec.hint_text = f"<div class='alert alert-info'><p>{base}</p><p class='mb-0'>{resp}</p></div>"

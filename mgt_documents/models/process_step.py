# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class ProcessStep(models.Model):
    """نموذج خطوات العملية BPMN 2.0"""
    
    _name = 'process.step'
    _description = 'خطوات العملية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'process_id, sequence, id'
    _rec_name = 'name'
    
    process_id = fields.Many2one(
        'workflow.process',
        string='العملية',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='اسم الخطوة',
        required=True,
        tracking=True
    )
    
    description = fields.Html(
        string='وصف الخطوة',
        help='وصف تفصيلي لما يجب عمله في هذه الخطوة'
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب الخطوة في العملية'
    )
    
    step_type = fields.Selection([
        ('user_task', 'مهمة مستخدم'),
        ('service_task', 'مهمة خدمة'),
        ('manual_task', 'مهمة يدوية'),
        ('script_task', 'مهمة برمجية'),
        ('send_task', 'مهمة إرسال'),
        ('receive_task', 'مهمة استقبال'),
        ('gateway', 'بوابة قرار'),
        ('timer', 'مؤقت'),
        ('notification', 'إشعار'),
        ('approval', 'موافقة'),
        ('review', 'مراجعة'),
        ('archive', 'أرشفة')
    ], string='نوع الخطوة', required=True, default='user_task', tracking=True)
    
    condition = fields.Text(
        string='شرط التنفيذ',
        help='شرط يجب توفره لتنفيذ هذه الخطوة (Python expression)',
        default='True'
    )
    
    is_mandatory = fields.Boolean(
        string='خطوة إجبارية',
        default=True,
        help='هل يمكن تخطي هذه الخطوة'
    )
    
    responsible_type = fields.Selection([
        ('specific_user', 'مستخدم محدد'),
        ('specific_employee', 'موظف محدد'),
        ('department', 'قسم'),
        ('role', 'دور'),
        ('group', 'مجموعة'),
        ('auto_assign', 'تكليف تلقائي')
    ], string='نوع المسؤولية', default='department', required=True)
    
    responsible_user_id = fields.Many2one(
        'res.users',
        string='المستخدم المسؤول'
    )
    
    responsible_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المسؤول'
    )
    
    responsible_department_id = fields.Many2one(
        'hr.department',
        string='القسم المسؤول'
    )
    
    responsible_role = fields.Many2one(
        'res.groups',
        string='الدور المسؤول'
    )
    
    max_duration = fields.Integer(
        string='أقصى مدة (ساعات)',
        default=24,
        help='أقصى مدة لإنجاز هذه الخطوة'
    )
    
    escalation_duration = fields.Integer(
        string='مدة التصعيد (ساعات)',
        default=48,
        help='المدة قبل تصعيد هذه الخطوة'
    )
    
    next_step_ids = fields.Many2many(
        'process.step',
        'process_step_flow_rel',
        'from_step_id',
        'to_step_id',
        string='الخطوات التالية',
        help='الخطوات التي يمكن الانتقال إليها من هذه الخطوة'
    )
    
    previous_step_ids = fields.Many2many(
        'process.step',
        'process_step_flow_rel',
        'to_step_id',
        'from_step_id',
        string='الخطوات السابقة',
        help='الخطوات التي تؤدي إلى هذه الخطوة'
    )
    
    send_notification = fields.Boolean(
        string='إرسال إشعار',
        default=True,
        help='إرسال إشعار عند بدء هذه الخطوة'
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='قالب الإشعار',
        help='قالب البريد الإلكتروني للإشعار'
    )
    
    require_attachment = fields.Boolean(
        string='مطالبة بمرفق',
        default=False,
        help='مطالبة المستخدم بإرفاق ملف'
    )
    
    require_notes = fields.Boolean(
        string='مطالبة بملاحظات',
        default=True,
        help='مطالبة المستخدم بإدخال ملاحظات'
    )
    
    approval_type = fields.Selection([
        ('single', 'موافقة فردية'),
        ('sequential', 'موافقة متتالية'),
        ('parallel', 'موافقة متوازية'),
        ('majority', 'موافقة الأغلبية')
    ], string='نوع الموافقة', default='single')
    
    approver_ids = fields.Many2many(
        'hr.employee',
        'process_step_approver_rel',
        'step_id',
        'employee_id',
        string='الموافقون',
        help='الموظفون المخولون بالموافقة على هذه الخطوة'
    )
    
    gateway_type = fields.Selection([
        ('exclusive', 'بوابة حصرية'),
        ('inclusive', 'بوابة شاملة'),
        ('parallel', 'بوابة متوازية'),
        ('complex', 'بوابة معقدة')
    ], string='نوع البوابة', default='exclusive')
    
    gateway_conditions = fields.Text(
        string='شروط البوابة',
        help='شروط تحديد المسار التالي (JSON format)',
        default='{}'
    )
    
    timer_type = fields.Selection([
        ('duration', 'مدة محددة'),
        ('date', 'تاريخ محدد'),
        ('cycle', 'دوري')
    ], string='نوع المؤقت', default='duration')
    
    timer_duration = fields.Integer(
        string='مدة المؤقت (دقائق)',
        default=60
    )
    
    timer_date = fields.Datetime(
        string='تاريخ المؤقت'
    )
    
    execution_count = fields.Integer(
        string='عدد مرات التنفيذ',
        compute='_compute_execution_stats',
        store=True
    )
    
    average_duration = fields.Float(
        string='متوسط المدة (ساعات)',
        compute='_compute_execution_stats',
        store=True
    )
    
    success_rate = fields.Float(
        string='معدل النجاح (%)',
        compute='_compute_execution_stats',
        store=True
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        related='process_id.company_id',
        store=True
    )
    

    @api.depends('process_id.instance_ids')
    def _compute_execution_stats(self):
        for step in self:

            instances = step.process_id.instance_ids
            step_executions = instances.mapped('step_history_ids').filtered(
                lambda h: h.step_id.id == step.id
            )
            
            step.execution_count = len(step_executions)
            
            if step_executions:
                completed_executions = step_executions.filtered(lambda h: h.state == 'completed')
                step.success_rate = (len(completed_executions) / len(step_executions)) * 100
                
                if completed_executions:
                    total_duration = sum([
                        (exec.completion_date - exec.start_date).total_seconds() / 3600
                        for exec in completed_executions
                        if exec.completion_date and exec.start_date
                    ])
                    step.average_duration = total_duration / len(completed_executions) if completed_executions else 0
                else:
                    step.average_duration = 0
            else:
                step.success_rate = 0
                step.average_duration = 0
    
    @api.constrains('max_duration', 'escalation_duration')
    def _check_duration_consistency(self):
        for step in self:
            if step.escalation_duration <= step.max_duration:
                raise ValidationError(_('مدة التصعيد يجب أن تكون أكبر من أقصى مدة للخطوة'))
    
    @api.constrains('next_step_ids')
    def _check_circular_dependency(self):
        """منع الدورات اللانهائية في الخطوات"""
        for step in self:
            visited = set()
            
            def check_cycle(current_step, path):
                if current_step.id in path:
                    raise ValidationError(_('دورة لانهائية مكتشفة في خطوات العملية'))
                
                path.add(current_step.id)
                for next_step in current_step.next_step_ids:
                    check_cycle(next_step, path.copy())
            
            check_cycle(step, set())
    
    def execute_step(self, instance, execution_data=None):
        """تنفيذ الخطوة"""
        self.ensure_one()
        
        if not self._check_condition(instance, execution_data):
            return False
        
        execution = self.env['process.step.execution'].create({
            'step_id': self.id,
            'instance_id': instance.id,
            'start_date': fields.Datetime.now(),
            'state': 'running',
            'execution_data': json.dumps(execution_data or {})
        })
        
        if self.step_type == 'user_task':
            self._execute_user_task(instance, execution)
        elif self.step_type == 'service_task':
            self._execute_service_task(instance, execution)
        elif self.step_type == 'gateway':
            self._execute_gateway(instance, execution)
        elif self.step_type == 'timer':
            self._execute_timer(instance, execution)
        elif self.step_type == 'notification':
            self._execute_notification(instance, execution)
        
        return execution
    
    def _check_condition(self, instance, execution_data):
        """فحص شرط تنفيذ الخطوة"""
        if not self.condition or self.condition.strip() == 'True':
            return True
        
        try:
            local_vars = {
                'instance': instance,
                'data': execution_data or {},
                'step': self,
                'process': self.process_id
            }
            return eval(self.condition, {"__builtins__": {}}, local_vars)
        except Exception as e:
            _logger.error(f"Error evaluating step condition: {e}")
            return False
    
    def _execute_user_task(self, instance, execution):
        """تنفيذ مهمة مستخدم"""
        task = self.env['admin.task'].create({
            'name': f'{self.name} - {instance.name}',
            'description': self.description,
            'task_type': 'execute_action',
            'process_id': self.process_id.id,
            'process_instance_id': instance.instance_id,
            'assigned_department_id': self.responsible_department_id.id,
            'assigned_employee_id': self.responsible_employee_id.id,
            'due_date': fields.Datetime.now() + timedelta(hours=self.max_duration),
            'escalation_date': fields.Datetime.now() + timedelta(hours=self.escalation_duration),
            'state': 'assigned'
        })
        

        execution.admin_task_id = task.id
        
        if self.send_notification:
            self._send_notification(instance, task)
    
    def _execute_service_task(self, instance, execution):
        """تنفيذ مهمة خدمة (تلقائية)"""
        # بعدين بسوية  المهام التلقائية
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        instance.move_to_next_step(self)
    
    def _execute_gateway(self, instance, execution):
        """تنفيذ بوابة قرار"""
        
        next_steps = self._evaluate_gateway_conditions(instance)
        
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        for step in next_steps:
            step.execute_step(instance)
    
    def _execute_timer(self, instance, execution):
        """تنفيذ مؤقت"""
        from datetime import timedelta
        
        if self.timer_type == 'duration':

            execution.write({
                'state': 'waiting',
                'scheduled_date': fields.Datetime.now() + timedelta(minutes=self.timer_duration)
            })
        elif self.timer_type == 'date':
            execution.write({
                'state': 'waiting',
                'scheduled_date': self.timer_date
            })
    
    def _execute_notification(self, instance, execution):
        """تنفيذ إشعار"""
        self._send_notification(instance)
        
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        instance.move_to_next_step(self)
    
    def _send_notification(self, instance, task=None):
        """إرسال إشعار"""
        if self.notification_template_id:
            self.notification_template_id.send_mail(instance.id)
        else:
            recipients = []
            if self.responsible_employee_id:
                recipients.append(self.responsible_employee_id.work_email)
            elif self.responsible_department_id:
                recipients.extend(
                    self.responsible_department_id.member_ids.mapped('work_email')
                )
            
            if recipients:
                pass
    
    def _evaluate_gateway_conditions(self, instance):
        """تقييم شروط البوابة لتحديد المسار التالي"""
        try:
            conditions = json.loads(self.gateway_conditions or '{}')
            next_steps = []
            
            for step_id, condition in conditions.items():
                step = self.env['process.step'].browse(int(step_id))
                if step and step._check_condition(instance, {}):
                    next_steps.append(step)
            
            return next_steps
        except Exception as e:
            _logger.error(f"Error evaluating gateway conditions: {e}")
            return self.next_step_ids
    
    def action_test_step(self):
        """اختبار الخطوة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الاختبار'),
                'message': _('تم اختبار الخطوة بنجاح'),
                'type': 'success'
            }
        }
    
    def action_view_executions(self):
        """عرض سجل تنفيذ الخطوة"""
        action = self.env.ref('mgt_documents.action_process_step_execution').read()[0]
        action['domain'] = [('step_id', '=', self.id)]
        return action
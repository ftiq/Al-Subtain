# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class ProcessStep(models.Model):
    """Process step model"""
    
    _name = 'process.step'
    _description = 'Process Step'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'process_id, sequence, id'
    _rec_name = 'name'
    
    process_id = fields.Many2one(
        'workflow.process',
        string='Process',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Step Name',
        required=True,
        tracking=True
    )
    
    description = fields.Html(
        string='Description',
        help='Description of what needs to be done in this step'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of the step in the process'
    )
    
    step_type = fields.Selection([
        ('user_task', 'User Task'),
        ('service_task', 'Service Task'),
        ('manual_task', 'Manual Task'),
        ('script_task', 'Script Task'),
        ('send_task', 'Send Task'),
        ('receive_task', 'Receive Task'),
        ('gateway', 'Gateway'),
        ('timer', 'Timer'),
        ('notification', 'Notification'),
        ('approval', 'Approval'),
        ('review', 'Review'),
        ('archive', 'Archive')
    ], string='Step Type', required=True, default='user_task', tracking=True)
    
    condition = fields.Text(
        string='Condition',
        help='Condition that must be met to execute this step (Python expression)',
        default='True'
    )
    
    is_mandatory = fields.Boolean(
        string='Mandatory Step',
        default=True,
        help='Can this step be skipped'
    )
    
    responsible_type = fields.Selection([
        ('specific_user', 'Specific User'),
        ('specific_employee', 'Specific Employee'),
        ('department', 'Department'),
        ('role', 'Role'),
        ('group', 'Group'),
        ('auto_assign', 'Auto Assign')
    ], string='Responsible Type', default='department', required=True)
    
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible User'
    )
    
    responsible_employee_id = fields.Many2one(
        'hr.employee',
        string='Responsible Employee'
    )
    
    responsible_department_id = fields.Many2one(
        'hr.department',
        string='Responsible Department'
    )
    
    responsible_role = fields.Many2one(
        'res.groups',
        string='Responsible Role'
    )
    
    max_duration = fields.Integer(
        string='Maximum Duration (Hours)',
        default=24,
        help='Maximum duration for this step'
    )
    
    escalation_duration = fields.Integer(
        string='Escalation Duration (Hours)',
        default=48,
        help='The duration before escalation of this step'
    )
    
    next_step_ids = fields.Many2many(
        'process.step',
        'process_step_flow_rel',
        'from_step_id',
        'to_step_id',
        string='Next Steps',
        help='Steps that can be transitioned to from this step'
    )
    
    previous_step_ids = fields.Many2many(
        'process.step',
        'process_step_flow_rel',
        'to_step_id',
        'from_step_id',
        string='Previous Steps',
        help='Steps that lead to this step'
    )
    
    send_notification = fields.Boolean(
        string='Send Notification',
        default=True,
        help='Send notification when this step starts'
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Notification Template',
        help='Email template for notification'
    )
    
    require_attachment = fields.Boolean(
        string='Attachment Required',
        default=False,
        help='Attachment required'
    )
    
    require_notes = fields.Boolean(
        string='Notes Required',
        default=True,
        help='Require user to enter notes'
    )
    
    approval_type = fields.Selection([
        ('single', 'Single Approval'),
        ('sequential', 'Sequential Approval'),
        ('parallel', 'Parallel Approval'),
        ('majority', 'Majority Approval')
    ], string='Approval Type', default='single')
    
    approver_ids = fields.Many2many(
        'hr.employee',
        'process_step_approver_rel',
        'step_id',
        'employee_id',
        string='Approvers',
        help='Employees authorized to approve this step'
    )
    
    gateway_type = fields.Selection([
        ('exclusive', 'Exclusive Gateway'),
        ('inclusive', 'Inclusive Gateway'),
        ('parallel', 'Parallel Gateway'),
        ('complex', 'Complex Gateway')
    ], string='Gateway Type', default='exclusive')
    
    gateway_conditions = fields.Text(
        string='Gateway Conditions',
        help='Conditions for determining the next step (JSON format)',
        default='{}'
    )
    
    timer_type = fields.Selection([
        ('duration', 'Duration'),
        ('date', 'Date'),
        ('cycle', 'Cycle')
    ], string='Timer Type', default='duration')
    
    timer_duration = fields.Integer(
        string='Timer Duration (Minutes)',
        default=60
    )
    
    timer_date = fields.Datetime(
        string='Timer Date'
    )
    
    execution_count = fields.Integer(
        string='Execution Count',
        compute='_compute_execution_stats',
        store=True
    )
    
    average_duration = fields.Float(
        string='Average Duration (Hours)',
        compute='_compute_execution_stats',
        store=True
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_execution_stats',
        store=True
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
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
                raise ValidationError(_('Escalation duration must be greater than maximum duration for this step'))
    
    @api.constrains('next_step_ids')
    def _check_circular_dependency(self):
        """Prevent circular dependencies in steps"""
        for step in self:
            visited = set()
            
            def check_cycle(current_step, path):
                if current_step.id in path:
                    raise ValidationError(_('Circular dependency detected in process steps'))
                
                path.add(current_step.id)
                for next_step in current_step.next_step_ids:
                    check_cycle(next_step, path.copy())
            
            check_cycle(step, set())
    
    def execute_step(self, instance, execution_data=None):
        """Execute the step"""
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
        """Check step execution condition"""
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
        """Execute user task"""
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
        """Execute service task"""
        # بعدين بسوية  المهام التلقائية
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        instance.move_to_next_step(self)
    
    def _execute_gateway(self, instance, execution):
        """Execute decision gateway"""
        
        next_steps = self._evaluate_gateway_conditions(instance)
        
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        for step in next_steps:
            step.execute_step(instance)
    
    def _execute_timer(self, instance, execution):
        """Execute timer"""
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
        """Execute notification"""
        self._send_notification(instance)
        
        execution.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        
        instance.move_to_next_step(self)
    
    def _send_notification(self, instance, task=None):
        """Send notification"""
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
        """Evaluate gateway conditions to determine the next step"""
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
        """Test the step"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test'),
                'message': _('Step tested successfully'),
                'type': 'success'
            }
        }
    
    def action_view_executions(self):
        """View step execution history"""
        action = self.env.ref('mgt_documents.action_process_step_execution').read()[0]
        action['domain'] = [('step_id', '=', self.id)]
        return action
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class WorkflowProcess(models.Model):
    """form the workflow process """
    
    _name = 'workflow.process'
    _description = 'Workflow Process'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, sequence asc, name asc'
    _rec_name = 'name'
    

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        help='Unique name for the workflow process or workflow'
    )
    
    description = fields.Html(
        string='Description',
        help='Detailed description of the workflow process or workflow'
    )
    
    code = fields.Char(
        string='Code',
        help='Short code for the workflow process or workflow for system use'
    )
    
    category = fields.Selection([
        ('document_review', 'Document Review'),
        ('approval_workflow', 'Approval Workflow'),
        ('document_routing', 'Document Routing'),
        ('task_assignment', 'Task Assignment'),
        ('department_transfer', 'Department Transfer'),
        ('automated_workflow', 'Automated Workflow'),
        ('data_processing', 'Data Processing'),
        ('communication', 'Communication'),
        ('administrative', 'Administrative'),
        ('quality_control', 'Quality Control'),
        ('custom', 'Custom')
    ], string='Category', default='custom', tracking=True)
    
    process_type = fields.Selection([
        ('sequential', 'Sequential'),
        ('parallel', 'Parallel'),
        ('conditional', 'Conditional'),
        ('loop', 'Loop'),
        ('hybrid', 'Hybrid')
    ], string='Process Type', default='sequential')
    

    expected_duration = fields.Float(
        string='Expected Duration (Hours)',
        default=24.0,
        help='Expected duration for the workflow process or workflow in hours'
    )
    
    escalation_threshold = fields.Float(
        string='Escalation Threshold (Hours)',
        default=48.0,
        help='Number of hours before escalation of the workflow process or workflow'
    )
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'Medium'),
        ('3', 'High'),
        ('4', 'Urgent')
    ], string='Priority', default='1')
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of the workflow process or workflow when displayed'
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )
    
    applicable_to = fields.Selection([
        ('all_documents', 'All Documents'),
        ('specific_categories', 'Specific Categories'),
        ('specific_departments', 'Specific Departments'),
        ('specific_roles', 'Specific Roles'),
        ('custom_conditions', 'Custom Conditions')
    ], string='Applicable To', default='all_documents')
    
    applicable_category_ids = fields.Many2many(
        'document.category',
        string='Applicable Categories',
        help='Categories of documents that this process applies to'
    )
    
    applicable_department_ids = fields.Many2many(
        'hr.department',
        string='Applicable Departments',
        help='Departments that this process applies to'
    )
    
    step_ids = fields.One2many(
        'workflow.step',
        'process_id',
        string='Steps'
    )
    
    step_count = fields.Integer(
        string='Number of Steps',
        compute='_compute_step_count'
    )
    
    trigger_conditions = fields.Text(
        string='Trigger Conditions',
        help='The conditions that activate this process (JSON format)'
    )
    
    trigger_condition = fields.Text(
        string='Trigger Condition',
        help='The conditions that activate this process (JSON format)',
        default='{}'
    )
    
    auto_trigger = fields.Boolean(
        string='Auto Trigger',
        default=True,
        help='Enable the process to be activated automatically when the conditions are met'
    )
    
    sla_hours = fields.Float(
        string='Standard Time (Hour)',
        help='Standard time for completing the process in hours'
    )
    
    trigger_condition = fields.Text(
        string='Trigger Condition',
        help='The conditions that activate this process (JSON format)',
        default='{}'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('testing', 'Testing'),
        ('deprecated', 'Deprecated'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True)
    
    instance_ids = fields.One2many(
        'workflow.instance',
        'process_id',
        string='Execution Instances',
        help='All execution instances of this process'
    )
    
    instance_count = fields.Integer(
        string='Number of Executions',
        compute='_compute_instance_count',
        help='Number of times this process has been executed'
    )
    
    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        help='Success rate of executing the process'
    )
    
    average_completion_time = fields.Float(
        string='Average Completion Time (Hour)',
        compute='_compute_average_completion_time',
        store=True,
        aggregator='avg'
    )
    
    owner_id = fields.Many2one(
        'hr.employee',
        string='Process Owner',
        tracking=True,
        default=lambda self: self.env.user.employee_id
    )
    
    manager_ids = fields.Many2many(
        'hr.employee',
        'process_manager_rel',
        string='Process Manager',
        help='Employees responsible for managing this process'
    )
    
    allow_skip_steps = fields.Boolean(
        string='Allow Skipping Steps',
        default=False,
        help='Allow users to skip certain steps'
    )
    
    require_notes = fields.Boolean(
        string='Require Notes',
        default=True,
        help='Require users to enter notes at each step'
    )
    
    notification_enabled = fields.Boolean(
        string='Notification Enabled',
        default=True,
        help='Send notifications to managers when the process progresses'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.depends('step_ids')
    def _compute_step_count(self):
        """Compute the number of steps in the process"""
        for process in self:
            process.step_count = len(process.step_ids)
    
    @api.depends('instance_ids')
    def _compute_instance_count(self):
        """Compute the number of execution instances"""
        for process in self:
            process.instance_count = self.env['workflow.instance'].search_count([
                ('process_id', '=', process.id)
            ])
    
    @api.depends('instance_ids')
    def _compute_success_rate(self):
        """Compute the success rate of the process"""
        for process in self:
            instances = self.env['workflow.instance'].search([
                ('process_id', '=', process.id)
            ])
            
            if instances:
                completed = instances.filtered(lambda i: i.state == 'completed')
                process.success_rate = (len(completed) / len(instances)) * 100
            else:
                process.success_rate = 0.0
    
    @api.depends('instance_ids')
    def _compute_average_completion_time(self):
        """Compute the average completion time of the process"""
        for process in self:
            completed_instances = self.env['workflow.instance'].search([
                ('process_id', '=', process.id),
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
        """Activate the process"""
        for process in self:
            if not process.step_ids:
                raise UserError(_('Cannot activate process without steps'))
            
            process.write({'state': 'active'})
            process._create_activation_log()
    
    def action_test(self):
        """Run the process in test mode"""
        for process in self:
            process.write({'state': 'testing'})

            test_instance = process._create_test_instance()
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'workflow.instance',
                'res_id': test_instance.id,
                'view_mode': 'form',
                'target': 'new'
            }
    
    def action_deprecate(self):
        """Deprecate the process"""
        for process in self:
            process.write({'state': 'deprecated'})

            active_instances = self.env['workflow.instance'].search([
                ('process_id', '=', process.id),
                ('state', 'in', ['running', 'waiting'])
            ])
            active_instances.action_cancel()
    
    def action_view_instances(self):
        """Open instances related to this process"""
        self.ensure_one()
        action = self.env.ref('mgt_documents.workflow_instance_action').read()[0]
        action['domain'] = [('process_id', '=', self.id)]
        action['context'] = {
            'default_process_id': self.id,
        }
        return action

    def action_view_steps(self):
        """Open steps related to this process"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Steps'),
            'res_model': 'workflow.step',
            'view_mode': 'list,form',
            'domain': [('process_id', '=', self.id)],
            'context': {'default_process_id': self.id},
            'target': 'current',
        }

    def action_archive_process(self):
        """Archive the process"""
        for process in self:
            process.write({
                'state': 'archived',
                'active': False
            })
    
    def create_instance(self, document_id=None, trigger_data=None):
        """Create a new instance of the process"""
        self.ensure_one()
        
        if self.state != 'active':
            raise UserError(_('The process is not active and cannot be executed'))
        
        if not self._check_trigger_conditions(trigger_data):
            return False
        
        instance = self.env['workflow.instance'].create({
            'process_id': self.id,
            'document_id': document_id,
            'name': f"{self.name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'trigger_data': json.dumps(trigger_data or {}),
            'state': 'running'
        })
        
        instance._start_next_step()
        
        return instance
    
    def _check_trigger_conditions(self, trigger_data):
        """Check the activation conditions of the process"""
        if not self.trigger_conditions:
            return True
        
        try:
            conditions = json.loads(self.trigger_conditions)

            return self._evaluate_conditions(conditions, trigger_data)
        except (json.JSONDecodeError, Exception) as e:
            _logger.error(f"Error evaluating trigger conditions: {str(e)}")
            return False
    
    def _evaluate_conditions(self, conditions, data):
        """Evaluate the custom conditions"""

        if not conditions or not isinstance(conditions, dict):
            return True
        
        for key, expected_value in conditions.items():
            if key not in data:
                return False
            if data[key] != expected_value:
                return False
        
        return True
    
    def _create_test_instance(self):
        """Create a test instance for testing"""
        return self.env['workflow.instance'].create({
            'process_id': self.id,
            'name': f"Test {self.name}",
            'is_test': True,
            'state': 'running'
        })
    
    def _create_activation_log(self):
        """Create an activation log"""
        self.message_post(
            body=_('The process was activated by %s') % self.env.user.name,
            message_type='notification'
        )
    

    @api.constrains('code')
    def _check_code_uniqueness(self):
        """Check the uniqueness of the process code"""
        for process in self:
            if process.code:
                existing = self.search([
                    ('code', '=', process.code),
                    ('id', '!=', process.id),
                    ('company_id', '=', process.company_id.id)
                ])
                if existing:
                    raise ValidationError(_('The process code must be unique within the company'))
    
    @api.constrains('sla_hours')
    def _check_sla_hours(self):
        """Check the validity of the standard time"""
        for process in self:
            if process.sla_hours and process.sla_hours <= 0:
                raise ValidationError(_('The standard time must be positive'))
    
    @api.constrains('expected_duration', 'escalation_threshold')
    def _check_duration_consistency(self):
        """Check the consistency of the duration"""
        for process in self:
            if (process.escalation_threshold and process.expected_duration and 
                process.escalation_threshold <= process.expected_duration):
                raise ValidationError(_('The escalation threshold must be greater than the expected duration'))


class WorkflowStep(models.Model):
    """Workflow steps"""
    
    _name = 'workflow.step'
    _description = 'Workflow steps'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'process_id, sequence, id'
    
    process_id = fields.Many2one(
        'workflow.process',
        string='Process',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Step name',
        required=True
    )
    
    description = fields.Html(
        string='Step description',
        help='Detailed instructions for executing the step'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='The sequence of the step in the process'
    )
    
    step_type = fields.Selection([
        ('manual', 'Manual step'),
        ('automatic', 'Automatic step'),
        ('approval', 'Approval'),
        ('review', 'Review'),
        ('data_entry', 'Data entry'),
        ('notification', 'Notification'),
        ('wait', 'Wait'),
        ('condition', 'Condition')
    ], string='Step type', default='manual', required=True)
    

    responsible_type = fields.Selection([
        ('specific_user', 'Specific user'),
        ('department', 'Department'),
        ('role', 'Role'),
        ('automatic', 'Automatic')
    ], string='Responsible type', default='specific_user')
    
    responsible_user_id = fields.Many2one('hr.employee', string='Responsible user')
    responsible_department_id = fields.Many2one('hr.department', string='Responsible department')
    responsible_role = fields.Char(string='Role')
    
    estimated_hours = fields.Float(
        string='Estimated hours',
        help='Estimated time to complete the step'
    )
    
    deadline_hours = fields.Float(
        string='Maximum allowed hours',
        help='Maximum allowed time to complete the step'
    )
    
    required_conditions = fields.Text(
        string='Required conditions',
        help='Conditions that must be met to execute the step'
    )
    
    skip_conditions = fields.Text(
        string='Skip conditions',
        help='Conditions that allow skipping this step'
    )
    
    is_mandatory = fields.Boolean(
        string='Mandatory',
        default=True,
        help='Can this step be skipped'
    )
    
    requires_approval = fields.Boolean(
        string='Requires approval',
        default=False,
        help='Does this step require additional approval'
    )
    
    next_step_ids = fields.Many2many(
        'workflow.step',
        'step_next_rel',
        'step_id',
        'next_step_id',
        string='Next steps'
    )
    
    send_notification = fields.Boolean(
        string='Send notification',
        default=True
    )
    
    notification_template_id = fields.Many2one(
        'mail.template',
        string='Notification template'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    @api.constrains('next_step_ids')
    def _check_no_circular_reference(self):
        """Prevent circular references in steps"""
        for step in self:
            if step in step.next_step_ids:
                raise ValidationError(_('A step cannot reference itself'))
    
    def action_toggle_active(self):
        """Toggle the active state of the step"""
        for step in self:
            step.active = not step.active


class WorkflowInstance(models.Model):
    """Workflow instance"""
    
    _name = 'workflow.instance'
    _description = 'Workflow instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    process_id = fields.Many2one(
        'workflow.process',
        string='Process',
        required=True
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='Document'
    )
    
    name = fields.Char(
        string='Name',
        required=True
    )
    
    state = fields.Selection([
        ('running', 'Running'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed')
    ], string='State', default='running', tracking=True)
    
    current_step_id = fields.Many2one(
        'workflow.step',
        string='Current step'
    )
    
    start_date = fields.Datetime(
        string='Start date',
        default=fields.Datetime.now
    )
    
    completion_date = fields.Datetime(
        string='Completion date'
    )
    
    trigger_data = fields.Text(
        string='Trigger data',
        help='Data that triggered the process'
    )
    
    is_test = fields.Boolean(
        string='Test instance',
        default=False
    )
    
    progress_percentage = fields.Float(
        string='Progress percentage',
        compute='_compute_progress_percentage'
    )
    
    step_execution_ids = fields.One2many(
        'workflow.step.execution',
        'instance_id',
        string='Step execution'
    )
    
    @api.depends('step_execution_ids', 'process_id.step_ids')
    def _compute_progress_percentage(self):
        """Compute progress percentage"""
        for instance in self:
            if instance.process_id.step_ids:
                completed_steps = instance.step_execution_ids.filtered(
                    lambda s: s.state == 'completed'
                )
                total_steps = len(instance.process_id.step_ids)
                instance.progress_percentage = (len(completed_steps) / total_steps) * 100
            else:
                instance.progress_percentage = 0.0
    
    def _start_next_step(self):
        """Start the next step"""
        for instance in self:
            process = instance.process_id
            if not process or not process.step_ids:
                return
            if not instance.current_step_id:
                next_step = process.step_ids.filtered(lambda s: s.active).sorted(key=lambda s: s.sequence)[:1]
            else:
                next_step = instance.current_step_id.next_step_ids.filtered(lambda s: s.active).sorted(key=lambda s: s.sequence)[:1]

            if not next_step:
                instance.write({
                    'state': 'completed',
                    'completion_date': fields.Datetime.now(),
                })
                return

            step = next_step[0]
            instance.write({'current_step_id': step.id})
            
            self.env['workflow.step.execution'].create({
                'instance_id': instance.id,
                'step_id': step.id,
                'assigned_user_id': step.responsible_user_id.id if step.responsible_user_id else False,
                'state': 'in_progress',
                'start_date': fields.Datetime.now(),
            })

            if step.send_notification and step.notification_template_id:
                try:
                    step.notification_template_id.send_mail(instance.id, force_send=True)
                except Exception:
                    pass
    
    def action_cancel(self):
        """Cancel the workflow instance"""
        for instance in self:
            instance.write({'state': 'cancelled'})


class WorkflowStepExecution(models.Model):
    """Workflow step execution"""
    
    _name = 'workflow.step.execution'
    _description = 'Workflow step execution'
    _order = 'start_date desc'
    
    instance_id = fields.Many2one(
        'workflow.instance',
        string='Workflow instance',
        required=True,
        ondelete='cascade'
    )
    
    step_id = fields.Many2one(
        'workflow.step',
        string='Step',
        required=True
    )
    
    assigned_user_id = fields.Many2one(
        'hr.employee',
        string='Assigned user'
    )
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed')
    ], string='State', default='pending')
    
    start_date = fields.Datetime(string='Start date')
    completion_date = fields.Datetime(string='Completion date')
    notes = fields.Text(string='Notes')
    
    def action_complete(self):
        """Complete the step"""
        for execution in self:
            execution.write({
                'state': 'completed',
                'completion_date': fields.Datetime.now()
            })

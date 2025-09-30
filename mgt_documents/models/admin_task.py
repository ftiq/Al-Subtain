# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AdministrativeTask(models.Model):
    """Administrative Tasks Form"""
    
    _name = 'admin.task'
    _description = 'Administrative Tasks Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, due_date asc, id desc'
    _rec_name = 'name'
    

    request_document_id = fields.Many2one(
        'document.document', 
        string='Related Document',
        tracking=True,
        help='The document that this task was created from'
    )
    
    process_id = fields.Many2one(
        'workflow.process', 
        string='Related Process',
        help='The process or workflow associated with this task'
    )
    
    process_instance_id = fields.Many2one(
        'document.workflow.instance',
        string='Process Instance',
        help='The current process instance associated with this task'
    )
    

    name = fields.Char(
        string='Task Name',
        required=True,
        tracking=True
    )
    
    description = fields.Html(
        string='Task Description',
        help='Detailed description of the task and what needs to be done'
    )
    
    task_type = fields.Selection([
        ('review_document', 'Review Document'),
        ('approve_request', 'Approve Request'),
        ('execute_action', 'Execute Action'),
        ('prepare_response', 'Prepare Response'),
        ('forward_document', 'Forward Document'),
        ('data_entry', 'Data Entry'),
        ('verification', 'Verification'),
        ('archive_document', 'Archive Document'),
        ('follow_up', 'Follow Up'),
        ('other', 'Other')
    ], string='Task Type', default='review_document', tracking=True)
    

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
        ('4', 'Critical')
    ], string='Priority', default='1', tracking=True)
    
    due_date = fields.Datetime(
        string='Due Date',
        required=True,
        tracking=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=3)
    )
    

    assigned_department_id = fields.Many2one(
        'hr.department',
        string='Assigned Department',
        tracking=True
    )
    
    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='Assigned Employee',
        tracking=True,
        domain="[('department_id', '=', assigned_department_id), ('active', '=', True)]"
    )
    
    assigned_by = fields.Many2one(
        'hr.employee',
        string='Assigned By',
        default=lambda self: self.env.user.employee_id,
        tracking=True
    )
    
    assigned_date = fields.Datetime(
        default=fields.Datetime.now,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold')
    ], string='State', default='draft', tracking=True)
    
    progress_percentage = fields.Float(
        string='Progress Percentage',
        default=0.0,
        help='Updated manually or through scheduled tasks'
    )
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Related Approval Request',
        help='The approval request that led to the creation of this task'
    )
    
    execution_notes = fields.Html(
        string='Execution Notes',
        help='Notes about how the task was executed'
    )
    
    completion_date = fields.Datetime(
        string='Completion Date',
        readonly=True
    )
    
    result_summary = fields.Text(
        string='Result Summary',
        help='A brief summary of the task result'
    )
    
    parent_task_id = fields.Many2one(
        'admin.task',
        string='Parent Task',
        help='The parent task if this is a subtask'
    )
    
    subtask_ids = fields.One2many(
        'admin.task',
        'parent_task_id',
        string='Subtasks'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_overdue_status',
        store=True
    )
    
    @api.depends('due_date', 'state')
    def _compute_overdue_status(self):
        now = fields.Datetime.now()
        for task in self:
            task.is_overdue = (
                bool(task.due_date)
                and task.due_date < now
                and task.state not in ['completed', 'cancelled']
            )
    
    def action_assign(self):
        """Assign the task"""
        self.write({'state': 'assigned'})
    
    def action_start(self):
        """Start executing the task"""
        self.write({'state': 'in_progress'})
    
    def action_complete(self):
        """Complete the task"""
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now(),
        })
    
    def action_cancel(self):
        """Cancel the task"""
        self.write({'state': 'cancelled'})
    
    def action_hold(self):
        """Hold the task"""
        self.write({'state': 'on_hold'})
    
    def action_resume(self):
        """Resume the task"""
        self.write({'state': 'assigned'})
    
    @api.model
    def send_due_task_reminders(self):
        """Cron: Send due task reminders for tasks due within 24 hours"""
        now = fields.Datetime.now()
        soon = now + timedelta(hours=24)
        tasks = self.search([
            ('state', 'in', ['assigned', 'in_progress']),
            ('due_date', '>=', now),
            ('due_date', '<=', soon),
        ], limit=500)
        for task in tasks:
            try:
                body = _('Reminder: Task "%s" is due on %s') % (task.name, task.due_date)
                task.message_post(body=body, message_type='notification')
            except Exception:
                continue
        return True
    
    @api.constrains('parent_task_id')
    def _check_recursion(self):
        """Prevent circular task recursion"""
        for task in self:
            if task.parent_task_id:
                current = task.parent_task_id
                visited = set()
                while current:
                    if current.id in visited:
                        raise ValidationError(_('Cannot create nested tasks'))
                    visited.add(current.id)
                    current = current.parent_task_id
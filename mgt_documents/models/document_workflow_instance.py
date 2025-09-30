# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import uuid
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class DocumentWorkflowInstance(models.Model):
    """Document workflow instance"""
    
    _name = 'document.workflow.instance'
    _description = 'Document workflow instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Instance Name',
        required=True,
        tracking=True
    )
    
    workflow_process_id = fields.Many2one(
        'workflow.process',
        string='Workflow Process',
        required=True,
        tracking=True
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='Related Document',
        tracking=True
    )
    
    state = fields.Selection([
        ('initiated', 'Initiated'),
        ('running', 'Running'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed')
    ], string='State', default='initiated', tracking=True, required=True)
    
    start_date = fields.Datetime(
        string='Start Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    completion_date = fields.Datetime(
        string='Completion Date',
        tracking=True
    )
    
    due_date = fields.Datetime(
        string='Due Date',
        compute='_compute_due_date',
        store=True,
        help='The expected completion date of the process'
    )
    
    current_step_id = fields.Many2one(
        'process.step',
        string='Current Step',
        tracking=True
    )
    
    current_step_name = fields.Char(
        string='Current Step Name',
        related='current_step_id.name',
        store=True
    )
    
    admin_task_ids = fields.One2many(
        'admin.task',
        'process_instance_id',
        string='Admin Tasks',
        help='Tasks generated from this process'
    )
    
    active_tasks_count = fields.Integer(
        string='Active Tasks Count',
        compute='_compute_tasks_count',
        store=True
    )
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'Important'),
        ('3', 'Urgent'),
        ('4', 'Critical')
    ], string='Priority', default='1', tracking=True)
    
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_overdue_status',
        store=True
    )
    
    trigger_data = fields.Text(
        string='Trigger Data',
        help='Data that triggered the process',
        default='{}'
    )
    
    result_summary = fields.Text(
        string='Result Summary',
        help='A summary of the process result'
    )
    
    @api.depends('workflow_process_id.expected_duration', 'start_date')
    def _compute_due_date(self):
        for instance in self:
            if instance.start_date and instance.workflow_process_id.expected_duration:
                instance.due_date = instance.start_date + timedelta(
                    hours=instance.workflow_process_id.expected_duration
                )
            else:
                instance.due_date = False
    
    @api.depends('admin_task_ids.state')
    def _compute_tasks_count(self):
        for instance in self:
            active_tasks = instance.admin_task_ids.filtered(
                lambda t: t.state not in ['completed', 'cancelled']
            )
            instance.active_tasks_count = len(active_tasks)
    
    @api.depends('due_date', 'state')
    def _compute_overdue_status(self):
        now = fields.Datetime.now()
        for instance in self:
            instance.is_overdue = (
                instance.due_date
                and instance.due_date < now
                and instance.state not in ['completed', 'cancelled']
            )
    def action_start(self):
        """Start process execution"""
        self.write({'state': 'running', 'start_date': fields.Datetime.now()})
    
    def action_complete(self):
        """Complete process"""
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
    
    def action_cancel(self):
        """Cancel process"""
        self.write({'state': 'cancelled'})
    
    def action_view_tasks(self):
        """View tasks associated with this process instance"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'admin.task',
            'view_mode': 'kanban,list,form',
            'domain': [('process_instance_id', '=', self.id)],
            'context': {'default_process_instance_id': self.id},
            'target': 'current',
        }

    @api.model
    def check_overdue_instances(self):
        """Cron: escalate or notify overdue workflow instances."""
        overdue = self.search([
            ('is_overdue', '=', True),
            ('state', 'in', ['running', 'waiting'])
        ], limit=200)
        for inst in overdue:
            try:
                inst.message_post(body=_('Overdue workflow instance, please follow up.'))
            except Exception:

                continue
        return True

    @api.model
    def cleanup_test_instances(self):
        """Cron: delete old completed test instances to keep DB light."""
        threshold = fields.Datetime.now() - timedelta(days=30)
        tests = self.search([
            ('is_test', '=', True),
            ('completion_date', '!=', False),
            ('completion_date', '<', threshold)
        ])
        try:
            tests.unlink()
        except Exception:

            pass
        return True
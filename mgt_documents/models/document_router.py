# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class DocumentRouter(models.Model):
    """Document Router"""
    
    _name = 'document.router'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Document Router'
    _order = 'priority desc, sequence asc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the document router'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence of the document router'
    )
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True)
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )

    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')
    ], string='State', default='inactive', tracking=True)

    filter_document_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('internal', 'Internal'),
        ('circular', 'Circular'),
        ('memo', 'Memo'),
        ('report', 'Report'),
        ('request', 'Request'),
        ('letter', 'Letter'),
        ('contract', 'Contract'),
        ('other', 'أخرى')
    ], string='Document Type', help='Document type to apply this rule on')
    
    filter_priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
        ('4', 'Emergency')
    ], string='Priority', help='Priority required to apply this rule')
    
    filter_departments = fields.Many2many(
        'hr.department',
        'router_filter_dept_rel',
        'router_id',
        'department_id',
        string='Departments',
        help='Apply this rule only on documents from these departments'
    )
    
    filter_keywords = fields.Char(
        string='Keywords',
        help='Keywords in the document name (separated by commas)'
    )

    applicable_category_ids = fields.Many2many(
        'document.category',
        'document_router_category_rel',
        'router_id',
        'category_id',
        string='Categories'
    )

    applicable_department_ids = fields.Many2many(
        'hr.department',
        'document_router_dept_rel',
        'router_id',
        'department_id',
        string='Departments'
    )

    target_process_id = fields.Many2one(
        'workflow.process',
        string='Target Process',
        help='Process to be executed when this rule is applied'
    )

    task_template = fields.Text(
        string='Task Template',
        help='Template for the task to be created'
    )

    notification_message = fields.Char(
        string='Notification Message',
        help='Message to be sent when this rule is applied'
    )

    create_approval_request = fields.Boolean(
        string='Create Approval Request',
        default=False,
        help='Create an approval request automatically'
    )

    approval_category_id = fields.Many2one(
        'approval.category',
        string='Approval Category',
        help='Category of the approval request to be created'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    def action_activate(self):
        """Activate the rule"""
        self.write({'state': 'active', 'active': True})

    def action_deactivate(self):
        """Deactivate the rule"""
        self.write({'state': 'inactive', 'active': False})
    
    def matches_document(self, document):
        """Check if the rule applies to the document"""
        self.ensure_one()
        
        if not self.active or self.state != 'active':
            return False
        
        if self.filter_document_type and document.document_type != self.filter_document_type:
            return False
        
        if self.filter_priority and document.priority != self.filter_priority:
            return False
        
        if self.filter_departments and document.department_id not in self.filter_departments:
            return False
        
        if self.filter_keywords:
            keywords = [k.strip() for k in self.filter_keywords.split(',')]
            document_text = (document.name or '').lower()
            if not any(keyword.lower() in document_text for keyword in keywords):
                return False
        
        return True
    
    def apply_to_document(self, document):
        """Apply the rule to the document"""
        self.ensure_one()
        
        if not self.matches_document(document):
            return False
        
        results = []
        
        if self.target_process_id:
            try:
                instance = self.target_process_id.create_instance(
                    document_id=document.id,
                    trigger_data={'router_rule_id': self.id}
                )
                results.append(f"Created workflow instance: {instance.name}")
            except Exception as e:
                _logger.error(f"Error creating workflow instance: {str(e)}")
        
        if self.task_template:
            try:
                task = self.env['admin.task'].create({
                    'name': f"Task from router rule: {self.name}",
                    'description': self.task_template,
                    'request_document_id': document.id,
                    'assigned_department_id': self.applicable_department_ids[0].id if self.applicable_department_ids else False,
                    'priority': self.filter_priority or '1',
                })
                results.append(f"Created task: {task.name}")
            except Exception as e:
                _logger.error(f"Error creating task: {str(e)}")
        
        if self.create_approval_request and self.approval_category_id:
            try:
                approval = self.env['approval.request'].create({
                    'name': f"Approval request from router rule: {self.name}",
                    'category_id': self.approval_category_id.id,
                    'document_id': document.id,
                    'request_owner_id': self.env.user.id,
                })
                results.append(f"Created approval request: {approval.name}")
            except Exception as e:
                _logger.error(f"Error creating approval request: {str(e)}")
        
        if self.notification_message:
            try:
                document.message_post(
                    body=self.notification_message,
                    message_type='notification'
                )
                results.append("Notification sent")
            except Exception as e:
                _logger.error(f"Error sending notification: {str(e)}")
        
        return {
            'success': bool(results),
            'message': '\n'.join(results) if results else _('No matching rules found'),
            'actions': results,
        }
    
    @api.model
    def process_document(self, document):
        """Process document with all matching rules and return a unified result"""
        active_rules = self.search([
            ('active', '=', True),
            ('state', '=', 'active')
        ], order='priority desc, sequence asc')
        
        actions = []
        for rule in active_rules:
            try:
                rule_results = rule.apply_to_document(document)
                if rule_results:
                    actions.extend(rule_results)
            except Exception as e:
                _logger.error(f"Error applying rule {rule.name}: {str(e)}")
                continue
        
        message = '\n'.join(actions) if actions else _('No matching rules found')
        return {
            'success': bool(actions),
            'message': message,
            'actions': actions,
        }

    @api.model
    def auto_route_new_documents(self):
        """Cron: find newly registered documents and try to route them using active rules."""
        docs = self.env['document.document'].search([
            ('processing_state', 'in', ['received', 'registered'])
        ], limit=100)
        for doc in docs:
            try:
                self.process_document(doc)
            except Exception:

                continue
        return True
    
    @api.constrains('filter_departments', 'applicable_department_ids')
    def _check_departments(self):
        """Check if the departments are valid"""
        for rule in self:
            if rule.filter_departments and rule.applicable_department_ids:
                if not set(rule.filter_departments.ids).intersection(set(rule.applicable_department_ids.ids)):
                    raise ValidationError(_('The applicable departments must include at least one department from the specified departments'))
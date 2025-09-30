# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    """Extend the employee model to add document management functions"""
    
    _inherit = 'hr.employee'
    

    is_document_approver = fields.Boolean(
        string='Document Approver',
        default=False,
        help='Whether the employee can approve documents'
    )
    
    approval_authority_level = fields.Selection([
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('executive', 'Executive')
    ], string='Approval Authority Level', default='basic',
       help='Approval authority level for document approval')
    
    document_categories_ids = fields.Many2many(
        'document.category',
        'employee_document_category_rel',
        'employee_id',
        'document_category_id',
        string='Document Categories',
        help='Document categories the employee can handle'
    )
    

    delegate_approvals_to = fields.Many2one(
        'hr.employee',
        string='Delegate Approvals To',
        help='Employee to delegate approvals to'
    )
    
    delegation_start_date = fields.Date(
        string='Delegation Start Date',
        help='Start date of delegation'
    )
    
    delegation_end_date = fields.Date(
        string='Delegation End Date',
        help='End date of delegation'
    )
    
    employee_type = fields.Selection(
        selection_add=[
            ('secretary', 'Secretary/Document Management'),
            ('manager', 'Manager'),
            ('department_head', 'Department Head'),
            ('executive', 'Executive')
        ],
        ondelete={
            'secretary': 'set default',
            'manager': 'set default', 
            'department_head': 'set default',
            'executive': 'set default'
        }
    )
    
    can_assign_tasks = fields.Boolean(
        string='Can Assign Tasks',
        default=False
    )
    
    task_assignment_scope = fields.Selection([
        ('department', 'Department Only'),
        ('subordinates', 'Subordinates Only'),
        ('all_departments', 'All Departments')
    ], string='Task Assignment Scope', default='department')
    
    can_handle_incoming = fields.Boolean(
        string='Can Handle Incoming',
        default=False
    )
    
    can_handle_outgoing = fields.Boolean(
        string='Can Handle Outgoing',
        default=False
    )
    
    document_access_level = fields.Selection([
        ('restricted', 'Restricted'),
        ('departmental', 'Departmental'),
        ('general', 'General'),
        ('confidential', 'Confidential')
    ], string='Document Access Level', default='restricted')
    
    assigned_tasks = fields.One2many(
        'admin.task', 
        'assigned_employee_id',
        string='Assigned Tasks'
    )
    
    active_tasks_count = fields.Integer(
        string='Active Tasks Count',
        compute='_compute_tasks_count'
    )
    
    approval_authority_types = fields.Many2many(
        'document.category',
        'employee_approval_category_rel', 
        'employee_id',
        'category_id',
        string='Approval Authority Types'
    )
    
    delegation_reason = fields.Text(
        string='Delegation Reason',
        help='Reason for delegation (vacation, travel, etc.)'
    )
    

    documents_created_count = fields.Integer(
        string='Documents Created Count',
        compute='_compute_document_statistics'
    )
    
    documents_received_count = fields.Integer(
        string='Documents Received Count',
        compute='_compute_document_statistics'
    )
    
    documents_sent_count = fields.Integer(
        string='Documents Sent Count',
        compute='_compute_document_statistics'
    )
    
    approvals_pending_count = fields.Integer(
        string='Approvals Pending Count',
        compute='_compute_document_statistics'
    )
    
    approvals_completed_count = fields.Integer(
        string='Approvals Completed Count',
        compute='_compute_document_statistics'
    )
    
    documents_count = fields.Integer(
        string='Documents Count',
        compute='_compute_documents_stats'
    )
    
    @api.depends('assigned_tasks')
    def _compute_tasks_count(self):
        """Compute active tasks count"""
        for employee in self:
            active_tasks = employee.assigned_tasks.filtered(
                lambda t: t.state not in ['completed', 'cancelled']
            )
            employee.active_tasks_count = len(active_tasks)
    
    @api.depends('name')
    def _compute_document_statistics(self):
        """Compute document statistics for the employee"""
        for employee in self:

            employee.documents_created_count = self.env['document.document'].search_count([
                ('sender_employee_id', '=', employee.id)
            ])
            

            employee.documents_received_count = self.env['document.document'].search_count([
                ('recipient_employee_id', '=', employee.id)
            ])
            

            employee.documents_sent_count = self.env['document.document'].search_count([
                ('sender_employee_id', '=', employee.id),
                ('document_type', 'in', ['outgoing', 'internal'])
            ])
            

            employee.approvals_pending_count = self.env['approval.request'].search_count([
                ('approver_ids.employee_id', '=', employee.id),
                ('request_status', '=', 'pending')
            ])
            

            employee.approvals_completed_count = self.env['approval.request'].search_count([
                ('approver_ids.employee_id', '=', employee.id),
                ('request_status', 'in', ['approved', 'rejected'])
            ])
            


            pass
    
    @api.depends('name')
    def _compute_documents_stats(self):
        """Compute document statistics for the employee"""
        for employee in self:
            employee.documents_count = self.env['document.document'].search_count([
                ('approver_ids.employee_id', '=', employee.id)
            ])
    
    def is_delegation_active(self):
        """Check if delegation is active"""
        self.ensure_one()
        
        if not self.delegate_approvals_to:
            return False
        
        today = fields.Date.today()
        
        if self.delegation_start_date and self.delegation_start_date > today:
            return False
        
        if self.delegation_end_date and self.delegation_end_date < today:
            return False
        
        return True
    
    @api.onchange('delegate_approvals_to')
    def _onchange_delegate_approvals_to(self):
        """Set default delegation dates"""
        if self.delegate_approvals_to and not self.delegation_start_date:
            self.delegation_start_date = fields.Date.today()
        if self.delegate_approvals_to and not self.delegation_end_date:
            self.delegation_end_date = fields.Date.today() + timedelta(days=30)
    
    @api.onchange('employee_type')
    def _onchange_employee_type(self):
        """Set permissions based on employee type"""
        if self.employee_type in ['manager', 'department_head', 'executive']:
            self.can_assign_tasks = True
            self.is_document_approver = True
            
        if self.employee_type == 'secretary':
            self.can_handle_incoming = True
            self.can_handle_outgoing = True
            self.document_access_level = 'general'
            
        if self.employee_type == 'executive':
            self.task_assignment_scope = 'all_departments'
            self.document_access_level = 'confidential'
    
    def get_effective_approver(self):
        """Get the effective approver (taking delegation into account)"""
        self.ensure_one()
        
        if self.is_delegation_active():
            return self.delegate_approvals_to
        
        return self
    
    def can_approve_category(self, category):
        """Check if the employee can approve a specific document category"""
        self.ensure_one()
        
        if not self.is_document_approver:
            return False
        
        if self.document_categories_ids:
            return category in self.document_categories_ids
        
        return True
    
    def get_approval_authority_documents(self):
        """Get the documents that the employee can approve"""
        self.ensure_one()
        
        if not self.is_document_approver:
            return self.env['document.document']
        
        domain = []
        
        if self.approval_authority_level != 'executive':
            if self.department_id:
                domain.append(('department_id', '=', self.department_id.id))
            else:
                return self.env['document.document']
        
        if self.document_categories_ids:
            domain.append(('category_id', 'in', self.document_categories_ids.ids))
        
        domain.append(('state', 'in', ['submitted', 'in_review']))
        
        return self.env['document.document'].search(domain)
    
    def get_subordinate_documents(self):
        """Get the documents of subordinates"""
        self.ensure_one()
        
        subordinates = self.env['hr.employee'].search([
            ('parent_id', '=', self.id)
        ])
        
        if not subordinates:
            return self.env['document.document']
        
        return self.env['document.document'].search([
            ('sender_employee_id', 'in', subordinates.ids)
        ])
    
    def create_delegation(self, delegate_to, start_date, end_date, reason):
        """Create a new delegation"""
        self.ensure_one()
        
        if not delegate_to.is_document_approver:
            raise UserError(_('The delegate must have document approval permission'))
        
        self.write({
            'delegate_approvals_to': delegate_to.id,
            'delegation_start_date': start_date,
            'delegation_end_date': end_date,
            'delegation_reason': reason,
        })
        
        self.env['mail.message'].create({
            'subject': _('Delegation of document approval'),
            'body': _('You have been delegated to approve documents on behalf of %s from %s to %s') % (
                self.name, start_date, end_date
            ),
            'model': 'hr.employee',
            'res_id': delegate_to.id,
            'message_type': 'notification',
        })
    
    def cancel_delegation(self):
        """Cancel delegation"""
        self.ensure_one()
        
        if self.delegate_approvals_to:
            self.env['mail.message'].create({
                'subject': _('Delegation of document approval'),
                'body': _('The delegation of document approval has been canceled for %s') % self.name,
                'model': 'hr.employee',
                'res_id': self.delegate_approvals_to.id,
                'message_type': 'notification',
            })
        
        self.write({
            'delegate_approvals_to': False,
            'delegation_start_date': False,
            'delegation_end_date': False,
            'delegation_reason': False,
        })
    
    def action_view_my_documents(self):
        """View documents of the employee"""
        self.ensure_one()
        
        return {
            'name': _('My Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [
                '|', '|',
                ('sender_employee_id', '=', self.id),
                ('recipient_employee_id', '=', self.id),
                ('create_uid', '=', self.user_id.id if self.user_id else 0)
            ],
        }
    
    def action_view_pending_approvals(self):
        """View pending approvals"""
        self.ensure_one()
        
        return {
            'name': _('Pending Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('approver_ids.employee_id', '=', self.id),
                ('request_status', 'in', ['new', 'pending', 'under_approval'])
            ],
        }
    
    def action_view_subordinate_documents(self):
        """View subordinate documents"""
        self.ensure_one()
        
        subordinate_docs = self.get_subordinate_documents()
        
        return {
            'name': _('Subordinate Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', subordinate_docs.ids)],
        }
    
    def action_create_delegation(self):
        """Create a new delegation"""
        self.ensure_one()
        
        return {
            'name': _('Create Delegation'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.delegation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delegator_id': self.id,
            }
        }
    


    @api.constrains('delegate_approvals_to')
    def _check_delegation_loop(self):
        """Check for delegation loop"""
        for employee in self:
            if employee.delegate_approvals_to:
        
                if employee.delegate_approvals_to.delegate_approvals_to == employee:
                    raise ValidationError(_('Cannot create a delegation loop'))
    
    @api.constrains('delegation_start_date', 'delegation_end_date')
    def _check_delegation_dates(self):
        """Check delegation dates"""
        for employee in self:
            if employee.delegation_start_date and employee.delegation_end_date:
                if employee.delegation_start_date > employee.delegation_end_date:
                    raise ValidationError(_('Delegation start date cannot be after delegation end date')) 
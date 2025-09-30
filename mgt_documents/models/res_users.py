# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResUsers(models.Model):
    """Extend the user model to add document management features"""
    
    _inherit = 'res.users'



    
    can_approve_documents = fields.Boolean(
        string='Can approve documents',
        default=False,
        help='Whether the user can approve documents'
    )
    
    approval_limit = fields.Selection([
        ('unlimited', 'Unlimited'),
        ('department', 'Department only'),
        ('team', 'Team only'),
        ('none', 'None')
    ], string='Approval limit', default='none', 
       help='Scope of document approval permissions')
    

    notify_document_approval = fields.Boolean(
        string='Notify document approvals',
        default=True,
        help='Send notifications when there are document approval requests'
    )
    
    notify_document_updates = fields.Boolean(
        string='Notify document updates',
        default=True,
        help='Send notifications when there are document updates'
    )
    
    notify_document_expiry = fields.Boolean(
        string='Notify document expiry',
        default=True,
        help='Send notifications before document expiry'
    )
    

    documents_created_count = fields.Integer(
        string='Number of documents created',
        compute='_compute_document_statistics'
    )
    
    documents_approved_count = fields.Integer(
        string='Number of documents approved',
        compute='_compute_document_statistics'
    )
    
    pending_approvals_count = fields.Integer(
        string='Number of pending approvals',
        compute='_compute_document_statistics'
    )
    

    

    is_sample_receipt_approver = fields.Boolean(
        string='Sample Receipt Approver',
        default=False,
        help='Technical field to fix view validation error'
    )
    

    @api.depends('name')
    def _compute_document_statistics(self):
        """Compute document statistics for the user"""
        for user in self:

            user.documents_created_count = self.env['document.document'].search_count([
                ('create_uid', '=', user.id)
            ])
            

            user.documents_approved_count = self.env['approval.request'].search_count([
                ('approver_ids.user_id', '=', user.id),
                ('request_status', '=', 'approved')
            ])
            

            user.pending_approvals_count = self.env['approval.request'].search_count([
                ('approver_ids.user_id', '=', user.id),
                ('request_status', '=', 'pending')
            ])
            


            pass
    

    def get_accessible_documents(self):
        """Get documents accessible to the user"""
        self.ensure_one()
        
        domain = []
        

        pass
        
        return self.env['document.document'].search(domain)
    
    def can_approve_document(self, document):
        """Check if the user can approve the document"""
        self.ensure_one()
        
        if not self.can_approve_documents:
            return False
        
        if self.approval_limit == 'unlimited':
            return True
        elif self.approval_limit == 'department':
            return (
                self.employee_id and 
                self.employee_id.department_id and
                document.department_id == self.employee_id.department_id
            )
        elif self.approval_limit == 'team':
            return (
                self.employee_id and
                document.sender_employee_id and
                self.employee_id.department_id == document.sender_employee_id.department_id
            )
        
        return False
    
    def get_pending_approvals(self):
        """Get pending approvals for the user"""
        self.ensure_one()
        
        return self.env['approval.request'].search([
            ('approver_ids.user_id', '=', self.id),
            ('request_status', '=', 'pending')
        ])
    

    

    def action_view_my_documents(self):
        """View documents for the user"""
        self.ensure_one()
        
        accessible_docs = self.get_accessible_documents()
        
        return {
            'name': _('My Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', accessible_docs.ids)],
            'context': {'default_create_uid': self.id}
        }
    
    def action_view_pending_approvals(self):
        """View pending approvals for the user"""
        self.ensure_one()
        
        return {
            'name': _('Pending Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('approver_ids.user_id', '=', self.id),
                ('request_status', 'in', ['new', 'pending', 'under_approval'])
            ],
        }
    

    
 
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DocumentHistory(models.Model):
    """Document History Model"""
    
    _name = 'document.history'
    _description = 'Document History'
    _order = 'timestamp desc, id desc'
    _rec_name = 'display_name'
    

    document_id = fields.Many2one(
        'document.document',
        string='Document',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        index=True
    )
    
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    action = fields.Selection([
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('deleted', 'Deleted'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('reset', 'Reset'),
        ('archived', 'Archived'),
        ('cancelled', 'Cancelled'),
        ('restored', 'Restored'),
        ('signed', 'Signed'),
        ('completed', 'Completed'),
        ('attachment_added', 'Attachment Added'),
        ('attachment_removed', 'Attachment Removed'),
        ('comment_added', 'Comment Added'),
        ('access_granted', 'Access Granted'),
        ('access_revoked', 'Access Revoked'),
        ('other', 'Other')
    ], string='Action', required=True, index=True)
    
    description = fields.Text(
        string='Description',
        required=True
    )
    

    previous_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('in_progress', 'In Progress'),
        ('pending_approval', 'Pending Approval'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
        ('received', 'Received'),
        ('registered', 'Registered'),
        ('routed', 'Routed'),
        ('under_review', 'Under Review'),
        ('in_execution', 'In Execution'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold')
    ], string='Previous State')
    
    new_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('in_progress', 'In Progress'),
        ('pending_approval', 'Pending Approval'),
        ('waiting_approval', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived'),
        ('received', 'Received'),
        ('registered', 'Registered'),
        ('routed', 'Routed'),
        ('under_review', 'Under Review'),
        ('in_execution', 'In Execution'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold')
    ], string='New State')
    

    field_changes = fields.Text(
        string='Field Changes',
        help='Details of the fields that were changed'
    )
    
    ip_address = fields.Char(
        string='IP Address',
        help='IP Address of the user when the change was made'
    )
    
    user_agent = fields.Char(
        string='معلومات المتصفح',
        help='معلومات المتصفح المستخدم'
    )
    

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Attachment',
        help='Attachment related to this change (if any)'
    )
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='Approval Request',
        help='Approval request related to this change (if any)'
    )
    


    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name'
    )
    
    document_name = fields.Char(
        string='Document Name',
        related='document_id.name',
        store=True
    )
    
    document_reference = fields.Char(
        string='Document Reference',
        related='document_id.reference_number',
        store=True
    )
    
    user_name = fields.Char(
        string='User Name',
        related='user_id.name',
        store=True
    )
    

    @api.depends('action', 'timestamp', 'user_id.name')
    def _compute_display_name(self):
        """Compute the display name for the record"""
        for record in self:
            action_name = dict(record._fields['action'].selection).get(record.action, record.action)
            timestamp_str = record.timestamp.strftime('%Y-%m-%d %H:%M') if record.timestamp else ''
            record.display_name = f"{action_name} - {record.user_id.name} - {timestamp_str}"
    

    @api.model_create_multi
    def create(self, vals_list):
        """Create a new history record with additional information"""
        for vals in vals_list:

            request = self.env.context.get('request')
            if request:
                vals.update({
                    'ip_address': request.httprequest.environ.get('REMOTE_ADDR'),
                    'user_agent': request.httprequest.environ.get('HTTP_USER_AGENT'),
                })
        
        return super().create(vals_list)
    
    def unlink(self):
        """Prevent deletion of history records to maintain audit trail"""
        raise UserError(_('Cannot delete history records to maintain audit trail'))
    

    @api.model
    def create_history_record(self, document_id, action, description, **kwargs):
        """Helper method to create a history record"""
        vals = {
            'document_id': document_id,
            'action': action,
            'description': description,
            'timestamp': fields.Datetime.now(),
            'user_id': self.env.user.id,
        }
        vals.update(kwargs)
        
        return self.create(vals)
    
    @api.model
    def get_document_timeline(self, document_id):
        """Get the document timeline"""
        return self.search([
            ('document_id', '=', document_id)
        ], order='timestamp asc')
    
    @api.model
    def get_user_activity(self, user_id, date_from=None, date_to=None):
        """Get user activity"""
        domain = [('user_id', '=', user_id)]
        
        if date_from:
            domain.append(('timestamp', '>=', date_from))
        if date_to:
            domain.append(('timestamp', '<=', date_to))
        
        return self.search(domain, order='timestamp desc')
    
    @api.model
    def get_document_statistics(self, document_id):
        """Get document statistics"""
        history_records = self.search([('document_id', '=', document_id)])
        
        stats = {
            'total_changes': len(history_records),
            'unique_users': len(history_records.mapped('user_id')),
            'creation_date': False,
            'last_update': False,
            'state_changes': 0,
            'attachments_added': 0,
        }
        
        if history_records:
            creation_record = history_records.filtered(lambda r: r.action == 'created')
            if creation_record:
                stats['creation_date'] = creation_record[0].timestamp
            
            stats['last_update'] = history_records[0].timestamp
            stats['state_changes'] = len(history_records.filtered(
                lambda r: r.previous_state != r.new_state and r.new_state
            ))
            stats['attachments_added'] = len(history_records.filtered(
                lambda r: r.action == 'attachment_added'
            ))
        
        return stats
    

    def action_view_document(self):
        """View the related document"""
        self.ensure_one()
        return {
            'name': _('Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_user(self):
        """View the related user"""
        self.ensure_one()
        return {
            'name': _('User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'target': 'new',
        } 
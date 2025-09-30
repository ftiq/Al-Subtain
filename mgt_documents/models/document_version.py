# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import hashlib
import base64
import logging

_logger = logging.getLogger(__name__)


class DocumentVersion(models.Model):
    """Document Version Management"""
    
    _name = 'document.version'
    _description = 'Document Versions'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'document_id, version_number desc, create_date desc'
    _rec_name = 'display_name'
    
    document_id = fields.Many2one(
        'document.document',
        string='Document',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    version_number = fields.Float(
        string='Version Number',
        required=True,
        tracking=True,
        help='Version number (e.g. 1.0, 1.1, 2.0)'
    )
    
    version_name = fields.Char(
        string='Version Name',
        help='Version name (optional)'
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('obsolete', 'Obsolete')
    ], string='State', default='draft', tracking=True)

    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Approval Status', default='draft', tracking=True)
    is_current = fields.Boolean(
        string='Current Version',
        default=False,
        tracking=True,
        help='Is this the current approved version?'
    )
    
    content = fields.Html(
        string='Content',
        help='Content of this version from the document'
    )
    content_file = fields.Binary(
        string='Content File',
        attachment=True,
        help='The file attached to this version (optional)'
    )
    content_filename = fields.Char(
        string='Content Filename',
        help='Filename for the binary content'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'document_version_attachment_rel',
        'version_id',
        'attachment_id',
        string='Attachments'
    )
    
    change_summary = fields.Text(   
        string='Change Summary',
        required=True,
        tracking=True,
        help='Description of the changes in this version'
    )

    description = fields.Text(
        string='Description',
        compute='_compute_description',
        inverse='_inverse_description',
        store=False
    )
    
    change_reason = fields.Selection([
        ('correction', 'Correction'),
        ('update', 'Update'),
        ('enhancement', 'Enhancement'),
        ('revision', 'Revision'),
        ('compliance', 'Compliance'),
        ('restructure', 'Restructure'),
        ('other', 'Other')
    ], string='Change Reason', default='update')
    
    change_details = fields.Html(
        string='Change Details',
        help='Additional details about the changes entered'
    )

    approval_notes = fields.Text(
        string='Approval Notes'
    )
    rejection_reason = fields.Text(
        string='Rejection Reason'
    )

    created_by = fields.Many2one(
        'hr.employee',
        string='Created By',
        default=lambda self: self.env.user.employee_id,
        required=True
    )
    
    created_date = fields.Datetime(
        string='Creation Date',
        default=fields.Datetime.now,
        required=True
    )
    
    approved_by = fields.Many2one(
        'hr.employee',
        string='Approved By',
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Approval Date',
        tracking=True
    )
    
    previous_version_id = fields.Many2one(
        'document.version',
        string='Previous Version',
        help='The version that preceded this version'
    )
    
    next_version_id = fields.Many2one(
        'document.version',
        string='Next Version',
        compute='_compute_next_version'
    )
    
    content_hash = fields.Char(
        string='Digital Signature',
        compute='_compute_content_hash',
        store=True,
        help='Digital signature to ensure content integrity'
    )
    
    view_count = fields.Integer(
        string='View Count',
        default=0,
        help='Number of times this version has been viewed'
    )
    
    download_count = fields.Integer(
        string='Download Count',
        default=0,
        help='Number of times this version has been downloaded'
    )

    file_size = fields.Integer(
        string='File Size',
        compute='_compute_file_size',
        store=True
    )
    
    @api.depends('attachment_ids')
    def _compute_file_size(self):
        for version in self:
            total = 0
            for att in version.attachment_ids:
                if hasattr(att, 'file_size') and att.file_size:
                    total += att.file_size
            version.file_size = total

    notes = fields.Text(
        string='Notes',
        help='Additional notes about this version'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.depends('document_id.name', 'version_number', 'version_name')
    def _compute_display_name(self):
        """Compute the display name for the version"""
        for version in self:
            base_name = version.document_id.name or _('Document')
            version_part = f"v{version.version_number}"
            
            if version.version_name:
                version_part += f" ({version.version_name})"
            
            version.display_name = f"{base_name} - {version_part}"

    def _compute_description(self):
        """Match the description field with the change summary to maintain display consistency"""
        for version in self:
            version.description = version.change_summary or False

    def _inverse_description(self):
        """Reverse the description value to the change summary"""
        for version in self:
            if version.description is not None:
                version.change_summary = version.description

    
    @api.depends('content', 'attachment_ids')
    def _compute_content_hash(self):
        """Compute the digital signature for the content"""
        for version in self:
            content_to_hash = ""
            
            if version.content:
                content_to_hash += version.content
            
            if version.attachment_ids:
                attachment_data = ",".join([
                    str(att.id) + att.name + str(att.file_size)
                    for att in version.attachment_ids
                ])
                content_to_hash += attachment_data
            
            if content_to_hash:
                hash_object = hashlib.md5(content_to_hash.encode('utf-8'))
                version.content_hash = hash_object.hexdigest()
            else:
                version.content_hash = False
    
    @api.depends('document_id')
    def _compute_next_version(self):
        """Compute the next version"""
        for version in self:
            next_version = self.search([
                ('document_id', '=', version.document_id.id),
                ('version_number', '>', version.version_number)
            ], order='version_number asc', limit=1)
            
            version.next_version_id = next_version.id if next_version else False
    
    def action_activate(self):
        """Activate the version and make it current"""
        for version in self:
            if version.state != 'draft':
                raise UserError(_('Only drafts can be activated'))
            
            other_versions = self.search([
                ('document_id', '=', version.document_id.id),
                ('id', '!=', version.id),
                ('is_current', '=', True)
            ])
            other_versions.write({'is_current': False})
            
            version.write({
                'state': 'active',
                'is_current': True,
                'approved_by': self.env.user.employee_id.id,
                'approved_date': fields.Datetime.now()
            })
            
            version.document_id.write({
                'content': version.content,
                'current_version_id': version.id
            })
            
            version._log_version_activity('activated')
    
    def action_submit_for_approval(self):
        """Submit the version for approval"""
        for version in self:
            if version.approval_status != 'draft':
                raise UserError(_('Only drafts can be submitted for approval'))
            version.write({'approval_status': 'pending'})
            version._log_version_activity('submitted')

    def action_approve(self):
        """Approve the version"""
        for version in self:
            if version.approval_status != 'pending':
                raise UserError(_('Only versions in pending approval can be approved'))
            version.write({
                'approval_status': 'approved',
                'approved_by': self.env.user.employee_id.id,
                'approved_date': fields.Datetime.now()
            })
            version._log_version_activity('approved')

    def action_reject(self):
        """Reject the version"""
        for version in self:
            if version.approval_status != 'pending':
                raise UserError(_('Only versions in pending approval can be rejected'))
            version.write({'approval_status': 'rejected'})
            version._log_version_activity('rejected')

    def action_archive_version(self):
        """Alias for button to maintain XML compatibility"""
        return self.action_archive()

    def action_archive(self):
        """Archive the version"""
        for version in self:
            if version.is_current:
                raise UserError(_('Cannot archive the current version'))
            
            version.write({'state': 'archived'})
            version._log_version_activity('archived')
    
    def action_obsolete(self):
        """Make the version obsolete"""
        for version in self:
            if version.is_current:
                raise UserError(_('Cannot obsolete the current version'))
            
            version.write({'state': 'obsolete'})
            version._log_version_activity('obsoleted')
    
    def action_view_document(self):
        """View the document content"""
        self.ensure_one()
        
        self.sudo().write({'view_count': self.view_count + 1})
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.version',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'readonly'}
        }
    
    def action_download(self):
        """Download the document content"""
        self.ensure_one()
        
        self.sudo().write({'download_count': self.download_count + 1})
        
        content = self._prepare_download_content()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=document.version&id={self.id}&field=content&download=true',
            'target': 'new'
        }
    
    def action_view_comparison(self):
        """Alias used by form stat button"""
        return self.action_compare_with_previous()

    def action_compare_with_previous(self):
        """Compare with the previous version"""
        self.ensure_one()
        
        if not self.previous_version_id:
            raise UserError(_('No previous version to compare with'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Versions'),
            'res_model': 'document.version.compare',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_version1_id': self.previous_version_id.id,
                'default_version2_id': self.id
            }
        }
    
    def action_create_new_version(self):
        """Create a new version based on this version"""
        self.ensure_one()
        
        max_version = self.search([
            ('document_id', '=', self.document_id.id)
        ], order='version_number desc', limit=1)
        
        new_version_number = (max_version.version_number or 0) + 0.1
        
        new_version = self.create({
            'document_id': self.document_id.id,
            'version_number': new_version_number,
            'content': self.content,
            'previous_version_id': self.id,
            'change_summary': _('New version based on version %s') % self.version_number,
            'change_reason': 'update'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.version',
            'res_id': new_version.id,
            'view_mode': 'form',
            'target': 'current'
        }
    
    comparison_summary = fields.Html(
        string='Comparison Summary',
        compute='_compute_comparison_summary'
    )

    def _compute_comparison_summary(self):
        """Generate a simple comparison summary with the previous version if available"""
        for version in self:
            if not version.previous_version_id:
                version.comparison_summary = _('No previous version to compare with.')
                continue
            summary_parts = []
            summary_parts.append(_('<b>Current Version:</b> %s') % version.version_number)
            summary_parts.append(_('<b>Previous Version:</b> %s') % version.previous_version_id.version_number)
            if version.change_summary:
                summary_parts.append(_('<b>Change Summary:</b> %s') % version.change_summary)
            version.comparison_summary = '<br/>'.join(summary_parts)
    def _prepare_download_content(self):
        """Preparing content for download"""
        self.ensure_one()
        
        content_parts = []
        content_parts.append(f"Document: {self.document_id.name}")
        content_parts.append(f"Version: {self.version_number}")
        content_parts.append(f"Created Date: {self.created_date}")
        content_parts.append(f"Created By: {self.created_by.name}")
        
        if self.change_summary:
            content_parts.append(f"Change Summary: {self.change_summary}")
        
        content_parts.append("=" * 50)
        
        if self.content:
            content_parts.append(self.content)
        
        return "\n\n".join(content_parts)
    
    def _log_version_activity(self, action):
        """Logging version activity"""
        self.ensure_one()
        
        activity_messages = {
            'activated': _('Version %s activated') % self.version_number,
            'archived': _('Version %s archived') % self.version_number,
            'obsoleted': _('Version %s obsoleted') % self.version_number,
            'created': _('Version %s created') % self.version_number,
        }
        
        message = activity_messages.get(action, _('Version %s modified') % self.version_number)
        
        self.document_id.message_post(
            body=message,
            subtype_xmlid='mail.mt_note'
        )
    
    @api.constrains('document_id', 'version_number')
    def _check_version_uniqueness(self):
        """Checking for unique version number for each document"""
        for version in self:
            existing = self.search([
                ('document_id', '=', version.document_id.id),
                ('version_number', '=', version.version_number),
                ('id', '!=', version.id)
            ])
            
            if existing:
                raise ValidationError(_(
                    'Version number %s already exists for this document'
                ) % version.version_number)
    
    @api.constrains('document_id', 'is_current')
    def _check_single_current_version(self):
        """Checking for single current version for each document"""
        for version in self:
            if version.is_current:
                other_current = self.search([
                    ('document_id', '=', version.document_id.id),
                    ('is_current', '=', True),
                    ('id', '!=', version.id)
                ])
                
                if other_current:
                    raise ValidationError(_(
                        'Only one current version is allowed for each document'
                    ))
    
    @api.constrains('version_number')
    def _check_version_number(self):
        """Checking for valid version number"""
        for version in self:
            if version.version_number <= 0:
                raise ValidationError(_('Version number must be positive'))


class DocumentVersionCompare(models.TransientModel):
    """Compare document versions"""
    
    _name = 'document.version.compare'
    _description = 'Compare document versions'
    
    version1_id = fields.Many2one(
        'document.version',
        string='Version 1',
        required=True
    )
    
    version2_id = fields.Many2one(
        'document.version',
        string='Version 2',
        required=True
    )
    
    comparison_result = fields.Html(
        string='Comparison Result',
        compute='_compute_comparison_result'
    )
    
    @api.depends('version1_id', 'version2_id')
    def _compute_comparison_result(self):
        """Compute comparison result"""
        for compare in self:
            if not compare.version1_id or not compare.version2_id:
                compare.comparison_result = _('Please select both versions for comparison')
                continue
            
            result_parts = []
            
            result_parts.append('<h3>Version Information</h3>')
            result_parts.append('<table class="table table-bordered">')
            result_parts.append('<tr><th>Information</th><th>Version 1</th><th>Version 2</th></tr>')
            
            result_parts.append(f'<tr><td>Version Number</td><td>{compare.version1_id.version_number}</td><td>{compare.version2_id.version_number}</td></tr>')
            
            result_parts.append(f'<tr><td>Created Date</td><td>{compare.version1_id.created_date}</td><td>{compare.version2_id.created_date}</td></tr>')
            
            result_parts.append(f'<tr><td>Created By</td><td>{compare.version1_id.created_by.name}</td><td>{compare.version2_id.created_by.name}</td></tr>')
            
            result_parts.append('</table>')
            
            if compare.version2_id.change_summary:
                result_parts.append('<h3>Change Summary</h3>')
                result_parts.append(f'<p>{compare.version2_id.change_summary}</p>')
            
            compare.comparison_result = ''.join(result_parts)


class DocumentVersionHistory(models.Model):
    """Document version history"""
    
    _name = 'document.version.history'
    _description = 'Document version history'
    _order = 'timestamp desc'
    
    version_id = fields.Many2one(
        'document.version',
        string='Version',
        required=True,
        ondelete='cascade'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user
    )
    
    action = fields.Selection([
        ('created', 'Created'),
        ('activated', 'Activated'),
        ('archived', 'Archived'),
        ('obsoleted', 'Obsoleted'),
        ('viewed', 'Viewed'),
        ('downloaded', 'Downloaded'),
        ('compared', 'Compared')
    ], string='Action', required=True)
    
    description = fields.Text(string='Description')
    
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True
    )
    
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')

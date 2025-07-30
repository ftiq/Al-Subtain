# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64
import hashlib
from datetime import datetime

class DigitalSignature(models.Model):
    _name = 'digital.signature'
    _description = 'Digital Signature'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='اسم التوقيع',
        required=True,
        default=lambda self: _('New Signature')
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        ondelete='cascade',
        help='الوثيقة المرتبطة بهذا التوقيع',
        index=True
    )
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='طلب الموافقة',
        ondelete='cascade',
        help='طلب الموافقة المرتبط بهذا التوقيع',
        index=True
    )
    
    signer_id = fields.Many2one(
        'res.users',
        string='الموقع',
        required=True,
        default=lambda self: self.env.user
    )
    
    signature_date = fields.Datetime(
        string='تاريخ التوقيع',
        required=True,
        default=fields.Datetime.now
    )
    
    signature_data = fields.Binary(
        string='التوقيع الإلكتروني',
        help='التوقيع الإلكتروني المرسوم مباشرة',
        attachment=True
    )
    
    signature_hash = fields.Char(
        string='تجمع التوقيع',
        help='التجمع المشفر لبيانات التوقيع للتحقق من الصحة'
    )
    
    is_valid = fields.Boolean(
        string='التوقيع صالح',
        default=True,
        help='هل التوقيع الرقمي صالح'
    )
    
    signature_method = fields.Selection([
        ('digital', 'توقيع رقمي'),
        ('electronic', 'توقيع إلكتروني'),
        ('manual', 'توقيع يدوي'),
    ], string='طريقة التوقيع', default='digital', required=True)
    
    verification_code = fields.Char(
        string='رمز التحقق',
        help='رمز التحقق من صحة التوقيع'
    )
    
    certificate_info = fields.Text(
        string='معلومات الشهادة',
        help='معلومات شهادة التوقيع الرقمي'
    )
    
    notes = fields.Text(
        string='ملاحظات'
    )
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('signed', 'موقع'),
        ('verified', 'محقق'),
        ('invalid', 'غير صالح'),
    ], string='الحالة', default='draft', required=True, tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New Signature')) == _('New Signature'):
            vals['name'] = self.env['ir.sequence'].next_by_code('digital.signature') or _('New Signature')
        

        if vals.get('signature_data'):
            vals['signature_hash'] = self._generate_signature_hash(vals['signature_data'])
            vals.update({
                'state': 'signed',
                'signature_date': fields.Datetime.now(),
                'is_valid': True
            })
            
        signature = super(DigitalSignature, self).create(vals)
        
        if signature.signature_data:
            if signature.document_id:
                signature.document_id.message_post(
                    body=_('✅ تم توقيع الوثيقة رقمياً بواسطة %s') % signature.signer_id.name,
                    subject=_('التوقيع الرقمي'),
                    message_type='notification'
                )
            
            if signature.approval_request_id:
                signature.approval_request_id.message_post(
                    body=_('✅ تم التوقيع رقمياً من قبل %s') % signature.signer_id.name,
                    subject=_('التوقيع الرقمي'),
                    message_type='notification'
                )

        return signature

    def write(self, vals):
        if 'signature_data' in vals and vals['signature_data']:
            vals['signature_hash'] = self._generate_signature_hash(vals['signature_data'])
            if self.state == 'draft':
                vals.update({
                    'state': 'signed',
                    'signature_date': fields.Datetime.now(),
                    'is_valid': True
                })
                if self.document_id:
                    self.document_id.message_post(
                        body=_('✅ تم تحديث التوقيع الرقمي بواسطة %s') % self.signer_id.name,
                        subject=_('تحديث التوقيع الرقمي'),
                        message_type='notification'
                    )
                
                if self.approval_request_id:
                    self.approval_request_id.message_post(
                        body=_('✅ تم تحديث التوقيع من قبل %s') % self.signer_id.name,
                        subject=_('تحديث التوقيع'),
                        message_type='notification'
                    )
                
        return super(DigitalSignature, self).write(vals)

    def _generate_signature_hash(self, signature_data):
        """Generate a hash for the signature data"""
        if signature_data:

            signature_bytes = base64.b64decode(signature_data)
            return hashlib.sha256(signature_bytes).hexdigest()
        return False

    def action_sign(self):
        """Sign the document"""
        self.ensure_one()
        if self.state != 'draft':
            raise ValidationError(_('يمكن توقيع التوقيعات في حالة المسودة فقط'))
            
        self.write({
            'state': 'signed',
            'signature_date': fields.Datetime.now(),
            'is_valid': True
        })
        
        if self.document_id:
            self.document_id.message_post(
                body=_('تم إضافة توقيع رقمي جديد بواسطة %s') % self.signer_id.name
            )

    def action_verify(self):
        """Verify the signature"""
        self.ensure_one()
        if self.state != 'signed':
            raise ValidationError(_('يمكن التحقق من التوقيعات الموقعة فقط'))
            
        is_valid = bool(self.signature_hash and self.signature_data)
        
        self.write({
            'state': 'verified' if is_valid else 'invalid',
            'is_valid': is_valid
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نتيجة التحقق'),
                'message': _('التوقيع صالح') if is_valid else _('التوقيع غير صالح'),
                'type': 'success' if is_valid else 'warning',
                'sticky': False,
            }
        }

    def action_invalidate(self):
        """Invalidate the signature"""
        self.ensure_one()
        self.write({
            'state': 'invalid',
            'is_valid': False
        })
        
        if self.document_id:
            self.document_id.message_post(
                body=_('تم إبطال التوقيع الرقمي بواسطة %s') % self.env.user.name
            )

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} - {record.signer_id.name}"
            if record.signature_date:
                name += f" ({record.signature_date.strftime('%Y-%m-%d')})"
            result.append((record.id, name))
        return result

    @api.constrains('document_id', 'approval_request_id')
    def _check_document_or_approval_required(self):

        for record in self:
            if not record.document_id and not record.approval_request_id:
                raise ValidationError(_(

                ))

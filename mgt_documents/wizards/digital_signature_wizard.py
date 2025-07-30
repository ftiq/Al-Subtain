# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64

class DigitalSignatureWizard(models.TransientModel):
    _name = 'digital.signature.wizard'
    _description = 'Digital Signature Wizard'

    signature_id = fields.Many2one(
        'digital.signature',
        string='التوقيع',
        required=True,
        ondelete='cascade'
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        related='signature_id.document_id',
        readonly=True
    )
    
    signature_data = fields.Binary(
        string='التوقيع الإلكتروني',
        required=True,
        help='ارسم توقيعك الإلكتروني هنا'
    )
    
    signature_method = fields.Selection([
        ('digital', 'توقيع رقمي'),
        ('electronic', 'توقيع إلكتروني'),
        ('manual', 'توقيع يدوي'),
    ], string='طريقة التوقيع', default='electronic', required=True)
    
    notes = fields.Text(
        string='ملاحظات التوقيع',
        help='أي ملاحظات إضافية حول التوقيع'
    )
    
    approval_required = fields.Boolean(
        string='موافقة مطلوبة',
        default=False,
        help='هل هذا التوقيع مطلوب لإكمال الموافقة؟'
    )

    @api.model
    def default_get(self, fields_list):
        """تحديد القيم الافتراضية"""
        res = super().default_get(fields_list)
        

        if self.env.context.get('default_signature_id'):
            res['signature_id'] = self.env.context['default_signature_id']
            
        if self.env.context.get('default_document_id'):
            res['document_id'] = self.env.context['default_document_id']
            
        if self.env.context.get('approval_required'):
            res['approval_required'] = True
            
        return res

    def action_sign(self):
        """تنفيذ التوقيع"""
        self.ensure_one()
        
        if not self.signature_data:
            raise ValidationError(_('يجب رسم التوقيع الإلكتروني أولاً'))
            
        self.signature_id.write({
            'signature_data': self.signature_data,
            'signature_method': self.signature_method,
            'notes': self.notes,
            'state': 'signed',
            'signature_date': fields.Datetime.now(),
            'is_valid': True
        })
        
        if self.approval_required and self.document_id:
            self.document_id.complete_approval_with_signature(self.signature_id.id)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تم التوقيع بنجاح'),
                    'message': _('تم إكمال التوقيع الإلكتروني واعتماد الوثيقة بنجاح'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم التوقيع بنجاح'),
                'message': _('تم حفظ التوقيع الإلكتروني بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        """إلغاء التوقيع"""
        self.ensure_one()
        
        if self.signature_id.state == 'draft':
            self.signature_id.unlink()
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الإلغاء'),
                'message': _('تم إلغاء عملية التوقيع. لم يتم اعتماد الوثيقة.'),
                'type': 'info',
                'sticky': False,
            }
        }
        
    @api.constrains('signature_data')
    def _check_signature_data(self):
        """التحقق من صحة بيانات التوقيع"""
        for record in self:
            if record.signature_data:
                try:
                    base64.b64decode(record.signature_data)
                except Exception:
                    raise ValidationError(_('بيانات التوقيع غير صالحة'))

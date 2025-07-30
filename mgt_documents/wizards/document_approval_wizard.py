# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class DocumentApprovalWizard(models.TransientModel):
    _name = 'document.approval.wizard'
    _description = 'معالج اعتماد الوثيقة'

    document_id = fields.Many2one('document.document', string='الوثيقة', required=True)
    requires_signature = fields.Boolean(string='يتطلب توقيع', default=False)
    signature_data = fields.Binary(string='التوقيع')
    approval_notes = fields.Text(string='ملاحظات الاعتماد')
    is_direct_approval = fields.Boolean(string='اعتماد مباشر', default=False)
    

    copy_to_user_ids = fields.Many2many(
        'res.users',
        'approval_copy_user_rel',
        'approval_id',
        'user_id',
        string='نسخة منه إلى',
        help='المستخدمون الذين سيتم إرسال نسخة من اعتماد الوثيقة إليهم'
    )
    
    copy_message_id = fields.Many2one(
        'document.copy.message',
        string='رسالة النسخة',
        help='اختر رسالة معدة مسبقاً لإرسالها مع إشعار اعتماد الوثيقة'
    )
    
    custom_copy_message = fields.Text(
        string='رسالة مخصصة',
        help='اكتب رسالة مخصصة إذا لم تجد رسالة مناسبة من القائمة'
    )
    
    final_copy_message = fields.Text(
        string='الرسالة النهائية',
        compute='_compute_final_copy_message',
        help='الرسالة التي سيتم إرسالها فعلياً'
    )
    
    @api.depends('copy_message_id', 'custom_copy_message')
    def _compute_final_copy_message(self):
        """حساب الرسالة النهائية للإرسال"""
        for record in self:
            if record.custom_copy_message:
                record.final_copy_message = record.custom_copy_message
            elif record.copy_message_id:
                record.final_copy_message = record.copy_message_id.message
            else:
                record.final_copy_message = ''
    
    def _send_copy_notifications(self):
        """إرسال إشعارات النسخ بعد الاعتماد"""
        if not self.copy_to_user_ids:
            return
            
        for user in self.copy_to_user_ids:
            message_body = f"""إشعار اعتماد وثيقة: {self.document_id.name}

عنوان الوثيقة: {self.document_id.name}
الرقم المرجعي: {self.document_id.reference_number or 'غير محدد'}
النوع: {dict(self.document_id._fields['document_type'].selection).get(self.document_id.document_type, self.document_id.document_type)}
تاريخ الاعتماد: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}
المعتمد: {self.env.user.name}

رسالة النسخة:
{self.final_copy_message}

ملاحظة: هذه نسخة إعلامية باعتماد الوثيقة"""
            
            try:
                mail_template = self.env.ref('mgt_documents.email_template_approval_notification', raise_if_not_found=False)
                if mail_template:
                    mail_template.with_context(
                        recipient_user=user,
                        approval_message=self.final_copy_message,
                        approver_name=self.env.user.name
                    ).send_mail(self.document_id.id, force_send=False)
            except Exception as e:
                self.document_id.message_post(
                    body=message_body,
                    subject=f'نسخة من الوثيقة: {self.document_id.name}',
                    partner_ids=[user.partner_id.id],
                    message_type='comment'
                )
            
            # إضافة المستخدم كمتابع
            if user.partner_id not in self.document_id.message_follower_ids.mapped('partner_id'):
                self.document_id.message_subscribe([user.partner_id.id])
    
    def action_approve(self):
        """اعتماد الوثيقة"""
        self.ensure_one()
        
        if self.signature_data:
            signature = self.env['digital.signature'].create({
                'document_id': self.document_id.id,
                'signature_data': self.signature_data,
                'signer_id': self.env.user.id,
                'signature_date': fields.Datetime.now(),
                'notes': 'توقيع اعتماد الوثيقة',
                'signature_method': 'digital',
            })
        
        self.document_id.write({
            'state': 'approved',
            'approval_status': 'approved',
            'approved_date': fields.Datetime.now(),
        })
        
        self._send_copy_notifications()
        
        message = f"تم اعتماد الوثيقة مباشرة من قبل: {self.env.user.name}"
        if self.approval_notes:
            message += f"\nملاحظات الاعتماد: {self.approval_notes}"
        if self.signature_data:
            message += "\nتم إرفاق التوقيع الرقمي"
        if self.copy_to_user_ids:
            copy_users = ', '.join(self.copy_to_user_ids.mapped('name'))
            message += f"\nتم إرسال نسخة إلى: {copy_users}"
            
        self.document_id.message_post(body=message)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_approve_without_signature(self):
        """اعتماد بدون توقيع"""
        self.write({'requires_signature': False})
        return self.action_approve()

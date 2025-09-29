# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class DocumentCopyWizard(models.TransientModel):
    """معالج إرسال النسخ والإشعارات للوثائق"""
    
    _name = 'document.copy.wizard'
    _description = 'معالج إرسال النسخ'

    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        required=True,
        ondelete='cascade'
    )
    
    document_name = fields.Char(
        related='document_id.name',
        string='عنوان الوثيقة',
        readonly=True
    )
    
    document_reference = fields.Char(
        related='document_id.reference_number',
        string='الرقم المرجعي',
        readonly=True
    )
    
    copy_to_user_ids = fields.Many2many(
        'res.users',
        'wizard_copy_to_rel',
        'wizard_id',
        'user_id',
        string='نسخة منه إلى',
        required=True,
        help='المستخدمون الذين سيتم إرسال نسخة من الوثيقة إليهم للقراءة فقط'
    )
    
    copy_message_id = fields.Many2one(
        'document.copy.message',
        string='رسالة النسخة',
        help='اختر رسالة معدة مسبقاً لإرسالها مع إشعار النسخة للمستخدمين المحددين'
    )
    
    custom_message = fields.Text(
        string='رسالة مخصصة',
        help='اكتب رسالة مخصصة إذا لم تجد رسالة مناسبة من القائمة'
    )
    
    urgent = fields.Boolean(
        string='عاجل',
        default=False,
        help='ضع علامة إذا كانت النسخة عاجلة'
    )
    
    require_acknowledgment = fields.Boolean(
        string='يتطلب إقرار بالاستلام',
        default=False,
        help='يتطلب من المستلمين تأكيد استلام النسخة'
    )
    
    final_message = fields.Text(
        string='الرسالة النهائية',
        compute='_compute_final_message',
        help='الرسالة التي سيتم إرسالها فعلياً'
    )
    
    # إحصائيات
    user_count = fields.Integer(
        string='عدد المستخدمين',
        compute='_compute_user_count'
    )
    
    @api.depends('copy_to_user_ids')
    def _compute_user_count(self):
        """حساب عدد المستخدمين المحددين"""
        for record in self:
            record.user_count = len(record.copy_to_user_ids)
    
    @api.depends('copy_message_id', 'custom_message')
    def _compute_final_message(self):
        """حساب الرسالة النهائية للإرسال"""
        for record in self:
            if record.custom_message:
                record.final_message = record.custom_message
            elif record.copy_message_id:
                record.final_message = record.copy_message_id.message
            else:
                record.final_message = 'يرجى الاطلاع على الوثيقة المرفقة للعلم والمتابعة اللازمة.'
    
    @api.model
    def default_get(self, fields_list):
        """تعيين القيم الافتراضية"""
        res = super().default_get(fields_list)
        

        if self.env.context.get('active_model') == 'document.document' and self.env.context.get('active_id'):
            document_id = self.env.context.get('active_id')
            document = self.env['document.document'].browse(document_id)
            
            res.update({
                'document_id': document_id,
                'copy_to_user_ids': document.copy_to_user_ids.ids,
                'copy_message_id': document.copy_message_id.id if document.copy_message_id else False,
            })
        
        return res
    
    @api.constrains('copy_to_user_ids')
    def _check_users_not_empty(self):
        """التحقق من وجود مستخدمين محددين"""
        for record in self:
            if not record.copy_to_user_ids:
                raise ValidationError(_('يجب تحديد مستخدم واحد على الأقل لإرسال النسخة إليه.'))
    
    def action_send_copy(self):
        """إرسال النسخة للمستخدمين المحددين"""
        self.ensure_one()
        
        if not self.copy_to_user_ids:
            raise ValidationError(_('يجب تحديد مستخدمين لإرسال النسخة إليهم.'))
        
        document = self.document_id
        
        # رسالة نصية بسيطة فقط
        message_body = f"""نسخة من الوثيقة: {document.name}

عنوان الوثيقة: {document.name}
الرقم المرجعي: {document.reference_number or 'غير محدد'}
النوع: {dict(document._fields['document_type'].selection).get(document.document_type, document.document_type)}
التاريخ: {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}

رسالة النسخة:
{self.final_message}

ملاحظة: هذه نسخة للقراءة فقط"""
        
        successful_sends = 0
        for user in self.copy_to_user_ids:
            try:

                mail_template = self.env.ref('mgt_documents.email_template_copy_notification', raise_if_not_found=False)
                if mail_template:
                    mail_template.with_context(
                        recipient_user=user,
                        copy_message=self.final_message
                    ).send_mail(document.id, force_send=False)
                
                if user.partner_id not in document.message_follower_ids.mapped('partner_id'):
                    document.message_subscribe([user.partner_id.id])
                
                copy_reader_group = self.env.ref('mgt_documents.group_document_copy_reader', raise_if_not_found=False)
                if copy_reader_group and copy_reader_group not in user.groups_id:
                    user.sudo().write({'groups_id': [(4, copy_reader_group.id)]})
                
                successful_sends += 1
                
            except Exception as e:
                _logger = self.env['ir.logging']
                _logger.create({
                    'name': 'Document Copy Error',
                    'type': 'server',
                    'level': 'ERROR',
                    'message': f'خطأ في إرسال نسخة الوثيقة {document.name} للمستخدم {user.name}: {str(e)}',
                    'path': 'document.copy.wizard',
                    'func': 'action_send_copy'
                })
        
        document.write({
            'copy_to_user_ids': [(6, 0, self.copy_to_user_ids.ids)],
            'copy_message_id': self.copy_message_id.id if self.copy_message_id else False,
            'notification_sent': True,
            'notification_sent_date': fields.Datetime.now()
        })
        
        if successful_sends == len(self.copy_to_user_ids):
            message = f'✅ تم إرسال النسخة بنجاح لجميع المستخدمين ({successful_sends} مستخدم)'
            notification_type = 'success'
        else:
            message = f'⚠️ تم إرسال النسخة لـ {successful_sends} من أصل {len(self.copy_to_user_ids)} مستخدمين'
            notification_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': notification_type,
                'sticky': False
            }
        }
    
    def action_preview_message(self):
        """معاينة الرسالة قبل الإرسال"""
        self.ensure_one()
        
        preview_html = f"""
        <div style="margin: 20px; font-family: Arial, sans-serif;">
            <h3>معاينة رسالة النسخة</h3>
            <hr>
            <div style="border: 1px solid #ddd; padding: 15px; border-radius: 5px; background: #f9f9f9;">
                {self.final_message}
            </div>
            <br>
            <p><strong>سيتم إرسالها إلى:</strong></p>
            <ul>
                {''.join([f'<li>{user.name} ({user.login})</li>' for user in self.copy_to_user_ids])}
            </ul>
        </div>
        """
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'معاينة رسالة النسخة',
            'res_model': 'document.copy.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'preview_mode': True,
                'preview_html': preview_html
            }
        }

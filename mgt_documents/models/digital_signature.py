# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
import hashlib
from datetime import datetime


class DigitalSignature(models.Model):
    """نموذج التوقيع الرقمي للوثائق"""
    
    _name = 'digital.signature'
    _description = 'التوقيع الرقمي'
    _inherit = ['mail.thread']
    _order = 'signing_date desc, id desc'
    _rec_name = 'display_name'
    

    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='الموقع',
        required=True,
        default=lambda self: self.env.user,
        tracking=True
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف الموقع',
        related='user_id.employee_id',
        store=True
    )
    
    signing_date = fields.Datetime(
        string='تاريخ التوقيع',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    signature_image = fields.Binary(
        string='صورة التوقيع',
        help='صورة التوقيع المرسومة أو المرفوعة'
    )
    
    signature_text = fields.Char(
        string='نص التوقيع',
        help='النص المستخدم للتوقيع (الاسم مثلاً)'
    )
    
    signature_type = fields.Selection([
        ('drawn', 'مرسوم'),
        ('typed', 'مكتوب'),
        ('uploaded', 'مرفوع'),
        ('certificate', 'شهادة رقمية'),
        ('biometric', 'بيومتري')
    ], string='نوع التوقيع', default='drawn', tracking=True)
    
    signature_hash = fields.Char(
        string='تشفير التوقيع',
        readonly=True,
        help='تشفير MD5 للتوقيع للتحقق من سلامته'
    )
    
    document_hash = fields.Char(
        string='تشفير الوثيقة',
        readonly=True,
        help='تشفير MD5 للوثيقة وقت التوقيع'
    )
    
    is_valid = fields.Boolean(
        string='صالح',
        compute='_compute_is_valid',
        store=True,
        help='ما إذا كان التوقيع صالحاً ولم يتم التلاعب به'
    )
    
    validation_message = fields.Text(
        string='رسالة التحقق',
        compute='_compute_is_valid',
        help='تفاصيل حالة التحقق من التوقيع'
    )
    
    certificate_id = fields.Many2one(
        'certificate.certificate',
        string='الشهادة الرقمية',
        ondelete='set null',
        help='الشهادة الرقمية المستخدمة للتوقيع'
    )
    
    certificate_serial = fields.Char(
        string='رقم الشهادة',
        help='الرقم التسلسلي للشهادة الرقمية'
    )
    
    certificate_issuer = fields.Char(
        string='مصدر الشهادة',
        help='الجهة المصدرة للشهادة الرقمية'
    )
    
    ip_address = fields.Char(
        string='عنوان IP',
        help='عنوان IP للجهاز المستخدم للتوقيع'
    )
    
    device_info = fields.Text(
        string='معلومات الجهاز',
        help='معلومات الجهاز والمتصفح المستخدم'
    )
    
    location = fields.Char(
        string='الموقع الجغرافي',
        help='الموقع الجغرافي التقريبي للتوقيع'
    )
    
    signature_purpose = fields.Selection([
        ('approval', 'موافقة'),
        ('review', 'مراجعة'),
        ('witness', 'شاهد'),
        ('author', 'مؤلف'),
        ('acknowledgment', 'إقرار'),
        ('other', 'أخرى')
    ], string='غرض التوقيع', default='approval', tracking=True)
    
    signature_role = fields.Char(
        string='دور الموقع',
        help='الدور أو المنصب الذي يوقع به الشخص'
    )
    
    comments = fields.Text(
        string='تعليقات',
        help='تعليقات إضافية حول التوقيع'
    )
    
    display_name = fields.Char(
        string='الاسم المعروض',
        compute='_compute_display_name'
    )
    
    document_name = fields.Char(
        string='اسم الوثيقة',
        related='document_id.name',
        store=True
    )
    
    signer_name = fields.Char(
        string='اسم الموقع',
        related='user_id.name',
        store=True
    )
    
    @api.depends('user_id.name', 'signing_date', 'signature_purpose')
    def _compute_display_name(self):
        """حساب الاسم المعروض للتوقيع"""
        for record in self:
            purpose_name = dict(record._fields['signature_purpose'].selection).get(record.signature_purpose, record.signature_purpose)
            date_str = record.signing_date.strftime('%Y-%m-%d %H:%M') if record.signing_date else ''
            record.display_name = f"{record.user_id.name} - {purpose_name} - {date_str}"
    
    @api.depends('signature_hash', 'document_hash', 'document_id')
    def _compute_is_valid(self):
        """التحقق من صحة التوقيع"""
        for record in self:
            if not record.signature_hash:
                record.is_valid = False
                record.validation_message = _('لا يوجد تشفير للتوقيع')
                continue
            
            # Check if document has been modified since signing
            if record.document_id:
                current_doc_hash = record._calculate_document_hash()
                if record.document_hash and record.document_hash != current_doc_hash:
                    record.is_valid = False
                    record.validation_message = _('تم تعديل الوثيقة بعد التوقيع')
                    continue
            
            # Check signature integrity
            current_sig_hash = record._calculate_signature_hash()
            if record.signature_hash != current_sig_hash:
                record.is_valid = False
                record.validation_message = _('تم التلاعب بالتوقيع')
                continue
            
            # Check certificate validity (if applicable)
            if record.certificate_id and not record.certificate_id.is_valid:
                record.is_valid = False
                record.validation_message = _('الشهادة الرقمية غير صالحة')
                continue
            
            record.is_valid = True
            record.validation_message = _('التوقيع صالح ومُتحقق منه')
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء توقيع رقمي جديد"""
        for vals in vals_list:
            request = self.env.context.get('request')
            if request:
                vals.update({
                    'ip_address': request.httprequest.environ.get('REMOTE_ADDR'),
                    'device_info': request.httprequest.environ.get('HTTP_USER_AGENT'),
                })
            
            if vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                if user.employee_id and user.employee_id.job_title:
                    vals['signature_role'] = user.employee_id.job_title
        
        signatures = super().create(vals_list)

        for signature in signatures:
            signature._update_hashes()
            signature._create_history_record()
        
        return signatures
    
    def write(self, vals):
        """تحديث التوقيع الرقمي"""
        protected_fields = ['signature_image', 'signature_text', 'signature_hash', 'document_hash', 'signing_date']
        for field in protected_fields:
            if field in vals and any(getattr(record, field) for record in self):
                raise UserError(_('لا يمكن تعديل بيانات التوقيع بعد إنشائه'))
        
        return super().write(vals)
    
    def unlink(self):
        """حذف التوقيع الرقمي"""
        for record in self:
            if record.is_valid:
                raise UserError(_('لا يمكن حذف التوقيعات الصالحة'))
        
        return super().unlink()
    
    def _calculate_signature_hash(self):
        """حساب تشفير التوقيع"""
        self.ensure_one()
        
        hash_data = ''
        
        if self.signature_image:
            hash_data += base64.b64encode(self.signature_image).decode()
        
        if self.signature_text:
            hash_data += self.signature_text
        
        hash_data += str(self.user_id.id)
        hash_data += self.signing_date.isoformat() if self.signing_date else ''
        hash_data += str(self.document_id.id) if self.document_id else ''
        
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    def _calculate_document_hash(self):
        """حساب تشفير الوثيقة"""
        self.ensure_one()
        
        if not self.document_id:
            return ''
        
        doc = self.document_id
        hash_data = ''
        hash_data += doc.name or ''
        hash_data += doc.subject or ''
        hash_data += doc.content or ''
        hash_data += str(doc.date) if doc.date else ''
        
        for attachment in doc.attachment_ids:
            if attachment.datas:
                hash_data += base64.b64encode(attachment.datas).decode()
        
        return hashlib.md5(hash_data.encode()).hexdigest()
    
    def _update_hashes(self):
        """تحديث تشفير التوقيع والوثيقة"""
        self.ensure_one()
        
        self.write({
            'signature_hash': self._calculate_signature_hash(),
            'document_hash': self._calculate_document_hash(),
        })
    
    def _create_history_record(self):
        """إنشاء سجل في تاريخ الوثيقة"""
        if self.document_id:
            self.env['document.history'].create({
                'document_id': self.document_id.id,
                'user_id': self.user_id.id,
                'action': 'signed',
                'description': _('تم توقيع الوثيقة بواسطة %s') % self.user_id.name,
                'signature_id': self.id,
            })
    
    def action_verify_signature(self):
        """التحقق من صحة التوقيع"""
        self.ensure_one()
        
        self._compute_is_valid()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('نتيجة التحقق'),
                'message': self.validation_message,
                'type': 'success' if self.is_valid else 'warning',
            }
        }
    
    def action_invalidate_signature(self):
        """إبطال التوقيع الرقمي"""
        self.ensure_one()
        
        if not self.is_valid:
            raise UserError(_('التوقيع غير صالح بالفعل'))
        
        self.write({
            'signature_hash': False,
            'validation_message': _('تم إبطال التوقيع يدوياً بواسطة %s') % self.env.user.name
        })
        
        self.env['document.history'].create({
            'document_id': self.document_id.id,
            'user_id': self.env.user.id,
            'action': 'signature_invalidated',
            'description': _('تم إبطال التوقيع الرقمي بواسطة %s') % self.env.user.name,
            'signature_id': self.id,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم إبطال التوقيع'),
                'message': _('تم إبطال التوقيع الرقمي بنجاح'),
                'type': 'success',
            }
        }
    
    def action_view_document(self):
        """عرض الوثيقة المرتبطة"""
        self.ensure_one()
        return {
            'name': _('الوثيقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_download_certificate(self):
        """تحميل شهادة التوقيع"""
        self.ensure_one()
        
        if not self.is_valid:
            raise UserError(_('لا يمكن تحميل شهادة لتوقيع غير صالح'))
        
        certificate_data = self._generate_signature_certificate()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/digital.signature/{self.id}/signature_certificate.pdf',
            'target': 'new',
        }
    
    def _generate_signature_certificate(self):
        """توليد شهادة التوقيع"""
        pass
    
    @api.model
    def validate_signature_integrity(self, signature_id):
        """التحقق من سلامة التوقيع (API method)"""
        signature = self.browse(signature_id)
        if not signature.exists():
            return {'valid': False, 'message': _('التوقيع غير موجود')}
        
        signature._compute_is_valid()
        
        return {
            'valid': signature.is_valid,
            'message': signature.validation_message,
            'signer': signature.user_id.name,
            'date': signature.signing_date.isoformat() if signature.signing_date else '',
            'document': signature.document_id.name,
        }
    
    @api.model
    def get_signature_chain(self, document_id):
        """الحصول على سلسلة التوقيعات للوثيقة"""
        signatures = self.search([
            ('document_id', '=', document_id)
        ], order='signing_date asc')
        
        return [{
            'id': sig.id,
            'signer': sig.user_id.name,
            'date': sig.signing_date.isoformat() if sig.signing_date else '',
            'purpose': sig.signature_purpose,
            'valid': sig.is_valid,
            'role': sig.signature_role,
        } for sig in signatures]
    
    @api.constrains('signature_image', 'signature_text')
    def _check_signature_data(self):
        """التحقق من وجود بيانات التوقيع"""
        for record in self:
            if not record.signature_image and not record.signature_text:
                raise ValidationError(_('يجب توفير صورة التوقيع أو نص التوقيع'))
    
    @api.constrains('signing_date')
    def _check_signing_date(self):
        """التحقق من تاريخ التوقيع"""
        for record in self:
            if record.signing_date and record.signing_date > fields.Datetime.now():
                raise ValidationError(_('لا يمكن أن يكون تاريخ التوقيع في المستقبل'))
    
    _sql_constraints = [
        ('unique_user_document_purpose', 
         'UNIQUE(document_id, user_id, signature_purpose)', 
         'لا يمكن للمستخدم توقيع نفس الوثيقة بنفس الغرض أكثر من مرة'),
    ] 
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import hashlib
import base64
import logging

_logger = logging.getLogger(__name__)


class DocumentVersion(models.Model):
    """نظام إدارة إصدارات الوثائق"""
    
    _name = 'document.version'
    _description = 'إصدارات الوثائق'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'document_id, version_number desc, create_date desc'
    _rec_name = 'display_name'
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة الأساسية',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    version_number = fields.Float(
        string='رقم الإصدار',
        required=True,
        tracking=True,
        help='رقم الإصدار (مثل 1.0, 1.1, 2.0)'
    )
    
    version_name = fields.Char(
        string='اسم الإصدار',
        help='اسم مميز للإصدار (اختياري)'
    )
    
    display_name = fields.Char(
        string='الاسم المعروض',
        compute='_compute_display_name',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('archived', 'مؤرشف'),
        ('obsolete', 'مهجور')
    ], string='الحالة', default='draft', tracking=True)

    approval_status = fields.Selection([
        ('draft', 'مسودة'),
        ('pending', 'قيد الاعتماد'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة')
    ], string='حالة الاعتماد', default='draft', tracking=True)
    is_current = fields.Boolean(
        string='الإصدار الحالي',
        default=False,
        tracking=True,
        help='هل هذا هو الإصدار الحالي المعتمد؟'
    )
    
    content = fields.Html(
        string='محتوى الإصدار',
        help='محتوى هذا الإصدار من الوثيقة'
    )
    content_file = fields.Binary(
        string='ملف المحتوى',
        attachment=True,
        help='الملف المرفق لهذا الإصدار (اختياري)'
    )
    content_filename = fields.Char(
        string='اسم الملف',
        help='اسم الملف للمحتوى الثنائي'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'document_version_attachment_rel',
        'version_id',
        'attachment_id',
        string='مرفقات الإصدار'
    )
    
    change_summary = fields.Text(   
        string='ملخص التغييرات',
        required=True,
        tracking=True,
        help='وصف التغييرات في هذا الإصدار'
    )

    description = fields.Text(
        string='الوصف',
        compute='_compute_description',
        inverse='_inverse_description',
        store=False
    )
    
    change_reason = fields.Selection([
        ('correction', 'تصحيح'),
        ('update', 'تحديث'),
        ('enhancement', 'تحسين'),
        ('revision', 'مراجعة'),
        ('compliance', 'توافق مع المعايير'),
        ('restructure', 'إعادة هيكلة'),
        ('other', 'أخرى')
    ], string='سبب التغيير', default='update')
    
    change_details = fields.Html(
        string='تفاصيل التغيير',
        help='تفاصيل إضافية حول التغييرات المُدخلة'
    )

    approval_notes = fields.Text(
        string='ملاحظات الاعتماد'
    )
    rejection_reason = fields.Text(
        string='سبب الرفض'
    )

    created_by = fields.Many2one(
        'hr.employee',
        string='أنشأ بواسطة',
        default=lambda self: self.env.user.employee_id,
        required=True
    )
    
    created_date = fields.Datetime(
        string='تاريخ الإنشاء',
        default=fields.Datetime.now,
        required=True
    )
    
    approved_by = fields.Many2one(
        'hr.employee',
        string='اعتمد بواسطة',
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='تاريخ الاعتماد',
        tracking=True
    )
    
    previous_version_id = fields.Many2one(
        'document.version',
        string='الإصدار السابق',
        help='الإصدار الذي سبق هذا الإصدار'
    )
    
    next_version_id = fields.Many2one(
        'document.version',
        string='الإصدار التالي',
        compute='_compute_next_version'
    )
    
    content_hash = fields.Char(
        string='التوقيع الرقمي',
        compute='_compute_content_hash',
        store=True,
        help='توقيع رقمي لضمان سلامة المحتوى'
    )
    
    view_count = fields.Integer(
        string='عدد المشاهدات',
        default=0,
        help='عدد مرات مشاهدة هذا الإصدار'
    )
    
    download_count = fields.Integer(
        string='عدد التحميلات',
        default=0,
        help='عدد مرات تحميل هذا الإصدار'
    )

    file_size = fields.Integer(
        string='حجم الملفات (بايت)',
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
        string='ملاحظات',
        help='ملاحظات إضافية حول هذا الإصدار'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )
    
    @api.depends('document_id.name', 'version_number', 'version_name')
    def _compute_display_name(self):
        """حساب الاسم المعروض للإصدار"""
        for version in self:
            base_name = version.document_id.name or _('وثيقة')
            version_part = f"v{version.version_number}"
            
            if version.version_name:
                version_part += f" ({version.version_name})"
            
            version.display_name = f"{base_name} - {version_part}"

    def _compute_description(self):
        """مطابقة حقل الوصف مع ملخص التغييرات للحفاظ على توافق العرض"""
        for version in self:
            version.description = version.change_summary or False

    def _inverse_description(self):
        """عكس قيمة الوصف إلى ملخص التغييرات"""
        for version in self:
            if version.description is not None:
                version.change_summary = version.description

    
    @api.depends('content', 'attachment_ids')
    def _compute_content_hash(self):
        """حساب التوقيع الرقمي للمحتوى"""
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
        """تحديد الإصدار التالي"""
        for version in self:
            next_version = self.search([
                ('document_id', '=', version.document_id.id),
                ('version_number', '>', version.version_number)
            ], order='version_number asc', limit=1)
            
            version.next_version_id = next_version.id if next_version else False
    
    def action_activate(self):
        """تفعيل الإصدار وجعله الحالي"""
        for version in self:
            if version.state != 'draft':
                raise UserError(_('يمكن تفعيل المسودات فقط'))
            
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
        """إرسال الإصدار للاعتماد"""
        for version in self:
            if version.approval_status != 'draft':
                raise UserError(_('يمكن إرسال المسودات فقط للاعتماد'))
            version.write({'approval_status': 'pending'})
            version._log_version_activity('submitted')

    def action_approve(self):
        """اعتماد الإصدار"""
        for version in self:
            if version.approval_status != 'pending':
                raise UserError(_('يمكن اعتماد الإصدارات قيد الاعتماد فقط'))
            version.write({
                'approval_status': 'approved',
                'approved_by': self.env.user.employee_id.id,
                'approved_date': fields.Datetime.now()
            })
            version._log_version_activity('approved')

    def action_reject(self):
        """رفض الإصدار"""
        for version in self:
            if version.approval_status != 'pending':
                raise UserError(_('يمكن رفض الإصدارات قيد الاعتماد فقط'))
            version.write({'approval_status': 'rejected'})
            version._log_version_activity('rejected')

    def action_archive_version(self):
        """Alias for button to maintain XML compatibility"""
        return self.action_archive()

    def action_archive(self):
        """أرشفة الإصدار"""
        for version in self:
            if version.is_current:
                raise UserError(_('لا يمكن أرشفة الإصدار الحالي'))
            
            version.write({'state': 'archived'})
            version._log_version_activity('archived')
    
    def action_obsolete(self):
        """جعل الإصدار مهجوراً"""
        for version in self:
            if version.is_current:
                raise UserError(_('لا يمكن عزل الإصدار الحالي'))
            
            version.write({'state': 'obsolete'})
            version._log_version_activity('obsoleted')
    
    def action_view_document(self):
        """عرض محتوى الإصدار"""
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
        """تحميل الإصدار"""
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
        """مقارنة مع الإصدار السابق"""
        self.ensure_one()
        
        if not self.previous_version_id:
            raise UserError(_('لا يوجد إصدار سابق للمقارنة معه'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('مقارنة الإصدارات'),
            'res_model': 'document.version.compare',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_version1_id': self.previous_version_id.id,
                'default_version2_id': self.id
            }
        }
    
    def action_create_new_version(self):
        """إنشاء إصدار جديد من هذا الإصدار"""
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
            'change_summary': _('إصدار جديد مبني على الإصدار %s') % self.version_number,
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
        string='ملخص المقارنة',
        compute='_compute_comparison_summary'
    )

    def _compute_comparison_summary(self):
        """توليد ملخص مبسط للمقارنة مع الإصدار السابق إن وجد"""
        for version in self:
            if not version.previous_version_id:
                version.comparison_summary = _('لا يوجد إصدار سابق للمقارنة.')
                continue
            summary_parts = []
            summary_parts.append(_('<b>الإصدار الحالي:</b> %s') % version.version_number)
            summary_parts.append(_('<b>الإصدار السابق:</b> %s') % version.previous_version_id.version_number)
            if version.change_summary:
                summary_parts.append(_('<b>ملخص التغييرات:</b> %s') % version.change_summary)
            version.comparison_summary = '<br/>'.join(summary_parts)
    def _prepare_download_content(self):
        """تحضير محتوى للتحميل"""
        self.ensure_one()
        
        content_parts = []
        content_parts.append(f"الوثيقة: {self.document_id.name}")
        content_parts.append(f"الإصدار: {self.version_number}")
        content_parts.append(f"تاريخ الإنشاء: {self.created_date}")
        content_parts.append(f"أنشأ بواسطة: {self.created_by.name}")
        
        if self.change_summary:
            content_parts.append(f"ملخص التغييرات: {self.change_summary}")
        
        content_parts.append("=" * 50)
        
        if self.content:
            content_parts.append(self.content)
        
        return "\n\n".join(content_parts)
    
    def _log_version_activity(self, action):
        """تسجيل نشاط الإصدار"""
        self.ensure_one()
        
        activity_messages = {
            'activated': _('تم تفعيل الإصدار %s') % self.version_number,
            'archived': _('تم أرشفة الإصدار %s') % self.version_number,
            'obsoleted': _('تم عزل الإصدار %s') % self.version_number,
            'created': _('تم إنشاء الإصدار %s') % self.version_number,
        }
        
        message = activity_messages.get(action, _('تم تعديل الإصدار %s') % self.version_number)
        
        self.document_id.message_post(
            body=message,
            subtype_xmlid='mail.mt_note'
        )
    
    @api.constrains('document_id', 'version_number')
    def _check_version_uniqueness(self):
        """التحقق من تفرد رقم الإصدار لكل وثيقة"""
        for version in self:
            existing = self.search([
                ('document_id', '=', version.document_id.id),
                ('version_number', '=', version.version_number),
                ('id', '!=', version.id)
            ])
            
            if existing:
                raise ValidationError(_(
                    'رقم الإصدار %s موجود بالفعل لهذه الوثيقة'
                ) % version.version_number)
    
    @api.constrains('document_id', 'is_current')
    def _check_single_current_version(self):
        """التأكد من وجود إصدار حالي واحد فقط لكل وثيقة"""
        for version in self:
            if version.is_current:
                other_current = self.search([
                    ('document_id', '=', version.document_id.id),
                    ('is_current', '=', True),
                    ('id', '!=', version.id)
                ])
                
                if other_current:
                    raise ValidationError(_(
                        'يمكن أن يكون هناك إصدار حالي واحد فقط لكل وثيقة'
                    ))
    
    @api.constrains('version_number')
    def _check_version_number(self):
        """التحقق من صحة رقم الإصدار"""
        for version in self:
            if version.version_number <= 0:
                raise ValidationError(_('رقم الإصدار يجب أن يكون موجباً'))


class DocumentVersionCompare(models.TransientModel):
    """مقارنة إصدارات الوثائق"""
    
    _name = 'document.version.compare'
    _description = 'مقارنة إصدارات الوثائق'
    
    version1_id = fields.Many2one(
        'document.version',
        string='الإصدار الأول',
        required=True
    )
    
    version2_id = fields.Many2one(
        'document.version',
        string='الإصدار الثاني',
        required=True
    )
    
    comparison_result = fields.Html(
        string='نتيجة المقارنة',
        compute='_compute_comparison_result'
    )
    
    @api.depends('version1_id', 'version2_id')
    def _compute_comparison_result(self):
        """حساب نتيجة المقارنة"""
        for compare in self:
            if not compare.version1_id or not compare.version2_id:
                compare.comparison_result = _('يرجى تحديد كلا الإصدارين للمقارنة')
                continue
            
            result_parts = []
            
            result_parts.append('<h3>معلومات الإصدارين</h3>')
            result_parts.append('<table class="table table-bordered">')
            result_parts.append('<tr><th>البيان</th><th>الإصدار الأول</th><th>الإصدار الثاني</th></tr>')
            
            # رقم الإصدار
            result_parts.append(f'<tr><td>رقم الإصدار</td><td>{compare.version1_id.version_number}</td><td>{compare.version2_id.version_number}</td></tr>')
            
            result_parts.append(f'<tr><td>تاريخ الإنشاء</td><td>{compare.version1_id.created_date}</td><td>{compare.version2_id.created_date}</td></tr>')
            
            result_parts.append(f'<tr><td>أنشأ بواسطة</td><td>{compare.version1_id.created_by.name}</td><td>{compare.version2_id.created_by.name}</td></tr>')
            
            result_parts.append('</table>')
            
            if compare.version2_id.change_summary:
                result_parts.append('<h3>ملخص التغييرات</h3>')
                result_parts.append(f'<p>{compare.version2_id.change_summary}</p>')
            
            compare.comparison_result = ''.join(result_parts)


class DocumentVersionHistory(models.Model):
    """سجل أحداث إصدارات الوثائق"""
    
    _name = 'document.version.history'
    _description = 'سجل أحداث إصدارات الوثائق'
    _order = 'timestamp desc'
    
    version_id = fields.Many2one(
        'document.version',
        string='الإصدار',
        required=True,
        ondelete='cascade'
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='المستخدم',
        required=True,
        default=lambda self: self.env.user
    )
    
    action = fields.Selection([
        ('created', 'إنشاء'),
        ('activated', 'تفعيل'),
        ('archived', 'أرشفة'),
        ('obsoleted', 'عزل'),
        ('viewed', 'مشاهدة'),
        ('downloaded', 'تحميل'),
        ('compared', 'مقارنة')
    ], string='الإجراء', required=True)
    
    description = fields.Text(string='الوصف')
    
    timestamp = fields.Datetime(
        string='التوقيت',
        default=fields.Datetime.now,
        required=True
    )
    
    ip_address = fields.Char(string='عنوان IP')
    user_agent = fields.Char(string='متصفح المستخدم')

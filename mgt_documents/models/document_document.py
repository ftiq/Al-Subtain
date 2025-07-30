# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DocumentDocument(models.Model):
    _name = 'document.document'
    _description = 'الوثائق والمخاطبات'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    
    documents_document_id = fields.Many2one(
        'documents.document',
        string='مربوط بوثيقة Documents',
        help='ربط هذه الوثيقة بنظام Documents'
    )
    

    folder_id = fields.Many2one(
        'documents.folder',
        string='المجلد',
        help='مجلد تنظيم الوثيقة'
    )
    
    tag_ids = fields.Many2many(
        'documents.tag',
        string='العلامات',
        help='علامات تصنيف الوثيقة'
    )
    

    name = fields.Char(
        string='عنوان الوثيقة',
        required=True,
        tracking=True
    )
    
    reference_number = fields.Char(
        string='الرقم المرجعي',
        required=True,
        copy=False,
        default=lambda self: _('جديد'),
        tracking=True
    )
    
    display_name = fields.Char(
        string='الاسم المعروض',
        compute='_compute_display_name',
        store=True
    )
    
    date = fields.Datetime(
        string='تاريخ الوثيقة',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    subject = fields.Char(
        string='الموضوع',
        required=True,
        tracking=True
    )
    
    summary = fields.Text(
        string='الملخص',
        tracking=True
    )
    
    content = fields.Html(
        string='المحتوى'
    )
    

    document_type_id = fields.Many2one(
        'document.category',
        string='نوع الوثيقة',
        required=True,
        tracking=True,
        domain=[('parent_id', '!=', False)],
        default=lambda self: self._get_default_document_type()
    )
    
    category_id = fields.Many2one(
        'document.category',
        string='الفئة',
        required=True,
        tracking=True,
        default=lambda self: self._get_default_category()
    )
    
    priority = fields.Selection([
        ('0', 'عادي'),
        ('1', 'مهم'),
        ('2', 'عاجل'),
        ('3', 'عاجل جداً')
    ], string='الأولوية', default='0', tracking=True)
    

    document_type = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
        ('internal', 'داخلي'),
        ('report', 'تقرير'),
        ('memo', 'مذكرة'),

        ('circular', 'تعميم'),
        ('letter', 'رسالة'),
        ('contract', 'عقد'),
        ('invoice', 'فاتورة'),
        ('other', 'أخرى')
    ], string='نوع الوثيقة', default='other', tracking=True)
    
    urgency_level = fields.Selection([
        ('low', 'منخفض'),
        ('medium', 'متوسط'), 
        ('high', 'عالي'),
        ('critical', 'حرج')
    ], string='مستوى الاستعجال', compute='_compute_urgency_level', store=True)
    

    sender_id = fields.Many2one(
        'res.partner',
        string='الجهة المرسلة',
        tracking=True
    )
    
    sender_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المرسل',
        tracking=True
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string='الجهة المستقبلة',
        tracking=True
    )
    
    recipient_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المستقبل',
        tracking=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='القسم المختص',
        tracking=True
    )
    
    document_direction = fields.Selection([
        ('incoming', 'واردة'),
        ('outgoing', 'صادرة'),
        ('internal', 'داخلية')
    ], string='اتجاه الوثيقة', tracking=True)
    
    document_type_gov = fields.Selection([
        ('official_letter', 'رسالة رسمية'),
        ('memorandum', 'مذكرة'),
        ('circular', 'تعميم'),
        ('decision', 'قرار'),
        ('report', 'تقرير'),
        ('contract', 'عقد'),
        ('agreement', 'اتفاقية'),
        ('certificate', 'شهادة'),
        ('permit', 'تصريح'),
        ('other', 'أخرى')
    ], string='نوع الوثيقة الحكومي', tracking=True)
    
    confidentiality_level = fields.Selection([
        ('public', 'عام'),
        ('internal', 'داخلي'),
        ('restricted', 'مقيد'),
        ('confidential', 'سري'),
        ('top_secret', 'سري للغاية')
    ], string='مستوى السرية', default='internal', tracking=True)
    
    due_date = fields.Date(
        string='تاريخ الاستحقاق',
        tracking=True,
        help='التاريخ المطلوب إنجاز معاملة الوثيقة'
    )
    
    approval_requests = fields.One2many(
        'approval.request',
        'document_id',
        string='طلبات الموافقة'
    )
    
    approval_count = fields.Integer(
        string='عدد طلبات الموافقة',
        compute='_compute_approval_count'
    )
    
    is_overdue = fields.Boolean(
        string='متأخرة',
        compute='_compute_is_overdue'
    )
    
    completion_percentage = fields.Float(
        string='نسبة الإنجاز (%)',
        compute='_compute_completion_percentage'
    )
    
    has_pending_approvals = fields.Boolean(
        string='توجد موافقات معلقة',
        compute='_compute_has_pending_approvals'
    )

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدمة'),
        ('in_review', 'قيد المراجعة'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة'),
        ('archived', 'مؤرشفة'),
        ('cancelled', 'ملغاة')
    ], string='الحالة', default='draft', tracking=True, copy=False)
    
    approval_status = fields.Selection([
        ('pending', 'في انتظار الموافقة'),
        ('approved', 'موافق عليها'),
        ('rejected', 'مرفوضة'),
        ('cancelled', 'ملغاة')
    ], string='حالة الموافقة', default='pending', tracking=True)
    
    requires_signature_for_approval = fields.Boolean(
        string='يتطلب توقيع للموافقة',
        default=True,
        help='إذا كان مفعلاً، سيتطلب توقيع إلكتروني عند الموافقة'
    )
    
    signature_for_approval_id = fields.Many2one(
        'digital.signature',
        string='توقيع الموافقة',
        help='التوقيع الإلكتروني المرتبط بهذه الموافقة'
    )
    

    submitted_date = fields.Datetime(
        string='تاريخ التقديم',
        readonly=True,
        copy=False
    )
    
    reviewed_date = fields.Datetime(
        string='تاريخ المراجعة',
        readonly=True,
        copy=False
    )
    
    approved_date = fields.Datetime(
        string='تاريخ الاعتماد',
        readonly=True,
        copy=False
    )
    
    archived_date = fields.Datetime(
        string='تاريخ الأرشفة',
        readonly=True,
        copy=False
    )
    

    attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'document.document')],
        string='المرفقات'
    )
    
    attachment_count = fields.Integer(
        string='عدد المرفقات (مخفي)',
        compute='_compute_attachment_count',
        store=False
    )
    
    
    total_attachments_count = fields.Integer(
        string='إجمالي المرفقات',
        compute='_compute_total_attachments_count',
        store=True
    )
    

    digital_signature_ids = fields.One2many(
        'digital.signature',
        'document_id',
        string='التوقيعات الرقمية',
        auto_join=False
    )
    
    signature_count = fields.Integer(
        string='عدد التوقيعات',
        compute='_compute_signature_count'
    )
    
    is_signed = fields.Boolean(
        string='موقعة',
        compute='_compute_is_signed',
        store=True
    )
    


    history_ids = fields.One2many(
        'document.history',
        'document_id',
        string='سجل التغييرات'
    )
    
    history_count = fields.Integer(
        string='عدد التغييرات',
        compute='_compute_history_count'
    )
    

    is_confidential = fields.Boolean(
        string='سري',
        default=False,
        tracking=True
    )
    
    access_level = fields.Selection([
        ('public', 'عام'),
        ('internal', 'داخلي'),
        ('restricted', 'مقيد'),
        ('confidential', 'سري')
    ], string='مستوى الوصول', default='internal', tracking=True)
    

    auto_archive_date = fields.Date(
        string='تاريخ الأرشفة التلقائية',
        compute='_compute_auto_archive_date',
        store=True
    )
    
    retention_period = fields.Integer(
        string='فترة الاحتفاظ (بالأيام)',
        default=365,
        help='عدد الأيام للاحتفاظ بالوثيقة قبل الأرشفة التلقائية'
    )
    

    author = fields.Char(
        string='المؤلف',
        tracking=True
    )
    
    publisher = fields.Char(
        string='الناشر',
        tracking=True
    )
    
    publication_date = fields.Date(
        string='تاريخ النشر'
    )
    
    isbn = fields.Char(
        string='الرقم الدولي للكتاب (ISBN)'
    )
    
    language = fields.Selection([
        ('ar', 'العربية'),
        ('en', 'الإنجليزية'),
        ('fr', 'الفرنسية'),
        ('other', 'أخرى')
    ], string='اللغة', default='ar')
    
    page_count = fields.Integer(
        string='عدد الصفحات'
    )
    

    needs_approval = fields.Boolean(
        string='تحتاج موافقة',
        compute='_compute_needs_approval',
        store=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='اعتمدت بواسطة',
        readonly=True
    )
    
    rejection_reason = fields.Text(
        string='سبب الرفض',
        readonly=True
    )
    
    is_archived = fields.Boolean(
        string='مؤرشفة',
        compute='_compute_is_archived',
        store=True
    )
    
    archived_by = fields.Many2one(
        'res.users',
        string='أرشفت بواسطة',
        readonly=True
    )
    
    archive_location = fields.Char(
        string='موقع الأرشيف',
        readonly=True
    )
    

    keywords = fields.Many2many(
        'document.keyword',
        string='الكلمات المفتاحية'
    )
    
    confidentiality_level = fields.Selection([
        ('public', 'عام'),
        ('internal', 'داخلي'),
        ('confidential', 'سري'),
        ('top_secret', 'سري للغاية')
    ], string='مستوى السرية', default='internal', tracking=True)
    
    related_documents = fields.Many2many(
        'document.document',
        'document_related_rel',
        'document1_id',
        'document2_id',
        string='الوثائق ذات الصلة'
    )
    

    copy_to_user_ids = fields.Many2many(
        'res.users',
        'document_copy_to_rel',
        'document_id',
        'user_id',
        string='نسخة منه إلى',
        help='المستخدمون الذين سيتم إرسال نسخة من الوثيقة إليهم للقراءة فقط'
    )
    
    copy_message_id = fields.Many2one(
        'document.copy.message',
        string='رسالة النسخة',
        help='اختر رسالة معدة مسبقاً لإرسالها مع إشعار النسخة للمستخدمين المحددين',
        default=lambda self: self.env.ref('mgt_documents.copy_message_default', raise_if_not_found=False)
    )
    
    notification_sent = fields.Boolean(
        string='تم إرسال الإشعارات',
        default=False,
        readonly=True,
        help='يحدد ما إذا كانت إشعارات النسخة قد تم إرسالها'
    )
    
    notification_sent_date = fields.Datetime(
        string='تاريخ إرسال الإشعارات',
        readonly=True
    )
    
    notes = fields.Text(
        string='ملاحظات داخلية'
    )
    

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )
    

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        """تحديد نوع الوثيقة بناءً على document_type_id"""
        if self.document_type_id:
            doc_type_name = self.document_type_id.name.lower()
            if 'وارد' in doc_type_name:
                self.document_type = 'incoming'
            elif 'صادر' in doc_type_name:
                self.document_type = 'outgoing'
            elif 'داخلي' in doc_type_name:
                self.document_type = 'internal'
            elif 'تقرير' in doc_type_name:
                self.document_type = 'report'
            elif 'مذكرة' in doc_type_name:
                self.document_type = 'memo'
            elif 'تعميم' in doc_type_name:
                self.document_type = 'circular'
            elif 'رسالة' in doc_type_name:
                self.document_type = 'letter'
            elif 'عقد' in doc_type_name:
                self.document_type = 'contract'
            elif 'فاتورة' in doc_type_name:
                self.document_type = 'invoice'
            else:
                self.document_type = 'other'
    
    @api.onchange('document_type')
    def _onchange_document_type(self):
        """تحديد نوع الوثيقة والفئة بناءً على نوع الوثيقة المحدد"""
        if self.document_type:
            type_category_map = {
                'incoming': 'mgt_documents.category_incoming',
                'outgoing': 'mgt_documents.category_outgoing',
                'internal': 'mgt_documents.category_internal',
                'circular': 'mgt_documents.category_circulars',

                'memo': 'mgt_documents.category_memos',
                'report': 'mgt_documents.category_reports'
            }
            
            category_ref = type_category_map.get(self.document_type)
            if category_ref:
                category = self.env.ref(category_ref, raise_if_not_found=False)
                if category and category.is_active:
                    self.document_type_id = category.id
                    self.category_id = category.parent_id.id if category.parent_id else category.id

    @api.depends('name', 'reference_number')
    def _compute_display_name(self):
        """حساب الاسم المعروض للوثيقة"""
        for record in self:
            if record.reference_number and record.reference_number != _('جديد'):
                record.display_name = f"[{record.reference_number}] {record.name}"
            else:
                record.display_name = record.name or _('وثيقة جديدة')
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        """حساب عدد المرفقات (مخفي)"""
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.depends('digital_signature_ids')
    def _compute_signature_count(self):
        """حساب عدد التوقيعات"""
        for record in self:
            record.signature_count = len(record.digital_signature_ids)
    
    @api.depends('digital_signature_ids.is_valid')
    def _compute_is_signed(self):
        """تحديد ما إذا كانت الوثيقة موقعة"""
        for record in self:
            record.is_signed = any(sig.is_valid for sig in record.digital_signature_ids)
    

    
    @api.depends('approval_request_ids')
    def _compute_approval_count(self):
        """حساب عدد طلبات الموافقة"""
        for record in self:
            count = len(record.approval_request_ids)
            record.approval_count = count
            record.approval_request_count = count
    
    @api.depends('approval_request_ids.status')
    def _compute_has_pending_approvals(self):
        """تحديد وجود طلبات موافقة معلقة"""
        for record in self:
            record.has_pending_approvals = any(
                req.status in ['pending', 'approved_pending_signature'] 
                for req in record.approval_request_ids
            )
    
    @api.depends('history_ids')
    def _compute_history_count(self):
        """حساب عدد التغييرات في السجل"""
        for record in self:
            record.history_count = len(record.history_ids)
    
    @api.depends('date', 'retention_period')
    def _compute_auto_archive_date(self):
        """حساب تاريخ الأرشفة التلقائية"""
        for record in self:
            if record.date and record.retention_period:
                archive_date = record.date + timedelta(days=record.retention_period)
                record.auto_archive_date = archive_date.date()
            else:
                record.auto_archive_date = False
    
    @api.depends('document_type')
    def _compute_needs_approval(self):
        """تحديد ما إذا كانت الوثيقة تحتاج موافقة"""
        for record in self:
            record.needs_approval = record.document_type in ['outgoing', 'circular', 'memo', 'report']
    
    @api.depends('state')
    def _compute_is_archived(self):
        """تحديد ما إذا كانت الوثيقة مؤرشفة"""
        for record in self:
            record.is_archived = record.state == 'archived'
    
    @api.depends('approval_request_ids')
    def _compute_approval_request_count(self):
        """حساب عدد طلبات الموافقة"""
        for record in self:
            record.approval_request_count = len(record.approval_request_ids)
    

    @api.depends('priority', 'state', 'date')
    def _compute_urgency_level(self):
        """حساب مستوى الاستعجال بناءً على الأولوية والحالة والتاريخ"""
        for record in self:
            urgency = 'low'  
            

            if record.priority == '3': 
                urgency = 'critical'
            elif record.priority == '2': 
                urgency = 'high'
            elif record.priority == '1': 
                urgency = 'medium'
            
            if record.state in ['submitted', 'in_review'] and urgency != 'critical':
                urgency = 'medium' if urgency == 'low' else 'high'
            
            if record.date:
                days_old = (fields.Datetime.now() - record.date).days
                if days_old > 7 and urgency in ['low', 'medium']:
                    urgency = 'medium' if urgency == 'low' else 'high'
            
            record.urgency_level = urgency


        
    @api.depends('attachment_ids')
    def _compute_total_attachments_count(self):
        """حساب إجمالي عدد المرفقات"""
        for record in self:
            record.total_attachments_count = len(record.attachment_ids)
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء وثيقة جديدة مع رقم مرجعي تلقائي"""
        for vals in vals_list:
            if vals.get('reference_number', _('جديد')) == _('جديد'):
                doc_type_id = vals.get('document_type_id')
                if doc_type_id:
                    doc_type_record = self.env['document.category'].browse(doc_type_id)
                    if 'وارد' in doc_type_record.name:
                        sequence_code = 'document.incoming'
                    elif 'صادر' in doc_type_record.name:
                        sequence_code = 'document.outgoing'
                    elif 'داخلي' in doc_type_record.name:
                        sequence_code = 'document.internal'
                    elif 'تعميم' in doc_type_record.name:
                        sequence_code = 'document.circular'

                    else:
                        sequence_code = 'document.incoming'
                else:
                    sequence_code = 'document.incoming'
                vals['reference_number'] = self.env['ir.sequence'].next_by_code(sequence_code) or _('جديد')
        
        documents = super().create(vals_list)
        
        for document in documents:
            document._create_history_record('created', _('تم إنشاء الوثيقة'))
        
        return documents
    
    def write(self, vals):
        """تحديث الوثيقة مع تسجيل التغييرات"""
        tracked_fields = {
            'state': 'الحالة',
            'approval_status': 'حالة الموافقة',
            'name': 'العنوان',
            'subject': 'الموضوع',
            'category_id': 'الفئة',
            'priority': 'الأولوية'
        }
        
        changes = []
        for field, field_name in tracked_fields.items():
            if field in vals:
                try:
                    for record in self:
                        old_value = getattr(record, field)
                        new_value = vals[field]
                        if old_value != new_value:
                            if (hasattr(record._fields[field], 'comodel_name') and 
                                record._fields[field].comodel_name and 
                                record._fields[field].comodel_name in self.env):
                                
                                comodel_name = record._fields[field].comodel_name
                                
                                if old_value:
                                    try:
                                        old_record = self.env[comodel_name].browse(old_value)
                                        old_display = old_record.display_name if old_record.exists() else str(old_value)
                                    except Exception:
                                        old_display = str(old_value)
                                else:
                                    old_display = _('غير محدد')
                                
                                if new_value:
                                    try:
                                        new_record = self.env[comodel_name].browse(new_value)
                                        new_display = new_record.display_name if new_record.exists() else str(new_value)
                                    except Exception:
                                        new_display = str(new_value)
                                else:
                                    new_display = _('غير محدد')
                                
                                changes.append(f"{field_name}: {old_display} ← {new_display}")

                            elif hasattr(record._fields[field], 'selection'):
                                old_display = dict(record._fields[field].selection).get(old_value, old_value)
                                new_display = dict(record._fields[field].selection).get(new_value, new_value)
                                changes.append(f"{field_name}: {old_display} ← {new_display}")
                            else:
                                changes.append(f"{field_name}: {old_value} ← {new_value}")
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Error tracking field {field}: {str(e)}")
                    continue
        
        result = super().write(vals)
        

        if changes:
            try:
                for record in self:
                    record._create_history_record('updated', '; '.join(changes))
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Error creating history record: {str(e)}")
        
        return result
    
    def unlink(self):
        """حذف الوثيقة مع التحقق من الصلاحيات"""
        for record in self:
            if record.state not in ('draft', 'cancelled'):
                raise UserError(_('لا يمكن حذف الوثيقة إلا في حالة المسودة أو الملغاة'))
            

            record._create_history_record('deleted', _('تم حذف الوثيقة'))
        
        return super().unlink()
    

    def _get_default_document_type(self):
        """الحصول على نوع الوثيقة الافتراضي"""

        default_type = self.env.ref('mgt_documents.category_incoming', raise_if_not_found=False)
        if default_type and default_type.is_active:
            return default_type.id
        

        default_type = self.env['document.category'].search([
            ('parent_id', '!=', False),
            ('is_active', '=', True)
        ], limit=1)
        return default_type.id if default_type else False
    
    def _get_default_category(self):
        """الحصول على الفئة الافتراضية"""

        default_category = self.env.ref('mgt_documents.category_administrative', raise_if_not_found=False)
        if default_category and default_category.is_active:
            return default_category.id
        

        default_category = self.env['document.category'].search([
            ('is_active', '=', True)
        ], limit=1)
        return default_category.id if default_category else False
    
    def _create_history_record(self, action, description, old_state=None, new_state=None):
        """إنشاء سجل في تاريخ الوثيقة"""
        self.env['document.history'].create({
            'document_id': self.id,
            'user_id': self.env.user.id,
            'action': action,
            'description': description,
            'timestamp': fields.Datetime.now(),
            'previous_state': old_state,
            'new_state': new_state or self.state,
        })
    

    def action_submit(self):
        """تقديم الوثيقة للمراجعة"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('يمكن تقديم الوثيقة للمراجعة من حالة المسودة فقط'))
            
            old_state = record.state
            record.write({
                'state': 'submitted',
                'submitted_date': fields.Datetime.now()
            })
            
            record._create_history_record('submitted', _('تم إرسال الوثيقة للمراجعة'), old_state, 'submitted')
            
            if record.document_type_id and any(keyword in record.document_type_id.name for keyword in ['صادر', 'تعميم', 'مذكرة']):
                record._create_approval_request()
    
    def action_start_review(self):
        """بدء مراجعة الوثيقة"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('يمكن بدء المراجعة للوثائق المقدمة فقط'))
            
            old_state = record.state
            record.write({
                'state': 'in_review',
                'reviewed_date': fields.Datetime.now()
            })
            
            record._create_history_record('reviewed', _('تم بدء مراجعة الوثيقة'), old_state, 'in_review')
    
    def action_approve(self):
        """اعتماد الوثيقة مع خيار التوقيع"""
        self.ensure_one()
        if self.state != 'in_review':
            raise UserError(_('يمكن اعتماد الوثائق قيد المراجعة فقط'))
        
        return {
            'name': _('اعتماد الوثيقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_requires_signature': getattr(self, 'requires_signature_for_approval', False),
            }
        }
            

        
    def complete_approval_with_signature(self, signature_id):
        """إكمال الموافقة بعد التوقيع الإلكتروني"""
        self.ensure_one()
        
        signature = self.env['digital.signature'].browse(signature_id)
        if not signature or signature.state != 'signed':
            raise UserError(_('يجب إكمال التوقيع الإلكتروني أولاً'))
            
        old_state = self.state
        self.write({
            'state': 'approved',
            'approval_status': 'approved',
            'approved_date': fields.Datetime.now(),
            'signature_for_approval_id': signature_id
        })
        
        self._create_history_record(
            'approved', 
            _('تم اعتماد الوثيقة مع التوقيع الإلكتروني بواسطة %s') % signature.signer_id.name, 
            old_state, 
            'approved'
        )
        

        self.message_post(
            body=_('✅ تم اعتماد الوثيقة بنجاح مع التوقيع الإلكتروني'),
            subject=_('اعتماد الوثيقة'),
            message_type='notification'
        )
        
        return True
        
    def approve_document(self, with_signature=False, signature_data=None):
        """اعتماد موحد للوثيقة"""
        self.ensure_one()
        
        old_state = self.state
        approval_data = {
            'state': 'approved',
            'approval_status': 'approved',
            'approved_date': fields.Datetime.now()
        }
        
        message = _('تم اعتماد الوثيقة')
        
        if with_signature and signature_data:
            signature = self.env['digital.signature'].create({
                'name': f'توقيع موافقة - {self.name}',
                'document_id': self.id,
                'signer_id': self.env.user.id,
                'signature_data': signature_data,
                'signature_method': 'electronic'
            })
            approval_data['signature_for_approval_id'] = signature.id
            message += f' مع التوقيع بواسطة {self.env.user.name}'
        else:
            message += f' بواسطة {self.env.user.name}'
        
        self.write(approval_data)
        self._create_history_record('approved', message, old_state, 'approved')
        self.message_post(body=f'✅ {message}', message_type='notification')
        
        return True
    
    def action_reject(self):
        """رفض الوثيقة"""
        for record in self:
            if record.state not in ('submitted', 'in_review'):
                raise UserError(_('يمكن رفض الوثائق المقدمة أو قيد المراجعة فقط'))
            
            old_state = record.state
            record.write({
                'state': 'rejected',
                'approval_status': 'rejected'
            })
            
            record._create_history_record('rejected', _('تم رفض الوثيقة'), old_state, 'rejected')
    
    def action_archive(self):
        """أرشفة الوثيقة"""
        for record in self:
            if record.state not in ('approved', 'rejected'):
                raise UserError(_('يمكن أرشفة الوثائق المعتمدة أو المرفوضة فقط'))
            
            old_state = record.state
            record.write({
                'state': 'archived',
                'archived_date': fields.Datetime.now()
            })
            
            record._create_history_record('archived', _('تم أرشفة الوثيقة'), old_state, 'archived')
    
    def action_cancel(self):
        """إلغاء الوثيقة"""
        for record in self:
            if record.state == 'archived':
                raise UserError(_('لا يمكن إلغاء الوثائق المؤرشفة'))
            
            old_state = record.state
            record.write({'state': 'cancelled'})
            
            record._create_history_record('cancelled', _('تم إلغاء الوثيقة'), old_state, 'cancelled')
    
    def action_reset_to_draft(self):
        """إعادة الوثيقة إلى حالة المسودة"""
        for record in self:
            if record.state not in ('rejected', 'cancelled'):
                raise UserError(_('يمكن إعادة الوثائق المرفوضة أو الملغاة إلى المسودة فقط'))
            
            old_state = record.state
            record.write({
                'state': 'draft',
                'approval_status': 'pending',
                'submitted_date': False,
                'reviewed_date': False,
                'approved_date': False,
                'archived_date': False
            })
            

            record._create_history_record('restored', _('تم إعادة الوثيقة إلى المسودة'), old_state, 'draft')
    
    def _create_approval_request(self):
        """إنشاء طلب موافقة للوثيقة"""

        approver = self._get_approver()
        
        if approver:
            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
            if category:
                self.env['approval.request'].create({
                    'name': f'طلب موافقة على الوثيقة: {self.name}',
                    'category_id': category.id,
                    'request_owner_id': self.env.user.id,
                    'date_start': fields.Datetime.now(),
                    'reason': f'طلب موافقة على الوثيقة رقم: {self.reference_number or self.name}',
                    'document_id': self.id,
                })
    
    def _get_approver(self):
        """تحديد الموافق المناسب"""
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
        
        group = self.env.ref('mgt_documents.group_document_manager', raise_if_not_found=False)
        if group and group.users:
            return group.users[0]
        
        return False
    
    def _transfer_attachments_to_approval(self, approval_request):
        """نقل المرفقات من الوثيقة إلى طلب الموافقة"""
        if not self.attachment_ids:
            return
            

        existing_names = self.env['ir.attachment'].search([
            ('res_model', '=', 'approval.request'),
            ('res_id', '=', approval_request.id)
        ]).mapped('name')
        
        transferred_count = 0
        for attachment in self.attachment_ids:
            transfer_name = f"[من الوثيقة] {attachment.name}"
            

            if transfer_name not in existing_names:
                attachment.copy({
                    'res_model': 'approval.request',
                    'res_id': approval_request.id,
                    'name': transfer_name
                })
                transferred_count += 1
                
        if transferred_count > 0:
            _logger.info(f"تم نقل {transferred_count} مرفق من الوثيقة {self.reference_number} إلى طلب الموافقة {approval_request.id}")
    
    def _get_approval_category(self):
        """تحديد فئة الموافقة بناءً على نوع الوثيقة"""
        category_mapping = {
            'incoming': 'INCOMING_DOCS',
            'outgoing': 'OUTGOING_DOCS', 
            'internal': 'INTERNAL_DOCS',
            'memo': 'MEMO_APPROVAL',
            'circular': 'CIRCULAR_APPROVAL',
            'report': 'REPORT_APPROVAL',
            'contract': 'CONTRACT_APPROVAL'
        }
        
        doc_type = getattr(self, 'document_type', 'other')
        category_name = category_mapping.get(doc_type, 'GENERAL')
        
        category = self.env['approval.category'].search([('name', '=', category_name)], limit=1)
        if not category:
            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
        
        return category
    



    def action_view_attachments(self):
        """عرض المرفقات التقليدية المرتبطة بالوثيقة"""
        return {
            'name': _('المرفقات'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', 'document.document'), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': 'document.document',
                'default_res_id': self.id,
            }
        }
    
    def action_view_signatures(self):
        """عرض التوقيعات الرقمية"""
        if not self.digital_signature_ids:
            return {
                'name': _('توقيع الوثيقة'),
                'type': 'ir.actions.act_window',
                'res_model': 'digital.signature',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_document_id': self.id,
                    'default_signer_id': self.env.user.id,
                    'default_signature_method': 'electronic'
                }
            }
        else:
            return {
                'name': _('التوقيعات الرقمية'),
                'type': 'ir.actions.act_window',
                'res_model': 'digital.signature',
                'view_mode': 'list,form',
                'domain': [('document_id', 'in', self.ids)],
                'context': {
                    'default_document_id': self.id if len(self) == 1 else False,
                    'default_signer_id': self.env.user.id,
                    'default_signature_method': 'electronic'
                }
            }
    
    def action_view_approvals(self):
        """عرض طلبات الموافقة"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات الموافقة'),
            'res_model': 'approval.request',
            'view_mode': 'tree,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id}
        }
    
    def action_view_history(self):
        """عرض سجل التغييرات"""
        return {
            'name': _('سجل التغييرات'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.history',
            'view_mode': 'list,form',
            'domain': [('document_id', 'in', self.ids)],
            'context': {'default_document_id': self.id if len(self) == 1 else False}
        }
    

    @api.constrains('date')
    def _check_date(self):
        """التحقق من صحة التاريخ"""
        for record in self:
            if record.date and record.date > fields.Datetime.now():
                raise ValidationError(_('لا يمكن أن يكون تاريخ الوثيقة في المستقبل'))
    
    @api.constrains('retention_period')
    def _check_retention_period(self):
        """التحقق من فترة الاحتفاظ"""
        for record in self:
            if record.retention_period and record.retention_period < 1:
                raise ValidationError(_('يجب أن تكون فترة الاحتفاظ أكبر من صفر'))
    
    @api.model
    def _update_existing_document_types(self):
        """تحديث نوع الوثيقة للوثائق الموجودة"""
        try:
            domain = ['|', ('document_type', '=', False), ('document_type', '=', 'other')]
            documents = self.search(domain)
            
            for doc in documents:
                try:
                    if not doc.name or not doc.subject:
                        continue
                        
                    if doc.document_type_id and doc.document_type_id.name:
                        doc_type_name = doc.document_type_id.name.lower()
                        new_type = 'other'  
                        
                        if 'وارد' in doc_type_name:
                            new_type = 'incoming'
                        elif 'صادر' in doc_type_name:
                            new_type = 'outgoing'
                        elif 'داخلي' in doc_type_name:
                            new_type = 'internal'
                        elif 'تقرير' in doc_type_name:
                            new_type = 'report'
                        elif 'مذكرة' in doc_type_name:
                            new_type = 'memo'
                        elif 'تعميم' in doc_type_name:
                            new_type = 'circular'
                        elif 'رسالة' in doc_type_name:
                            new_type = 'letter'
                        elif 'عقد' in doc_type_name:
                            new_type = 'contract'
                        elif 'فاتورة' in doc_type_name:
                            new_type = 'invoice'
                        
                        doc.with_context(skip_validation=True).write({'document_type': new_type})
                        
                    elif not doc.document_type:
                        doc.with_context(skip_validation=True).write({'document_type': 'other'})
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
            
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء وثيقة جديدة مع الترقيم الصحيح"""
        for vals in vals_list:
            document_type = vals.get('document_type', 'other')
            
            if vals.get('reference_number', _('جديد')) == _('جديد'):

                sequence_mapping = {
                    'incoming': 'document.incoming',
                    'outgoing': 'document.outgoing', 
                    'internal': 'document.internal',
                    'report': 'document.report',
                    'memo': 'document.memo',

                    'circular': 'document.circular',
                    'letter': 'document.letter',
                    'contract': 'document.contract',
                    'invoice': 'document.invoice',
                    'other': 'document.other'
                }
                
                sequence_code = sequence_mapping.get(document_type, 'document.other')
                reference_number = self.env['ir.sequence'].next_by_code(sequence_code)
                
                if reference_number:
                    vals['reference_number'] = reference_number
                else:
                    vals['reference_number'] = f"{document_type.upper()}-{fields.Datetime.now().year}-001"
        
        return super().create(vals_list)
    
    def action_request_approval(self):
        """طلب موافقة موحد"""
        self.ensure_one()
        
        category = self._get_approval_category()
        suggested_approver = self._get_approver()
        urgency_mapping = {'0': 'normal', '1': 'urgent', '2': 'very_urgent', '3': 'critical'}
        
        return {
            'name': _('طلب موافقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_name': f'موافقة على الوثيقة: {self.name}',
                'default_category_id': category.id if category else False,
                'default_request_owner_id': self.env.user.id,
                'default_urgency_level': urgency_mapping.get(self.priority, 'normal'),
                'default_confidentiality_level': getattr(self, 'confidentiality_level', 'internal'),
                'default_department_id': self.department_id.id if self.department_id else False,
                'default_reason': f'طلب موافقة على الوثيقة رقم: {self.reference_number}',
                'transfer_document_attachments': True,
                'suggested_approver_id': suggested_approver.id if suggested_approver else False,
            }
        }

    @api.depends('approval_requests')
    def _compute_approval_count(self):
        """حساب عدد طلبات الموافقة"""
        for record in self:
            record.approval_count = len(record.approval_requests)
    
    @api.depends('due_date')
    def _compute_is_overdue(self):
        """تحديد ما إذا كانت الوثيقة متأخرة"""
        today = fields.Date.today()
        for record in self:
            record.is_overdue = (
                record.due_date and 
                record.due_date < today and 
                record.state not in ['approved', 'archived', 'cancelled']
            )
    
    @api.depends('state')
    def _compute_completion_percentage(self):
        """حساب نسبة إنجاز الوثيقة"""
        for record in self:
            percentages = {
                'draft': 0,
                'submitted': 20,
                'in_review': 40,
                'approved': 100,
                'rejected': 0,
                'archived': 100,
                'cancelled': 0
            }
            record.completion_percentage = percentages.get(record.state, 0)
    
    @api.depends('approval_requests.request_status')
    def _compute_has_pending_approvals(self):
        """تحديد ما إذا كانت هناك موافقات معلقة"""
        for record in self:
            pending_approvals = record.approval_requests.filtered(
                lambda r: r.request_status in ['new', 'pending', 'under_approval']
            )
            record.has_pending_approvals = bool(pending_approvals)
    

    
    def action_view_smart_approvals(self):
        """عرض طلبات الموافقة الذكية"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات الموافقة'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id}
        }
    
    def action_approve(self):
        """اعتماد موحد - بمعالج موافقة وتوقيع"""
        self.ensure_one()
        

        return {
            'name': _('معالج اعتماد الوثيقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_approval_notes': f'اعتماد مباشر للوثيقة: {self.name}',
                'default_requires_signature': self.requires_signature_for_approval,
                'default_is_direct_approval': True,
                'from_document_approve': True
            }
        }
    
    def approve_document(self, with_signature=False, signature_data=None):
        """اعتماد مباشر للوثيقة مع التوقيع الاختياري"""
        self.ensure_one()
        

        if with_signature and signature_data:
            signature = self.env['digital.signature'].create({
                'name': f'توقيع اعتماد: {self.name}',
                'document_id': self.id,
                'signer_id': self.env.user.id,
                'signature_data': signature_data,
                'signature_method': 'electronic',
                'signature_date': fields.Datetime.now(),
                'is_valid': True
            })
            self.signature_for_approval_id = signature.id
        

        self.write({
            'state': 'approved',
            'approval_status': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        

        signature_note = ' مع توقيع رقمي' if with_signature else ''
        self._create_history_record(
            'approved', 
            f'تم اعتماد الوثيقة مباشرة{signature_note}',
            'in_review',
            'approved'
        )
        
        return True
    
    def action_request_approval(self):
        """طلب موافقة عبر نظام approvals القياسي"""
        self.ensure_one()
        

        return {
            'name': _('إنشاء طلب موافقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_name': f'طلب موافقة للوثيقة: {self.name}',
                'default_request_owner_id': self.env.user.id,
                'from_document_approval': True
            }
        }
    
    def action_view_related_documents(self):
        """عرض الوثائق ذات الصلة"""
        self.ensure_one()
        
        if not self.related_documents:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'لا توجد وثائق ذات صلة بهذه الوثيقة',
                    'type': 'info'
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'الوثائق ذات الصلة بـ {self.name}',
            'res_model': 'document.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.related_documents.ids)],
            'context': {
                'search_default_group_by_state': 1,
            }
        }
    
    def action_send_copy_notifications(self):
        """إرسال إشعارات النسخ للمستخدمين المحددين"""
        self.ensure_one()
        
        if not self.copy_to_user_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'لم يتم تحديد مستخدمين لإرسال النسخة إليهم',
                    'type': 'warning'
                }
            }
        

        for user in self.copy_to_user_ids:

            message_body = f"""نسخة من الوثيقة: {self.name}

عنوان الوثيقة: {self.name}
الرقم المرجعي: {self.reference_number or 'غير محدد'}
النوع: {dict(self._fields['document_type'].selection).get(self.document_type, self.document_type)}
التاريخ: {self.date.strftime('%Y-%m-%d %H:%M') if self.date else 'غير محدد'}

رسالة النسخة:
{self.copy_message_id.message if self.copy_message_id else 'يرجى الاطلاع على الوثيقة المرفقة للعلم والمتابعة اللازمة.'}

ملاحظة: هذه نسخة للقراءة فقط"""
            


            mail_template = self.env.ref('mgt_documents.email_template_copy_notification', raise_if_not_found=False)
            if mail_template:
                mail_template.with_context(
                    recipient_user=user,
                    copy_message=self.copy_message_id.message if self.copy_message_id else 'يرجى الاطلاع على الوثيقة المرفقة للعلم والمتابعة اللازمة.'
                ).send_mail(self.id, force_send=False)
            

            if user.partner_id not in self.message_follower_ids.mapped('partner_id'):
                self.message_subscribe([user.partner_id.id])
            

            copy_reader_group = self.env.ref('mgt_documents.group_document_copy_reader', raise_if_not_found=False)
            if copy_reader_group and copy_reader_group not in user.groups_id:
                user.sudo().write({'groups_id': [(4, copy_reader_group.id)]})
        

        self.write({
            'notification_sent': True,
            'notification_sent_date': fields.Datetime.now()
        })
        

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'تم إرسال إشعارات النسخة لـ {len(self.copy_to_user_ids)} مستخدمين',
                'type': 'success'
            }
        }
    
    def check_copy_access(self):
        """تحقق من صلاحية الوصول للنسخة"""
        self.ensure_one()
        current_user = self.env.user
        

        if current_user in self.copy_to_user_ids:
            return {
                'can_read': True,
                'can_write': False,
                'can_delete': False,
                'access_type': 'copy_reader'
            }
        

        return {
            'can_read': True,
            'can_write': True,
            'can_delete': True,
            'access_type': 'full_access'
        }
    
    @api.onchange('document_direction', 'document_type_gov')
    def _onchange_smart_classification(self):
        """تصنيف تلقائي ذكي للوثائق"""
        if self.document_direction and self.document_type_gov:
            direction_labels = {
                'incoming': 'واردة',
                'outgoing': 'صادرة', 
                'internal': 'داخلية'
            }
            
            type_labels = {
                'official_letter': 'رسائل رسمية',
                'memorandum': 'مذكرات',
                'circular': 'تعاميم',
                'decision': 'قرارات',
                'report': 'تقارير',
                'contract': 'عقود',
                'permit': 'تصاريح'
            }
            
            direction_label = direction_labels.get(self.document_direction, '')
            type_label = type_labels.get(self.document_type_gov, '')
            
            if direction_label and type_label:
                folder_name = f'{direction_label} - {type_label}'
                
                folder = self.env['documents.folder'].search([
                    ('name', '=', folder_name)
                ], limit=1)
                
                if folder:
                    self.folder_id = folder.id
    
    _sql_constraints = [
        ('reference_number_unique', 'UNIQUE(reference_number, company_id)', 'الرقم المرجعي يجب أن يكون فريداً!'),
        ('retention_period_positive', 'CHECK(retention_period > 0)', 'فترة الاحتفاظ يجب أن تكون أكبر من صفر!'),
    ]


class DocumentKeyword(models.Model):
    """نموذج الكلمات المفتاحية للوثائق"""
    
    _name = 'document.keyword'
    _description = 'الكلمات المفتاحية'
    _order = 'name'
    
    name = fields.Char(
        string='الكلمة المفتاحية',
        required=True
    )
    
    description = fields.Text(
        string='الوصف'
    )
    
    color = fields.Integer(
        string='اللون',
        default=0
    )
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'الكلمة المفتاحية يجب أن تكون فريدة!')
    ] 
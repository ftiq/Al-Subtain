# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DocumentDocument(models.Model):
    """نموذج الوثيقة الأساسي لإدارة الكتب الإلكترونية والمخاطبات الإدارية"""
    
    _name = 'document.document'
    _description = 'الوثائق والمخاطبات'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    

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
        string='المحتوى',
        tracking=True
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
        string='عدد المرفقات',
        compute='_compute_attachment_count',
        store=True
    )
    

    digital_signature_ids = fields.One2many(
        'digital.signature',
        'document_id',
        string='التوقيعات الرقمية'
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
    

    approval_request_ids = fields.One2many(
        'document.approval.request',
        'document_id',
        string='طلبات الموافقة'
    )
    
    approval_count = fields.Integer(
        string='عدد طلبات الموافقة',
        compute='_compute_approval_count'
    )
    
    approval_request_count = fields.Integer(
        string='عدد طلبات الموافقة',
        compute='_compute_approval_count'
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
    

    document_type = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
        ('internal', 'داخلي'),
        ('circular', 'تعميم'),
        ('ebook', 'كتاب إلكتروني'),
        ('memo', 'مذكرة'),
        ('report', 'تقرير')
    ], string='نوع الوثيقة', required=True, tracking=True)
    

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
        'document_document_rel',
        'document_id',
        'related_document_id',
        string='الوثائق ذات الصلة'
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
    

    @api.onchange('document_type')
    def _onchange_document_type(self):
        """تحديد نوع الوثيقة والفئة بناءً على نوع الوثيقة المحدد"""
        if self.document_type:
            type_category_map = {
                'incoming': 'mgt_documents.category_incoming',
                'outgoing': 'mgt_documents.category_outgoing',
                'internal': 'mgt_documents.category_internal',
                'circular': 'mgt_documents.category_circulars',
                'ebook': 'mgt_documents.category_ebooks_reference',
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
        """حساب عدد المرفقات"""
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
                    elif 'كتاب' in doc_type_record.name:
                        sequence_code = 'document.ebook'
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
                for record in self:
                    old_value = getattr(record, field)
                    new_value = vals[field]
                    if old_value != new_value:

                        if hasattr(record._fields[field], 'comodel_name'):
                            old_display = record[field].display_name if old_value else _('غير محدد')
                            new_display = self.env[record._fields[field].comodel_name].browse(new_value).display_name if new_value else _('غير محدد')
                            changes.append(f"{field_name}: {old_display} ← {new_display}")

                        elif hasattr(record._fields[field], 'selection'):
                            old_display = dict(record._fields[field].selection).get(old_value, old_value)
                            new_display = dict(record._fields[field].selection).get(new_value, new_value)
                            changes.append(f"{field_name}: {old_display} ← {new_display}")
                        else:
                            changes.append(f"{field_name}: {old_value} ← {new_value}")
        
        result = super().write(vals)
        

        if changes:
            for record in self:
                record._create_history_record('updated', '; '.join(changes))
        
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
    
    def _create_history_record(self, action, description):
        """إنشاء سجل في تاريخ الوثيقة"""
        self.env['document.history'].create({
            'document_id': self.id,
            'user_id': self.env.user.id,
            'action': action,
            'description': description,
            'timestamp': fields.Datetime.now(),
            'previous_state': self.state if action != 'created' else False,
            'new_state': self.state if action != 'deleted' else False,
        })
    

    def action_submit(self):
        """تقديم الوثيقة للمراجعة"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('يمكن تقديم الوثيقة للمراجعة من حالة المسودة فقط'))
            
            record.write({
                'state': 'submitted',
                'submitted_date': fields.Datetime.now()
            })
            

            if record.document_type_id and any(keyword in record.document_type_id.name for keyword in ['صادر', 'تعميم', 'مذكرة']):
                record._create_approval_request()
    
    def action_start_review(self):
        """بدء مراجعة الوثيقة"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('يمكن بدء المراجعة للوثائق المقدمة فقط'))
            
            record.write({
                'state': 'in_review',
                'reviewed_date': fields.Datetime.now()
            })
    
    def action_approve(self):
        """اعتماد الوثيقة"""
        for record in self:
            if record.state != 'in_review':
                raise UserError(_('يمكن اعتماد الوثائق قيد المراجعة فقط'))
            
            record.write({
                'state': 'approved',
                'approval_status': 'approved',
                'approved_date': fields.Datetime.now()
            })
    
    def action_reject(self):
        """رفض الوثيقة"""
        for record in self:
            if record.state not in ('submitted', 'in_review'):
                raise UserError(_('يمكن رفض الوثائق المقدمة أو قيد المراجعة فقط'))
            
            record.write({
                'state': 'rejected',
                'approval_status': 'rejected'
            })
    
    def action_archive(self):
        """أرشفة الوثيقة"""
        for record in self:
            if record.state not in ('approved', 'rejected'):
                raise UserError(_('يمكن أرشفة الوثائق المعتمدة أو المرفوضة فقط'))
            
            record.write({
                'state': 'archived',
                'archived_date': fields.Datetime.now()
            })
    
    def action_cancel(self):
        """إلغاء الوثيقة"""
        for record in self:
            if record.state == 'archived':
                raise UserError(_('لا يمكن إلغاء الوثائق المؤرشفة'))
            
            record.write({'state': 'cancelled'})
    
    def action_reset_to_draft(self):
        """إعادة الوثيقة إلى حالة المسودة"""
        for record in self:
            if record.state not in ('rejected', 'cancelled'):
                raise UserError(_('يمكن إعادة الوثائق المرفوضة أو الملغاة إلى المسودة فقط'))
            
            record.write({
                'state': 'draft',
                'approval_status': 'pending'
            })
    
    def _create_approval_request(self):
        """إنشاء طلب موافقة للوثيقة"""

        approver = self._get_approver()
        
        if approver:
            self.env['document.approval.request'].create({
                'document_id': self.id,
                'approver_id': approver.id,
                'request_date': fields.Datetime.now(),
                'status': 'pending'
            })
    
    def _get_approver(self):
        """تحديد الموافق المناسب للوثيقة"""

        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
        

        group = self.env.ref('mgt_documents.group_document_manager', raise_if_not_found=False)
        if group and group.users:
            return group.users[0]
        
        return False
    

    def action_view_attachments(self):
        """عرض المرفقات"""
        return {
            'name': _('المرفقات'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', self._name), ('res_id', 'in', self.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id if len(self) == 1 else False,
            }
        }
    
    def action_view_signatures(self):
        """عرض التوقيعات الرقمية"""
        return {
            'name': _('التوقيعات الرقمية'),
            'type': 'ir.actions.act_window',
            'res_model': 'digital.signature',
            'view_mode': 'tree,form',
            'domain': [('document_id', 'in', self.ids)],
            'context': {'default_document_id': self.id if len(self) == 1 else False}
        }
    
    def action_view_approvals(self):
        """عرض طلبات الموافقة"""
        return {
            'name': _('طلبات الموافقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.approval.request',
            'view_mode': 'tree,form',
            'domain': [('document_id', 'in', self.ids)],
            'context': {'default_document_id': self.id if len(self) == 1 else False}
        }
    
    def action_view_history(self):
        """عرض سجل التغييرات"""
        return {
            'name': _('سجل التغييرات'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.history',
            'view_mode': 'tree,form',
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
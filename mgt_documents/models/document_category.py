# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DocumentCategory(models.Model):
    """نموذج فئات الوثائق لتصنيف وتنظيم الوثائق"""
    
    _name = 'document.category'
    _description = 'فئات الوثائق'
    _inherit = ['mail.thread']
    _order = 'sequence, name'
    _parent_store = True
    _rec_name = 'complete_name'
    
    name = fields.Char(
        string='اسم الفئة',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='رمز الفئة',
        help='رمز فريد للفئة'
    )
    
    description = fields.Text(
        string='الوصف',
        tracking=True
    )
    
    is_active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='يستخدم لترتيب الفئات في القوائم'
    )
    
    color = fields.Integer(
        string='اللون',
        help='لون الفئة في الواجهات'
    )
    

    parent_id = fields.Many2one(
        'document.category',
        string='الفئة الأب',
        index=True,
        ondelete='cascade',
        tracking=True
    )
    
    parent_path = fields.Char(
        index=True,
        unaccent=False
    )
    
    child_ids = fields.One2many(
        'document.category',
        'parent_id',
        string='الفئات الفرعية'
    )
    
    complete_name = fields.Char(
        string='الاسم الكامل',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    

    allowed_document_types = fields.Char(
        string='الأنواع المسموحة',
        help='أنواع الوثائق المسموحة (مفصولة بفواصل)',
        tracking=True
    )
    
    specific_document_types = fields.Text(
        string='أنواع محددة',
        help='الأنواع المحددة المسموحة عند اختيار "مخصص" (مفصولة بفواصل)'
    )
    

    document_count = fields.Integer(
        string='عدد الوثائق',
        compute='_compute_document_count',
        store=True
    )
    

    allowed_department_ids = fields.Many2many(
        'hr.department',
        string='الأقسام المخولة',
        help='الأقسام التي يمكنها استخدام هذه الفئة'
    )
    
    allowed_user_ids = fields.Many2many(
        'res.users',
        string='المستخدمون المخولون',
        help='المستخدمون الذين يمكنهم استخدام هذه الفئة'
    )
    
    is_public = fields.Boolean(
        string='عامة',
        default=True,
        help='إذا كانت مفعلة، يمكن لجميع المستخدمين استخدام هذه الفئة'
    )
    

    auto_archive_enabled = fields.Boolean(
        string='تفعيل الأرشفة التلقائية',
        default=False,
        help='تفعيل الأرشفة التلقائية للوثائق في هذه الفئة'
    )
    
    auto_archive_days = fields.Integer(
        string='أيام الأرشفة',
        default=365,
        help='عدد الأيام قبل الأرشفة التلقائية'
    )
    
    archive_condition = fields.Selection([
        ('after_approval', 'بعد الموافقة'),
        ('after_days', 'بعد عدد أيام محدد'),
        ('manual', 'يدوي فقط')
    ], string='شرط الأرشفة', default='after_days')
    
    notify_before_archive = fields.Boolean(
        string='إشعار قبل الأرشفة',
        default=False,
        help='إرسال إشعار قبل أرشفة الوثائق'
    )
    
    notification_days = fields.Integer(
        string='أيام الإشعار',
        default=7,
        help='عدد الأيام قبل الأرشفة لإرسال الإشعار'
    )
    
    default_priority = fields.Selection([
        ('low', 'منخفضة'),
        ('normal', 'عادية'),
        ('high', 'عالية'),
        ('urgent', 'عاجلة')
    ], string='الأولوية الافتراضية', default='normal')
    
    requires_approval = fields.Boolean(
        string='تتطلب موافقة',
        default=False,
        help='هل تتطلب الوثائق في هذه الفئة موافقة إدارية'
    )
    
    allowed_group_ids = fields.Many2many(
        'res.groups',
        string='المجموعات المخولة',
        help='المجموعات التي يمكنها استخدام هذه الفئة'
    )
    
    active_document_count = fields.Integer(
        string='عدد الوثائق النشطة',
        compute='_compute_document_counts',
        store=True
    )
    
    archived_document_count = fields.Integer(
        string='عدد الوثائق المؤرشفة',
        compute='_compute_document_counts',
        store=True
    )
    

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """حساب الاسم الكامل للفئة"""
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name
    
    @api.depends('document_ids', 'document_ids.state', 'document_type_ids', 'document_type_ids.state')
    def _compute_document_count(self):
        """حساب عدد الوثائق في الفئة"""
        for category in self:

            category.document_count = len(category.document_ids) + len(category.document_type_ids)
    
    @api.depends('document_ids', 'document_ids.state', 'document_type_ids', 'document_type_ids.state')
    def _compute_document_counts(self):
        """حساب عدد الوثائق النشطة والمؤرشفة"""
        for category in self:
            all_docs = category.document_ids + category.document_type_ids
            category.active_document_count = len(all_docs.filtered(lambda d: d.state != 'archived'))
            category.archived_document_count = len(all_docs.filtered(lambda d: d.state == 'archived'))
    

    document_ids = fields.One2many(
        'document.document',
        'category_id',
        string='الوثائق'
    )
    
    document_type_ids = fields.One2many(
        'document.document',
        'document_type_id',
        string='الوثائق من هذا النوع'
    )
    

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """التحقق من عدم وجود حلقة في التسلسل الهرمي"""
        if not self._check_recursion():
            raise ValidationError(_('لا يمكن إنشاء فئة فرعية من نفسها'))
    
    @api.constrains('auto_archive_days')
    def _check_auto_archive_days(self):
        """التحقق من صحة عدد أيام الأرشفة"""
        for category in self:
            if category.auto_archive_enabled and category.auto_archive_days < 1:
                raise ValidationError(_('يجب أن يكون عدد أيام الأرشفة أكبر من صفر'))
    

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء فئة جديدة"""
        categories = super().create(vals_list)
        return categories
    
    def write(self, vals):
        """تحديث الفئة"""
        result = super().write(vals)
        

        if 'parent_id' in vals:
            self._compute_complete_name()
        
        return result
    
    def unlink(self):
        """حذف الفئة مع التحقق من وجود وثائق"""
        for category in self:
            total_docs = len(category.document_ids) + len(category.document_type_ids)
            if total_docs > 0:
                raise ValidationError(
                    _('لا يمكن حذف الفئة "%s" لأنها تحتوي على %d وثيقة') % 
                    (category.name, total_docs)
                )
        
        return super().unlink()
    

    def action_view_documents(self):
        """عرض وثائق الفئة"""
        return {
            'name': _('وثائق الفئة: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': ['|', ('category_id', 'child_of', self.ids), ('document_type_id', 'child_of', self.ids)],
            'context': {
                'default_category_id': self.id,
                'search_default_category_id': self.id,
            }
        }
    
    def action_archive_documents(self):
        """أرشفة جميع وثائق الفئة"""
        documents = self.env['document.document'].search([
            '|', 
            ('category_id', 'child_of', self.ids),
            ('document_type_id', 'child_of', self.ids),
            ('state', 'in', ['approved', 'rejected'])
        ])
        
        if documents:
            documents.action_archive()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تم بنجاح'),
                    'message': _('تم أرشفة %d وثيقة') % len(documents),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تنبيه'),
                    'message': _('لا توجد وثائق قابلة للأرشفة في هذه الفئة'),
                    'type': 'warning',
                }
            }
    

    def get_allowed_document_types(self):
        """الحصول على أنواع الوثائق المسموحة للفئة"""
        if not self.allowed_document_types:
            return []
        
        types = [t.strip() for t in self.allowed_document_types.split(',') if t.strip()]
        return types
    
    def is_accessible_by_user(self, user=None):
        """التحقق من إمكانية وصول المستخدم للفئة"""
        if not user:
            user = self.env.user
        
        if self.is_public:
            return True
        
        if user in self.allowed_user_ids:
            return True
        
        if user.employee_id and user.employee_id.department_id in self.allowed_department_ids:
            return True
        
        return False
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )
    

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'رمز الفئة يجب أن يكون فريداً'),
        ('archive_days_positive', 'CHECK(auto_archive_days > 0)', 'عدد أيام الأرشفة يجب أن يكون موجباً'),
    ] 
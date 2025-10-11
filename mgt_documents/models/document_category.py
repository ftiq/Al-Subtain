# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


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
        index=True
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
    
    @api.model
    def get_allowed_categories(self, user_id=None):
        """الحصول على الفئات المسموحة للمستخدم"""
        if not user_id:
            user_id = self.env.user.id
            
        user = self.env['res.users'].browse(user_id)
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        
        domain = ['|', ('is_public', '=', True)]
        

        auth_conditions = []
        if employee and employee.department_id:
            auth_conditions.append(('allowed_department_ids', 'in', [employee.department_id.id]))
        auth_conditions.append(('allowed_user_ids', 'in', [user_id]))
        
        if auth_conditions:
            domain.extend(['|'] * (len(auth_conditions) - 1))
            domain.extend(auth_conditions)
            
        return self.search(domain)
    
    def check_user_access(self, user_id=None):
        """فحص صلاحية المستخدم لاستخدام هذه الفئة"""
        if not user_id:
            user_id = self.env.user.id
            
        if self.is_public:
            return True
            
        user = self.env['res.users'].browse(user_id)
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        

        if user_id in self.allowed_user_ids.ids:
            return True
            

        if employee and employee.department_id and employee.department_id.id in self.allowed_department_ids.ids:
            return True
            
        return False
    

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
    

    default_sla_hours = fields.Float(
        string='مدة SLA الافتراضية (ساعات)',
        default=72.0,
        help='المدة الافتراضية لإنجاز وثائق هذه الفئة'
    )
    
    priority_sla_hours = fields.Json(
        string='مدد SLA حسب الأولوية',
        default=lambda self: {
            '0': 168,  
            '1': 72,   
            '2': 24,   
            '3': 4     
        },
        help='مدد SLA مختلفة لكل مستوى أولوية'
    )
    
    department_sla_hours = fields.Json(
        string='مدد SLA حسب القسم',
        default=lambda self: {},
        help='مدد SLA مخصصة لأقسام معينة (department_id: hours)'
    )
    
    escalation_enabled = fields.Boolean(
        string='تفعيل التصعيد',
        default=True,
        help='تفعيل تصعيد تلقائي عند تجاوز SLA'
    )
    
    escalation_percentage = fields.Float(
        string='نسبة التصعيد (%)',
        default=80.0,
        help='نسبة الوقت المستغرق قبل التصعيد'
    )
    
    notification_schedule = fields.Json(
        string='جدول الإشعارات',
        default=lambda self: {
            'first_reminder': 50,    
            'second_reminder': 75,   
            'final_warning': 90      
        },
        help='جدول إرسال التذكيرات والتنبيهات'
    )
    
    working_hours_only = fields.Boolean(
        string='ساعات العمل فقط',
        default=True,
        help='حساب SLA في ساعات العمل فقط (استثناء عطل نهاية الأسبوع)'
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
    
    @api.depends('document_ids', 'document_type_ids')
    def _compute_document_count(self):
        """حساب عدد الوثائق في الفئة"""
        for category in self:

            category.document_count = len(category.document_ids) + len(category.document_type_ids)
    
    @api.depends('document_ids.is_archived', 'document_type_ids.is_archived')
    def _compute_document_counts(self):
        """حساب عدد الوثائق النشطة والمؤرشفة"""
        for category in self:
            all_docs = category.document_ids + category.document_type_ids
            category.active_document_count = len(all_docs.filtered(lambda d: not d.is_archived))
            category.archived_document_count = len(all_docs.filtered(lambda d: d.is_archived))
    

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
        for record in self:
            if record.parent_id:
                if not record._check_recursion():
                    raise ValidationError(_('لا يمكن إنشاء فئة فرعية من نفسها'))
    
    @api.constrains('auto_archive_days')
    def _check_auto_archive_days(self):
        """التحقق من صحة عدد أيام الأرشفة"""
        for category in self:
            if category.auto_archive_enabled and category.auto_archive_days < 1:
                raise ValidationError(_('يجب أن يكون عدد أيام الأرشفة أكبر من صفر'))
    
    def get_sla_hours(self, priority='1', department_id=None):
        """حساب مدة SLA بناءً على الأولوية والقسم"""
        self.ensure_one()
        
        if department_id and self.department_sla_hours:
            dept_hours = self.department_sla_hours.get(str(department_id))
            if dept_hours:
                return float(dept_hours)
        
        if self.priority_sla_hours:
            priority_hours = self.priority_sla_hours.get(str(priority))
            if priority_hours:
                return float(priority_hours)
        
        return self.default_sla_hours or 72.0
    
    def calculate_due_date(self, start_date, priority='1', department_id=None):

        self.ensure_one()
        
        if not start_date:
            start_date = fields.Datetime.now()
        
        sla_hours = self.get_sla_hours(priority, department_id)
        
        if self.working_hours_only:
            working_days_needed = sla_hours / 8.0
            due_date = self._add_working_days(start_date, working_days_needed)
        else:
            due_date = start_date + timedelta(hours=sla_hours)
        
        return due_date
    
    def _add_working_days(self, start_date, working_days):

        current_date = start_date
        days_added = 0
        
        while days_added < working_days:
            current_date += timedelta(days=1)

            if current_date.weekday() < 5: 
                days_added += 1
        
        return current_date
    
    def get_escalation_date(self, start_date, priority='1', department_id=None):
        self.ensure_one()
        
        if not self.escalation_enabled:
            return False
        
        due_date = self.calculate_due_date(start_date, priority, department_id)
        total_duration = due_date - start_date
        escalation_duration = total_duration * (self.escalation_percentage / 100.0)
        
        return start_date + escalation_duration
    
    def get_notification_dates(self, start_date, priority='1', department_id=None):
        
        self.ensure_one()
        
        if not self.notification_schedule:
            return {}
        
        due_date = self.calculate_due_date(start_date, priority, department_id)
        total_duration = due_date - start_date
        
        notification_dates = {}
        for reminder_type, percentage in self.notification_schedule.items():
            reminder_duration = total_duration * (percentage / 100.0)
            notification_dates[reminder_type] = start_date + reminder_duration
        
        return notification_dates
    

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء فئة جديدة"""
        categories = super().create(vals_list)
        return categories
    
    def write(self, vals):
        """تحديث الفئة"""

        if 'color' in vals and vals['color']:
            color_value = vals['color']
            if isinstance(color_value, str):
                if color_value.startswith('#'):
                    try:
                        vals['color'] = int(color_value[1:], 16)
                    except ValueError:
                        vals['color'] = 0
                else:
                    try:
                        vals['color'] = int(color_value)
                    except ValueError:
                        vals['color'] = 0
        
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
            ('processing_state', 'in', ['approved', 'rejected', 'completed'])
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
    
    def calculate_sla_deadline(self, priority='1', department_id=None, document_type='incoming', user_id=None, company_id=None):

        self.ensure_one()
        
        sla_hours = self.get_sla_hours(priority, department_id)
        
        multiplier = 1.0
        
        if self.document_type_multipliers:
            type_multiplier = self.document_type_multipliers.get(document_type, 1.0)
            multiplier *= type_multiplier
        
        if self.consider_working_hours:
           
            company = self.env['res.company'].browse(company_id) if company_id else self.env.company
            work_hours_per_day = self._get_work_hours_per_day(company)
            
            work_days = sla_hours / work_hours_per_day if work_hours_per_day > 0 else sla_hours / 8
            
            deadline = self._calculate_business_deadline(work_days, company)
            
        else:
            adjusted_hours = sla_hours * multiplier
            deadline = fields.Datetime.now() + timedelta(hours=adjusted_hours)
        
        return deadline
    
    def _get_work_hours_per_day(self, company):
        """حساب عدد ساعات العمل في اليوم"""
        try:
            if hasattr(company, 'resource_calendar_id') and company.resource_calendar_id:
                calendar = company.resource_calendar_id

                total_hours = sum(attendance.hour_to - attendance.hour_from 
                                for attendance in calendar.attendance_ids 
                                if not attendance.date_from)
                working_days = len(set(calendar.attendance_ids.mapped('dayofweek')))
                return total_hours / working_days if working_days > 0 else 8.0
        except Exception:
            pass
        return 8.0 
    
    def _calculate_business_deadline(self, work_days, company):
        """حساب موعد نهائي بناءً على أيام العمل"""
        start_date = fields.Datetime.now()
        
        try:
            if hasattr(company, 'resource_calendar_id') and company.resource_calendar_id:
                calendar = company.resource_calendar_id
                
                end_date = calendar.plan_hours(
                    work_days * self._get_work_hours_per_day(company),
                    start_date
                )
                return end_date
        except Exception:
            pass
        
        
        current_date = start_date
        days_added = 0
        
        while days_added < work_days:
            current_date += timedelta(days=1)
            
            if current_date.weekday() not in [4, 5]: 
                days_added += 1
        
        return current_date
    
    @api.model
    def get_sla_recommendations(self, document_data):
        """إعطاء توصيات SLA بناءً على بيانات الوثيقة"""
        category_id = document_data.get('category_id')
        priority = document_data.get('priority', '1')
        department_id = document_data.get('department_id')
        document_type = document_data.get('document_type', 'incoming')
        
        if not category_id:
            return {
                'recommended_hours': 72,
                'deadline': fields.Datetime.now() + timedelta(hours=72),
                'confidence': 'low',
                'reason': 'لم يتم تحديد فئة الوثيقة'
            }
        
        category = self.browse(category_id)
        
        recommended_hours = category.get_sla_hours(priority, department_id)
        deadline = category.calculate_sla_deadline(
            priority=priority,
            department_id=department_id,
            document_type=document_type
        )
        
        confidence = 'high'
        reason = 'تم حساب SLA بناءً على إعدادات الفئة'
        
        if not category.priority_sla_hours:
            confidence = 'medium'
            reason = 'تم استخدام SLA افتراضي للفئة'
        
        return {
            'recommended_hours': recommended_hours,
            'deadline': deadline,
            'confidence': confidence,
            'reason': reason,
            'category_name': category.name
        } 
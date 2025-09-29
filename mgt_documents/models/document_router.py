# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class DocumentRouter(models.Model):
    """محرك التوجيه للوثائق - مبسط"""
    
    _name = 'document.router'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'محرك التوجيه للوثائق'
    _order = 'priority desc, sequence asc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='اسم قاعدة التوجيه',
        required=True,
        tracking=True
    )
    
    description = fields.Text(
        string='وصف القاعدة',
        help='وصف تفصيلي لقاعدة التوجيه'
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب تطبيق القاعدة'
    )
    
    priority = fields.Selection([
        ('0', 'منخفض'),
        ('1', 'عادي'),
        ('2', 'عالي'),
        ('3', 'عاجل')
    ], string='الأولوية', default='1', tracking=True)
    
    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )

    state = fields.Selection([
        ('active', 'نشط'),
        ('inactive', 'معطل')
    ], string='الحالة', default='inactive', tracking=True)

    filter_document_type = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
        ('internal', 'داخلي'),
        ('circular', 'تعميم'),
        ('memo', 'مذكرة'),
        ('report', 'تقرير'),
        ('request', 'طلب'),
        ('letter', 'خطاب'),
        ('contract', 'عقد'),
        ('other', 'أخرى')
    ], string='نوع الوثيقة', help='نوع الوثيقة لتطبيق هذه القاعدة عليها')
    
    filter_priority = fields.Selection([
        ('0', 'منخفض'),
        ('1', 'عادي'),
        ('2', 'عالي'),
        ('3', 'عاجل'),
        ('4', 'حرج')
    ], string='الأولوية المطلوبة', help='الأولوية المطلوبة لتطبيق هذه القاعدة')
    
    filter_departments = fields.Many2many(
        'hr.department',
        'router_filter_dept_rel',
        'router_id',
        'department_id',
        string='الأقسام المحددة',
        help='تطبيق القاعدة فقط على الوثائق من هذه الأقسام'
    )
    
    filter_keywords = fields.Char(
        string='الكلمات المفتاحية',
        help='كلمات مفتاحية في عنوان الوثيقة (مفصولة بفواصل)'
    )

    applicable_category_ids = fields.Many2many(
        'document.category',
        'document_router_category_rel',
        'router_id',
        'category_id',
        string='الفئات المطبقة'
    )

    applicable_department_ids = fields.Many2many(
        'hr.department',
        'document_router_dept_rel',
        'router_id',
        'department_id',
        string='الأقسام المطبقة'
    )

    target_process_id = fields.Many2one(
        'workflow.process',
        string='العملية المستهدفة',
        help='العملية التي سيتم تشغيلها عند تطبيق القاعدة'
    )

    task_template = fields.Text(
        string='قالب المهمة',
        help='نموذج للمهمة التي سيتم إنشاؤها'
    )

    notification_message = fields.Char(
        string='رسالة الإشعار',
        help='رسالة يتم إرسالها عند تطبيق القاعدة'
    )

    create_approval_request = fields.Boolean(
        string='إنشاء طلب موافقة',
        default=False,
        help='إنشاء طلب موافقة تلقائياً'
    )

    approval_category_id = fields.Many2one(
        'approval.category',
        string='فئة الموافقة',
        help='فئة طلب الموافقة المراد إنشاؤه'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )

    def action_activate(self):
        """تفعيل القاعدة"""
        self.write({'state': 'active', 'active': True})

    def action_deactivate(self):
        """إلغاء تفعيل القاعدة"""
        self.write({'state': 'inactive', 'active': False})
    
    def matches_document(self, document):
        """فحص ما إذا كانت القاعدة تنطبق على الوثيقة"""
        self.ensure_one()
        
        if not self.active or self.state != 'active':
            return False
        
        if self.filter_document_type and document.document_type != self.filter_document_type:
            return False
        
        if self.filter_priority and document.priority != self.filter_priority:
            return False
        
        if self.filter_departments and document.department_id not in self.filter_departments:
            return False
        
        if self.filter_keywords:
            keywords = [k.strip() for k in self.filter_keywords.split(',')]
            document_text = (document.name or '').lower()
            if not any(keyword.lower() in document_text for keyword in keywords):
                return False
        
        return True
    
    def apply_to_document(self, document):
        """تطبيق القاعدة على الوثيقة"""
        self.ensure_one()
        
        if not self.matches_document(document):
            return False
        
        results = []
        
        if self.target_process_id:
            try:
                instance = self.target_process_id.create_instance(
                    document_id=document.id,
                    trigger_data={'router_rule_id': self.id}
                )
                results.append(f"تم إنشاء عملية سير عمل: {instance.name}")
            except Exception as e:
                _logger.error(f"Error creating workflow instance: {str(e)}")
        
        if self.task_template:
            try:
                task = self.env['admin.task'].create({
                    'name': f"مهمة من قاعدة التوجيه: {self.name}",
                    'description': self.task_template,
                    'request_document_id': document.id,
                    'assigned_department_id': self.applicable_department_ids[0].id if self.applicable_department_ids else False,
                    'priority': self.filter_priority or '1',
                })
                results.append(f"تم إنشاء مهمة: {task.name}")
            except Exception as e:
                _logger.error(f"Error creating task: {str(e)}")
        
        if self.create_approval_request and self.approval_category_id:
            try:
                approval = self.env['approval.request'].create({
                    'name': f"طلب موافقة: {document.name}",
                    'category_id': self.approval_category_id.id,
                    'document_id': document.id,
                    'request_owner_id': self.env.user.id,
                })
                results.append(f"تم إنشاء طلب موافقة: {approval.name}")
            except Exception as e:
                _logger.error(f"Error creating approval request: {str(e)}")
        
        if self.notification_message:
            try:
                document.message_post(
                    body=self.notification_message,
                    message_type='notification'
                )
                results.append("تم إرسال الإشعار")
            except Exception as e:
                _logger.error(f"Error sending notification: {str(e)}")
        
        return {
            'success': bool(results),
            'message': '\n'.join(results) if results else _('لم تنطبق أي قاعدة توجيه'),
            'actions': results,
        }
    
    @api.model
    def process_document(self, document):
        """معالجة وثيقة بجميع القواعد المطبقة وإرجاع نتيجة موحدة"""
        active_rules = self.search([
            ('active', '=', True),
            ('state', '=', 'active')
        ], order='priority desc, sequence asc')
        
        actions = []
        for rule in active_rules:
            try:
                rule_results = rule.apply_to_document(document)
                if rule_results:
                    actions.extend(rule_results)
            except Exception as e:
                _logger.error(f"Error applying rule {rule.name}: {str(e)}")
                continue
        
        message = '\n'.join(actions) if actions else _('لم تنطبق أي قاعدة توجيه')
        return {
            'success': bool(actions),
            'message': message,
            'actions': actions,
        }
    
    @api.constrains('filter_departments', 'applicable_department_ids')
    def _check_departments(self):
        """التحقق من صحة الأقسام"""
        for rule in self:
            if rule.filter_departments and rule.applicable_department_ids:
                if not set(rule.filter_departments.ids).intersection(set(rule.applicable_department_ids.ids)):
                    raise ValidationError(_('يجب أن تتضمن الأقسام المطبقة قسماً واحداً على الأقل من الأقسام المحددة في الشروط'))
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResUsers(models.Model):
    """تمديد نموذج المستخدمين لإضافة وظائف إدارة الوثائق"""
    
    _inherit = 'res.users'


    document_signature = fields.Binary(
        string='التوقيع الافتراضي',
        help='التوقيع الافتراضي للمستخدم في الوثائق'
    )
    
    can_approve_documents = fields.Boolean(
        string='يمكن اعتماد الوثائق',
        default=False,
        help='ما إذا كان المستخدم يمكنه اعتماد الوثائق'
    )
    
    approval_limit = fields.Selection([
        ('unlimited', 'غير محدود'),
        ('department', 'قسمه فقط'),
        ('team', 'فريقه فقط'),
        ('none', 'لا يوجد')
    ], string='حد الاعتماد', default='none', 
       help='نطاق صلاحية اعتماد الوثائق')
    
    document_access_level = fields.Selection([
        ('all', 'جميع الوثائق'),
        ('department', 'وثائق القسم'),
        ('own', 'وثائقه الشخصية'),
        ('assigned', 'الوثائق المخصصة له')
    ], string='مستوى الوصول للوثائق', default='own',
       help='مستوى الوصول للوثائق في النظام')
    

    notify_document_approval = fields.Boolean(
        string='إشعار طلبات الموافقة',
        default=True,
        help='إرسال إشعارات عند وجود طلبات موافقة'
    )
    
    notify_document_updates = fields.Boolean(
        string='إشعار تحديثات الوثائق',
        default=True,
        help='إرسال إشعارات عند تحديث الوثائق المتابعة'
    )
    
    notify_document_expiry = fields.Boolean(
        string='إشعار انتهاء صلاحية الوثائق',
        default=True,
        help='إرسال إشعارات قبل انتهاء صلاحية الوثائق'
    )
    

    documents_created_count = fields.Integer(
        string='عدد الوثائق المنشأة',
        compute='_compute_document_statistics'
    )
    
    documents_approved_count = fields.Integer(
        string='عدد الوثائق المعتمدة',
        compute='_compute_document_statistics'
    )
    
    pending_approvals_count = fields.Integer(
        string='عدد الموافقات المعلقة',
        compute='_compute_document_statistics'
    )
    
    signatures_count = fields.Integer(
        string='عدد التوقيعات',
        compute='_compute_document_statistics'
    )
    

    is_sample_receipt_approver = fields.Boolean(
        string='Sample Receipt Approver',
        default=False,
        help='Technical field to fix view validation error'
    )
    

    @api.depends('name')
    def _compute_document_statistics(self):
        """حساب إحصائيات الوثائق للمستخدم"""
        for user in self:

            user.documents_created_count = self.env['document.document'].search_count([
                ('create_uid', '=', user.id)
            ])
            

            user.documents_approved_count = self.env['approval.request'].search_count([
                ('approver_ids.user_id', '=', user.id),
                ('request_status', '=', 'approved')
            ])
            

            user.pending_approvals_count = self.env['approval.request'].search_count([
                ('approver_ids.user_id', '=', user.id),
                ('request_status', '=', 'pending')
            ])
            

            user.signatures_count = self.env['digital.signature'].search_count([
                ('user_id', '=', user.id)
            ])
    

    def get_accessible_documents(self):
        """الحصول على الوثائق التي يمكن للمستخدم الوصول إليها"""
        self.ensure_one()
        
        domain = []
        
        if self.document_access_level == 'all':
            pass
        elif self.document_access_level == 'department':

            if self.employee_id and self.employee_id.department_id:
                domain.append(('department_id', '=', self.employee_id.department_id.id))
            else:
                domain.append(('id', '=', 0)) 
        elif self.document_access_level == 'own':
            domain.append(('create_uid', '=', self.id))
        elif self.document_access_level == 'assigned':
            domain.extend([
                '|', '|',
                ('create_uid', '=', self.id),
                ('sender_employee_id.user_id', '=', self.id),
                ('recipient_employee_id.user_id', '=', self.id)
            ])
        
        return self.env['document.document'].search(domain)
    
    def can_approve_document(self, document):
        """التحقق من إمكانية اعتماد الوثيقة"""
        self.ensure_one()
        
        if not self.can_approve_documents:
            return False
        
        if self.approval_limit == 'unlimited':
            return True
        elif self.approval_limit == 'department':
            return (
                self.employee_id and 
                self.employee_id.department_id and
                document.department_id == self.employee_id.department_id
            )
        elif self.approval_limit == 'team':
            return (
                self.employee_id and
                document.sender_employee_id and
                self.employee_id.department_id == document.sender_employee_id.department_id
            )
        
        return False
    
    def get_pending_approvals(self):
        """الحصول على طلبات الموافقة المعلقة للمستخدم"""
        self.ensure_one()
        
        return self.env['approval.request'].search([
            ('approver_ids.user_id', '=', self.id),
            ('request_status', '=', 'pending')
        ])
    

    

    def action_view_my_documents(self):
        """عرض وثائق المستخدم"""
        self.ensure_one()
        
        accessible_docs = self.get_accessible_documents()
        
        return {
            'name': _('وثائقي'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', accessible_docs.ids)],
            'context': {'default_create_uid': self.id}
        }
    
    def action_view_pending_approvals(self):
        """عرض طلبات الموافقة المعلقة"""
        self.ensure_one()
        
        return {
            'name': _('طلبات الموافقة المعلقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [
                ('approver_ids.user_id', '=', self.id),
                ('request_status', 'in', ['new', 'pending', 'under_approval'])
            ],
        }
    
    def action_view_my_signatures(self):
        """عرض توقيعات المستخدم"""
        self.ensure_one()
        
        return {
            'name': _('توقيعاتي'),
            'type': 'ir.actions.act_window',
            'res_model': 'digital.signature',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
        }
    
 
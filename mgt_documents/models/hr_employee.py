# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    """تمديد نموذج الموظفين لإضافة وظائف إدارة الوثائق"""
    
    _inherit = 'hr.employee'
    

    is_document_approver = fields.Boolean(
        string='موافق على الوثائق',
        default=False,
        help='ما إذا كان الموظف يمكنه اعتماد الوثائق'
    )
    
    approval_authority_level = fields.Selection([
        ('basic', 'أساسي'),
        ('intermediate', 'متوسط'),
        ('advanced', 'متقدم'),
        ('executive', 'تنفيذي')
    ], string='مستوى صلاحية الاعتماد', default='basic',
       help='مستوى صلاحية اعتماد الوثائق')
    
    document_categories_ids = fields.Many2many(
        'document.category',
        'employee_document_category_rel',
        'employee_id',
        'document_category_id',
        string='فئات الوثائق المخولة',
        help='فئات الوثائق التي يمكن للموظف التعامل معها'
    )
    

    delegate_approvals_to = fields.Many2one(
        'hr.employee',
        string='تفويض الموافقات إلى',
        help='الموظف المفوض لاعتماد الوثائق نيابة عن هذا الموظف'
    )
    
    delegation_start_date = fields.Date(
        string='تاريخ بداية التفويض',
        help='تاريخ بداية تفويض الموافقات'
    )
    
    delegation_end_date = fields.Date(
        string='تاريخ نهاية التفويض',
        help='تاريخ نهاية تفويض الموافقات'
    )
    
    delegation_reason = fields.Text(
        string='سبب التفويض',
        help='سبب تفويض الموافقات (إجازة، سفر، إلخ)'
    )
    

    documents_created_count = fields.Integer(
        string='عدد الوثائق المنشأة',
        compute='_compute_document_statistics'
    )
    
    documents_received_count = fields.Integer(
        string='عدد الوثائق المستلمة',
        compute='_compute_document_statistics'
    )
    
    documents_sent_count = fields.Integer(
        string='عدد الوثائق المرسلة',
        compute='_compute_document_statistics'
    )
    
    approvals_pending_count = fields.Integer(
        string='عدد الموافقات المعلقة',
        compute='_compute_document_statistics'
    )
    
    approvals_completed_count = fields.Integer(
        string='عدد الموافقات المكتملة',
        compute='_compute_document_statistics'
    )
    
    signatures_count = fields.Integer(
        string='عدد التوقيعات',
        compute='_compute_document_statistics'
    )
    

    @api.depends('name')
    def _compute_document_statistics(self):
        """حساب إحصائيات الوثائق للموظف"""
        for employee in self:

            employee.documents_created_count = self.env['document.document'].search_count([
                ('sender_employee_id', '=', employee.id)
            ])
            

            employee.documents_received_count = self.env['document.document'].search_count([
                ('recipient_employee_id', '=', employee.id)
            ])
            

            employee.documents_sent_count = self.env['document.document'].search_count([
                ('sender_employee_id', '=', employee.id),
                ('document_type', 'in', ['outgoing', 'internal'])
            ])
            

            employee.approvals_pending_count = self.env['approval.request'].search_count([
                ('approver_ids.employee_id', '=', employee.id),
                ('request_status', '=', 'pending')
            ])
            

            employee.approvals_completed_count = self.env['approval.request'].search_count([
                ('approver_ids.employee_id', '=', employee.id),
                ('request_status', 'in', ['approved', 'rejected'])
            ])
            

            if employee.user_id:
                employee.signatures_count = self.env['digital.signature'].search_count([
                    ('user_id', '=', employee.user_id.id)
                ])
            else:
                employee.signatures_count = 0
    

    def is_delegation_active(self):
        """التحقق من نشاط التفويض"""
        self.ensure_one()
        
        if not self.delegate_approvals_to:
            return False
        
        today = fields.Date.today()
        
        if self.delegation_start_date and self.delegation_start_date > today:
            return False
        
        if self.delegation_end_date and self.delegation_end_date < today:
            return False
        
        return True
    
    def get_effective_approver(self):
        """الحصول على الموافق الفعلي (مع مراعاة التفويض)"""
        self.ensure_one()
        
        if self.is_delegation_active():
            return self.delegate_approvals_to
        
        return self
    
    def can_approve_category(self, category):
        """التحقق من إمكانية اعتماد فئة معينة من الوثائق"""
        self.ensure_one()
        
        if not self.is_document_approver:
            return False
        
        if self.document_categories_ids:
            return category in self.document_categories_ids
        
        return True
    
    def get_approval_authority_documents(self):
        """الحصول على الوثائق التي يمكن للموظف اعتمادها"""
        self.ensure_one()
        
        if not self.is_document_approver:
            return self.env['document.document']
        
        domain = []
        
        if self.approval_authority_level != 'executive':
            if self.department_id:
                domain.append(('department_id', '=', self.department_id.id))
            else:
                return self.env['document.document']
        
        if self.document_categories_ids:
            domain.append(('category_id', 'in', self.document_categories_ids.ids))
        
        domain.append(('state', 'in', ['submitted', 'in_review']))
        
        return self.env['document.document'].search(domain)
    
    def get_subordinate_documents(self):
        """الحصول على وثائق المرؤوسين"""
        self.ensure_one()
        
        subordinates = self.env['hr.employee'].search([
            ('parent_id', '=', self.id)
        ])
        
        if not subordinates:
            return self.env['document.document']
        
        return self.env['document.document'].search([
            ('sender_employee_id', 'in', subordinates.ids)
        ])
    
    def create_delegation(self, delegate_to, start_date, end_date, reason):
        """إنشاء تفويض جديد"""
        self.ensure_one()
        
        if not delegate_to.is_document_approver:
            raise UserError(_('الموظف المفوض يجب أن يكون له صلاحية اعتماد الوثائق'))
        
        self.write({
            'delegate_approvals_to': delegate_to.id,
            'delegation_start_date': start_date,
            'delegation_end_date': end_date,
            'delegation_reason': reason,
        })
        
        self.env['mail.message'].create({
            'subject': _('تفويض اعتماد الوثائق'),
            'body': _('تم تفويضك لاعتماد الوثائق نيابة عن %s من %s إلى %s') % (
                self.name, start_date, end_date
            ),
            'model': 'hr.employee',
            'res_id': delegate_to.id,
            'message_type': 'notification',
        })
    
    def cancel_delegation(self):
        """إلغاء التفويض"""
        self.ensure_one()
        
        if self.delegate_approvals_to:
            self.env['mail.message'].create({
                'subject': _('إلغاء تفويض اعتماد الوثائق'),
                'body': _('تم إلغاء تفويضك لاعتماد الوثائق نيابة عن %s') % self.name,
                'model': 'hr.employee',
                'res_id': self.delegate_approvals_to.id,
                'message_type': 'notification',
            })
        
        self.write({
            'delegate_approvals_to': False,
            'delegation_start_date': False,
            'delegation_end_date': False,
            'delegation_reason': False,
        })
    
    def action_view_my_documents(self):
        """عرض وثائق الموظف"""
        self.ensure_one()
        
        return {
            'name': _('وثائقي'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [
                '|', '|',
                ('sender_employee_id', '=', self.id),
                ('recipient_employee_id', '=', self.id),
                ('create_uid', '=', self.user_id.id if self.user_id else 0)
            ],
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
                ('approver_ids.employee_id', '=', self.id),
                ('request_status', 'in', ['new', 'pending', 'under_approval'])
            ],
        }
    
    def action_view_subordinate_documents(self):
        """عرض وثائق المرؤوسين"""
        self.ensure_one()
        
        subordinate_docs = self.get_subordinate_documents()
        
        return {
            'name': _('وثائق المرؤوسين'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': [('id', 'in', subordinate_docs.ids)],
        }
    
    def action_create_delegation(self):
        """إنشاء تفويض جديد"""
        self.ensure_one()
        
        return {
            'name': _('إنشاء تفويض'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.delegation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delegator_id': self.id,
            }
        }
    
    def action_view_my_signatures(self):
        """عرض توقيعات الموظف"""
        self.ensure_one()
        
        if not self.user_id:
            raise UserError(_('الموظف لا يملك حساب مستخدم'))
        
        return {
            'name': _('توقيعاتي'),
            'type': 'ir.actions.act_window',
            'res_model': 'digital.signature',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.user_id.id)],
        }

    @api.constrains('delegate_approvals_to')
    def _check_delegation_loop(self):
        """التحقق من عدم وجود حلقة في التفويض"""
        for employee in self:
            if employee.delegate_approvals_to:
        
                if employee.delegate_approvals_to.delegate_approvals_to == employee:
                    raise ValidationError(_('لا يمكن إنشاء حلقة في التفويض'))
    
    @api.constrains('delegation_start_date', 'delegation_end_date')
    def _check_delegation_dates(self):
        """التحقق من صحة تواريخ التفويض"""
        for employee in self:
            if employee.delegation_start_date and employee.delegation_end_date:
                if employee.delegation_start_date > employee.delegation_end_date:
                    raise ValidationError(_('تاريخ بداية التفويض لا يمكن أن يكون بعد تاريخ النهاية')) 
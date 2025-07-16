# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class DocumentApprovalRequest(models.Model):
    """نموذج طلبات الموافقة للوثائق"""
    
    _name = 'document.approval.request'
    _description = 'طلبات موافقة الوثائق'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    _rec_name = 'display_name'
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    approver_id = fields.Many2one(
        'hr.employee',
        string='الموافق',
        required=True,
        tracking=True
    )
    
    requester_id = fields.Many2one(
        'hr.employee',
        string='طالب الموافقة',
        default=lambda self: self.env.user.employee_id,
        required=True,
        tracking=True
    )
    
    request_date = fields.Datetime(
        string='تاريخ الطلب',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    due_date = fields.Datetime(
        string='تاريخ الاستحقاق',
        tracking=True,
        help='التاريخ المتوقع للرد على طلب الموافقة'
    )
    
    status = fields.Selection([
        ('pending', 'في الانتظار'),
        ('approved', 'موافق عليه'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغي'),
        ('expired', 'منتهي الصلاحية')
    ], string='الحالة', default='pending', tracking=True, copy=False)
    
    priority = fields.Selection([
        ('0', 'عادي'),
        ('1', 'مهم'),
        ('2', 'عاجل'),
        ('3', 'عاجل جداً')
    ], string='الأولوية', default='0', tracking=True)
    
    response_date = fields.Datetime(
        string='تاريخ الرد',
        readonly=True,
        copy=False
    )
    
    response_notes = fields.Text(
        string='ملاحظات الرد',
        tracking=True
    )
    
    rejection_reason = fields.Text(
        string='سبب الرفض',
        tracking=True
    )
    
    request_subject = fields.Char(
        string='موضوع الطلب',
        required=True,
        tracking=True
    )
    
    request_description = fields.Text(
        string='وصف الطلب',
        tracking=True
    )
    
    approval_type = fields.Selection([
        ('content', 'موافقة على المحتوى'),
        ('publication', 'موافقة على النشر'),
        ('archiving', 'موافقة على الأرشفة'),
        ('deletion', 'موافقة على الحذف'),
        ('access', 'موافقة على الوصول'),
        ('signature', 'موافقة على التوقيع'),
        ('other', 'أخرى')
    ], string='نوع الموافقة', default='content', tracking=True)
    
    delegate_id = fields.Many2one(
        'hr.employee',
        string='المفوض',
        help='الموظف المفوض للموافقة نيابة عن الموافق الأصلي'
    )
    
    delegation_reason = fields.Text(
        string='سبب التفويض'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        required=True
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
    
    document_reference = fields.Char(
        string='رقم الوثيقة المرجعي',
        related='document_id.reference_number',
        store=True
    )
    
    approver_name = fields.Char(
        string='اسم الموافق',
        related='approver_id.name',
        store=True
    )
    
    requester_name = fields.Char(
        string='اسم طالب الموافقة',
        related='requester_id.name',
        store=True
    )
    
    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_is_overdue'
    )
    
    days_pending = fields.Integer(
        string='أيام الانتظار',
        compute='_compute_days_pending'
    )
    
    can_approve = fields.Boolean(
        string='يمكن الموافقة',
        compute='_compute_can_approve'
    )
    
    is_delegated = fields.Boolean(
        string='مفوض',
        compute='_compute_is_delegated',
        help='يشير إلى ما إذا كان هذا الطلب مفوض لموظف آخر'
    )
    
    @api.depends('request_subject', 'document_id.name', 'status')
    def _compute_display_name(self):
        """حساب الاسم المعروض للطلب"""
        for record in self:
            status_name = dict(record._fields['status'].selection).get(record.status, record.status)
            record.display_name = f"{record.request_subject} - {status_name}"
    
    @api.depends('due_date', 'status')
    def _compute_is_overdue(self):
        """تحديد ما إذا كان الطلب متأخراً"""
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = (
                record.status == 'pending' and 
                record.due_date and 
                record.due_date < now
            )
    
    @api.depends('request_date', 'status')
    def _compute_days_pending(self):
        """حساب عدد أيام الانتظار"""
        now = fields.Datetime.now()
        for record in self:
            if record.status == 'pending' and record.request_date:
                delta = now - record.request_date
                record.days_pending = delta.days
            else:
                record.days_pending = 0
    
    @api.depends('approver_id', 'delegate_id')
    def _compute_can_approve(self):
        """تحديد ما إذا كان المستخدم الحالي يمكنه الموافقة"""
        current_employee = self.env.user.employee_id
        for record in self:
            record.can_approve = (
                current_employee and (
                    current_employee == record.approver_id or
                    current_employee == record.delegate_id
                )
            )
    
    @api.depends('delegate_id')
    def _compute_is_delegated(self):
        """تحديد ما إذا كان الطلب مفوض"""
        for record in self:
            record.is_delegated = bool(record.delegate_id)
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء طلب موافقة جديد"""
        for vals in vals_list:
            if not vals.get('due_date') and vals.get('request_date'):
                request_date = fields.Datetime.to_datetime(vals['request_date'])
                vals['due_date'] = request_date + timedelta(days=3)
            
            if not vals.get('request_subject') and vals.get('document_id'):
                document = self.env['document.document'].browse(vals['document_id'])
                vals['request_subject'] = f"طلب موافقة على: {document.name}"
        
        requests = super().create(vals_list)
        
        for request in requests:
            request._create_approval_activity()
        
        return requests
    
    def write(self, vals):
        """تحديث طلب الموافقة"""
        result = super().write(vals)
        
        if 'status' in vals:
            for record in self:
                record._update_document_state()
        
        return result
    
    def action_approve(self):
        """الموافقة على الطلب"""
        for record in self:
            if record.status != 'pending':
                raise UserError(_('يمكن الموافقة على الطلبات المعلقة فقط'))
            
            if not record.can_approve:
                raise UserError(_('ليس لديك صلاحية الموافقة على هذا الطلب'))
            
            record.write({
                'status': 'approved',
                'response_date': fields.Datetime.now()
            })
            
            if record.document_id:
                record.document_id.action_approve()
            
            record._create_history_record('approved', _('تم اعتماد الطلب'))
            
            record._send_approval_notification('approved')
    
    def action_reject(self):
        """رفض الطلب"""
        for record in self:
            if record.status != 'pending':
                raise UserError(_('يمكن رفض الطلبات المعلقة فقط'))
            
            if not record.can_approve:
                raise UserError(_('ليس لديك صلاحية رفض هذا الطلب'))
            
            record.write({
                'status': 'rejected',
                'response_date': fields.Datetime.now()
            })
            
            if record.document_id:
                record.document_id.action_reject()
            
            record._create_history_record('rejected', _('تم رفض الطلب'))
            

            record._send_approval_notification('rejected')
    
    def action_cancel(self):
        """إلغاء الطلب"""
        for record in self:
            if record.status not in ('pending', 'expired'):
                raise UserError(_('يمكن إلغاء الطلبات المعلقة أو منتهية الصلاحية فقط'))
            
            record.write({
                'status': 'cancelled',
                'response_date': fields.Datetime.now()
            })
            
            record._create_history_record('cancelled', _('تم إلغاء الطلب'))
    
    def action_delegate(self):
        """تفويض الموافقة"""
        return {
            'name': _('تفويض الموافقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.delegation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_request_id': self.id,
                'default_approver_id': self.approver_id.id,
            }
        }
    
    def action_reset(self):
        """إعادة تعيين الطلب إلى الحالة المعلقة"""
        for record in self:
            if record.status not in ('rejected', 'cancelled', 'expired'):
                raise UserError(_('يمكن إعادة تعيين الطلبات المرفوضة أو الملغية أو منتهية الصلاحية فقط'))
            
            record.write({
                'status': 'pending',
                'response_date': False,
                'response_notes': False,
                'rejection_reason': False,
            })
            
            record._create_history_record('reset', _('تم إعادة تعيين الطلب إلى الانتظار'))
            
            record._create_approval_activity()
    
    def action_remind(self):
        """تذكير الموافق"""
        for record in self:
            if record.status != 'pending':
                raise UserError(_('يمكن إرسال تذكير للطلبات المعلقة فقط'))
            
            record._send_reminder_notification()
    
    def _create_approval_activity(self):
        """إنشاء نشاط للموافق"""
        self.ensure_one()
        
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if activity_type:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                summary=f"طلب موافقة: {self.request_subject}",
                note=self.request_description or '',
                user_id=self.approver_id.user_id.id,
                date_deadline=self.due_date.date() if self.due_date else fields.Date.today()
            )
    
    def _update_document_state(self):
        """تحديث حالة الوثيقة بناءً على حالة الموافقة"""
        self.ensure_one()
        
        if not self.document_id:
            return
        
        if self.status == 'approved':
            pending_requests = self.search([
                ('document_id', '=', self.document_id.id),
                ('status', '=', 'pending')
            ])
            
            if not pending_requests:
                if self.document_id.state == 'in_review':
                    self.document_id.write({'state': 'approved'})
        
        elif self.status == 'rejected':
            if self.document_id.state in ('submitted', 'in_review'):
                self.document_id.write({'state': 'rejected'})
    
    def _create_history_record(self, action, description):
        """إنشاء سجل في تاريخ الوثيقة"""
        if self.document_id:
            self.env['document.history'].create({
                'document_id': self.document_id.id,
                'user_id': self.env.user.id,
                'action': action,
                'description': description,
                'approval_request_id': self.id,
            })
    
    def _send_approval_notification(self, action):
        """إرسال إشعار بنتيجة الموافقة"""
        template_name = f'mgt_documents.email_template_approval_{action}'
        template = self.env.ref(template_name, raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)
    
    def _send_reminder_notification(self):
        """إرسال تذكير للموافق"""
        template = self.env.ref('mgt_documents.email_template_approval_reminder', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)
    
    @api.model
    def _check_expired_requests(self):
        """التحقق من الطلبات منتهية الصلاحية"""
        now = fields.Datetime.now()
        expired_requests = self.search([
            ('status', '=', 'pending'),
            ('due_date', '<', now)
        ])
        
        expired_requests.write({'status': 'expired'})
        
        for request in expired_requests:
            request._send_expiry_notification()
    
    def _send_expiry_notification(self):
        """إرسال إشعار انتهاء صلاحية الطلب"""
        template = self.env.ref('mgt_documents.email_template_approval_expired', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)
    
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
    
    @api.constrains('due_date', 'request_date')
    def _check_due_date(self):
        """التحقق من صحة تاريخ الاستحقاق"""
        for record in self:
            if record.due_date and record.request_date and record.due_date < record.request_date:
                raise ValidationError(_('تاريخ الاستحقاق لا يمكن أن يكون قبل تاريخ الطلب'))
    
    @api.constrains('approver_id', 'requester_id')
    def _check_approver_requester(self):
        """التحقق من أن الموافق ليس هو نفسه طالب الموافقة"""
        for record in self:
            if record.approver_id and record.requester_id and record.approver_id == record.requester_id:
                raise ValidationError(_('لا يمكن أن يكون الموافق هو نفسه طالب الموافقة')) 
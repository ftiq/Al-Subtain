# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class ApprovalTaskAssignmentWizard(models.TransientModel):    
    _name = 'approval.task.assignment.wizard'
    _description = 'معالج تعيين المهام بعد الموافقة'
    
    approver_id = fields.Many2one(
        'approval.approver',
        string='الموافق',
        required=True,
        readonly=True
    )
    
    request_id = fields.Many2one(
        'approval.request',
        string='طلب الموافقة',
        required=True,
        readonly=True
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة المرتبطة',
        readonly=True
    )
    
    official_directive = fields.Text(
        string='بيان الأمر الرسمي / الهامش',
        required=True,
        help='نص الأمر أو التوجيه الذي سيتم تنفيذه بناءً على هذه الموافقة'
    )
    
    assignment_type = fields.Selection([
        ('department', 'تعيين لقسم'),
        ('employee', 'تعيين لموظف محدد'),
        ('both', 'تعيين لقسم وموظف محدد'),
        ('none', 'عدم تعيين مهمة (موافقة فقط)')
    ], string='نوع التعيين', default='department', required=True)
    
    assigned_department_id = fields.Many2one(
        'hr.department',
        string='القسم المُكلف',
        help='القسم الذي سيتم تكليفه بتنفيذ هذا الأمر'
    )
    
    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المُكلف',
        help='الموظف المحدد الذي سيتم تكليفه'
    )
    
    task_title = fields.Char(
        string='عنوان المهمة',
        required=True,
        help='عنوان واضح للمهمة المطلوب تنفيذها'
    )
    
    task_description = fields.Text(
        string='وصف تفصيلي للمهمة',
        help='وصف مفصل للمهمة والخطوات المطلوب تنفيذها'
    )
    
    task_type = fields.Selection([
        ('execute_directive', 'تنفيذ أمر إداري'),
        ('prepare_response', 'إعداد رد'),
        ('coordinate_departments', 'تنسيق بين الأقسام'),
        ('follow_up', 'متابعة تنفيذ'),
        ('archive_process', 'عملية أرشفة'),
        ('legal_procedure', 'إجراء قانوني'),
        ('financial_procedure', 'إجراء مالي'),
        ('administrative_procedure', 'إجراء إداري'),
        ('other', 'أخرى')
    ], string='نوع المهمة', default='execute_directive', required=True)
    
    priority = fields.Selection([
        ('0', 'منخفضة'),
        ('1', 'عادية'),
        ('2', 'مرتفعة'),
        ('3', 'عاجلة')
    ], string='الأولوية', default='1', required=True)
    
    due_date = fields.Datetime(
        string='تاريخ الاستحقاق',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=7)
    )
    
    approver_notes = fields.Text(
        string='ملاحظات الموافق',
        help='ملاحظات إضافية من الموافق'
    )
    
    send_notification = fields.Boolean(
        string='إرسال إشعار',
        default=True,
        help='إرسال إشعار للمُكلف بالمهمة'
    )
    
    notification_message = fields.Text(
        string='رسالة الإشعار',
        default='تم تكليفكم بمهمة جديدة بناءً على موافقة إدارية.'
    )
    
    @api.onchange('assignment_type')
    def _onchange_assignment_type(self):
        """تحديث الحقول المطلوبة حسب نوع التعيين"""
        if self.assignment_type == 'department':
            self.assigned_employee_id = False
        elif self.assignment_type == 'employee':
            self.assigned_department_id = False
        elif self.assignment_type == 'none':
            self.assigned_department_id = False
            self.assigned_employee_id = False
    
    @api.onchange('assigned_employee_id')
    def _onchange_assigned_employee(self):
        """تحديث القسم تلقائياً عند اختيار موظف"""
        if self.assigned_employee_id and self.assignment_type in ['employee', 'both']:
            self.assigned_department_id = self.assigned_employee_id.department_id
    
    @api.onchange('document_id', 'request_id')
    def _onchange_document_or_request(self):
        """تحديث تلقائي لبيانات المهمة"""
        if self.document_id:
            self.task_title = f"تنفيذ أمر بخصوص: {self.document_id.name}"
            
            if self.document_id.department_id:
                self.assigned_department_id = self.document_id.department_id
            
            doc_type_mapping = {
                'incoming': 'prepare_response',
                'outgoing': 'follow_up',
                'internal': 'execute_directive',
                'contract': 'legal_procedure',
                'invoice': 'financial_procedure',
                'report': 'administrative_procedure'
            }
            if self.document_id.document_type in doc_type_mapping:
                self.task_type = doc_type_mapping[self.document_id.document_type]
    
    @api.constrains('assignment_type', 'assigned_department_id', 'assigned_employee_id')
    def _check_assignment_consistency(self):
        """التحقق من تناسق بيانات التعيين"""
        for record in self:
            if record.assignment_type == 'department' and not record.assigned_department_id:
                raise ValidationError(_('يجب تحديد القسم عند اختيار "تعيين لقسم"'))
            elif record.assignment_type == 'employee' and not record.assigned_employee_id:
                raise ValidationError(_('يجب تحديد الموظف عند اختيار "تعيين لموظف محدد"'))
            elif record.assignment_type == 'both' and (not record.assigned_department_id or not record.assigned_employee_id):
                raise ValidationError(_('يجب تحديد القسم والموظف عند اختيار "تعيين لقسم وموظف محدد"'))
    
    def action_approve_and_assign(self):
        """تنفيذ الموافقة وتعيين المهمة"""
        self.ensure_one()
        
        self.approver_id.action_approve_final()
        self.approver_id.write({
            'comment': self.official_directive + 
                      (f"\n\nملاحظات الموافق: {self.approver_notes}" if self.approver_notes else "")
        })
        
        if self.assignment_type != 'none':
            task_vals = self._prepare_task_values()
            task = self.env['admin.task'].create(task_vals)
            
            self.request_id.write({
                'related_task_ids': [(4, task.id)]
            })
            
            if self.send_notification:
                self._send_assignment_notification(task)
            
            if self.document_id:
                body_html = (
                    f"<p><strong>تم إنشاء مهمة بناءً على موافقة:</strong></p>"
                    f"<ul>"
                    f"<li><strong>بيان الأمر:</strong> {self.official_directive}</li>"
                    f"<li><strong>عنوان المهمة:</strong> {self.task_title}</li>"
                    f"<li><strong>المُكلف:</strong> {self._get_assigned_description()}</li>"
                    f"<li><strong>تاريخ الاستحقاق:</strong> {self.due_date}</li>"
                    f"</ul>"
                )
                self.document_id.message_post(
                    body=body_html,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment'
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تمت الموافقة بنجاح'),
                'message': _('تم تنفيذ الموافقة وتعيين المهمة بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _prepare_task_values(self):
        description = self.task_description or ''
        if self.official_directive:
            description = (description + '\n\n' if description else '') + f"بيان الأمر: {self.official_directive}"
        if self.approver_notes:
            description = (description + '\n\n' if description else '') + f"ملاحظات الموافق: {self.approver_notes}"
        # خرائط لأنواع المهام بين المعالج ونموذج admin.task
        type_map = {
            'execute_directive': 'execute_action',
            'prepare_response': 'prepare_response',
            'coordinate_departments': 'other',
            'follow_up': 'follow_up',
            'archive_process': 'other',
            'legal_procedure': 'other',
            'financial_procedure': 'other',
            'administrative_procedure': 'other',
            'other': 'other',
        }
        mapped_task_type = type_map.get(self.task_type, 'other')
        # ملاحظة: حقول سير العمل تم تعطيلها
        # process_id, process_instance_id, workflow_step_id تم تعليقها في admin.task

        return {
            'name': self.task_title,
            'description': description,
            'task_type': mapped_task_type,
            'assigned_department_id': self.assigned_department_id.id if self.assigned_department_id else False,
            'assigned_employee_id': self.assigned_employee_id.id if self.assigned_employee_id else False,
            'priority': self.priority,
            'due_date': self.due_date,
            'request_document_id': self.document_id.id if self.document_id else False,
            # 'process_id': False,  # معطل - سير العمل تم إزالته
            # 'process_instance_id': False,  # معطل - سير العمل تم إزالته
            # 'workflow_step_id': False,  # معطل - سير العمل تم إزالته
            'approval_request_id': self.request_id.id,
            'state': 'assigned'
        }
    
    def _get_assigned_description(self):
        """وصف المُكلف"""
        if self.assignment_type == 'department':
            return self.assigned_department_id.name
        elif self.assignment_type == 'employee':
            return self.assigned_employee_id.name
        elif self.assignment_type == 'both':
            return f"{self.assigned_employee_id.name} ({self.assigned_department_id.name})"
        else:
            return "غير محدد"
    
    def _send_assignment_notification(self, task):
        """إرسال إشعار بالتكليف"""
        if self.assigned_employee_id and self.assigned_employee_id.user_id:
            task.message_post(
                body=self.notification_message,
                partner_ids=[self.assigned_employee_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
        
        if self.assigned_department_id and self.assigned_department_id.manager_id and self.assigned_department_id.manager_id.user_id:
            task.message_post(
                body=f"تم تكليف قسمكم بمهمة جديدة: {self.task_title}",
                partner_ids=[self.assigned_department_id.manager_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
    
    def action_approve_without_task(self):
        """موافقة بدون تعيين مهمة"""
        self.ensure_one()
        
        self.approver_id.action_approve_final()
        
        self.approver_id.write({
            'comment': self.official_directive + 
                      (f"\n\nملاحظات الموافق: {self.approver_notes}" if self.approver_notes else "")
        })
        
        if self.document_id:
            self.document_id.message_post(
                body=f"""
                <p><strong>تمت الموافقة مع بيان الأمر:</strong></p>
                <p>{self.official_directive}</p>
                {f"<p><strong>ملاحظات:</strong> {self.approver_notes}</p>" if self.approver_notes else ""}
                """,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تمت الموافقة'),
                'message': _('تم تسجيل الموافقة وبيان الأمر بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }

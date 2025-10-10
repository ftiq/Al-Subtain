# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class AdministrativeTask(models.Model):
    """نموذج المهام الإدارية"""
    
    _name = 'admin.task'
    _description = 'المهام الإدارية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, due_date asc, id desc'
    _rec_name = 'name'
    

    request_document_id = fields.Many2one(
        'document.document', 
        string='الوثيقة المرتبطة',
        tracking=True,
        help='الوثيقة التي نشأت عنها هذه المهمة'
    )
    
    process_id = fields.Many2one(
        'workflow.process', 
        string='العملية المرتبطة',
        help='العملية أو سير العمل المرتبط بهذه المهمة'
    )
    
    process_instance_id = fields.Many2one(
        'document.workflow.instance',
        string='نسخة العملية',
        help='نسخة العملية الجارية المرتبطة بهذه المهمة'
    )
    
    workflow_step_id = fields.Many2one(
        'workflow.step',
        string='خطوة سير العمل',
        help='الخطوة التي أنشأت هذه المهمة'
    )
    

    name = fields.Char(
        string='عنوان المهمة',
        required=True,
        tracking=True
    )
    
    description = fields.Html(
        string='وصف المهمة',
        help='وصف تفصيلي للمهمة والمطلوب تنفيذه'
    )
    
    task_type = fields.Selection([
        ('review_document', 'مراجعة وثيقة'),
        ('approve_request', 'موافقة على طلب'),
        ('execute_action', 'تنفيذ إجراء'),
        ('prepare_response', 'إعداد رد'),
        ('forward_document', 'تحويل وثيقة'),
        ('data_entry', 'إدخال بيانات'),
        ('verification', 'تحقق من معلومات'),
        ('follow_up', 'متابعة'),
        ('other', 'أخرى')
    ], string='نوع المهمة', default='review_document', tracking=True)
    

    priority = fields.Selection([
        ('0', 'عادي'),
        ('1', 'متوسط'),
        ('2', 'عالي'),
        ('3', 'عاجل'),
        ('4', 'حرج')
    ], string='الأولوية', default='1', tracking=True)
    
    progress_percentage = fields.Float(
        string='نسبة التقدم (%)',
        default=0.0,
    )
    

    assigned_department_id = fields.Many2one(
        'hr.department',
        string='القسم المُكلف',
        tracking=True
    )
    
    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المُكلف',
        tracking=True,
        domain="[('department_id', '=', assigned_department_id), ('active', '=', True)]"
    )
    
    assigned_by = fields.Many2one(
        'hr.employee',
        string='كُلف بواسطة',
        default=lambda self: self.env.user.employee_id,
        tracking=True
    )
    
    assigned_date = fields.Datetime(
        string='تاريخ التكليف',
        default=fields.Datetime.now,
        tracking=True
    )
    
    due_date = fields.Datetime(
        string='تاريخ الاستحقاق',
        tracking=True,
        help='الموعد النهائي المتوقع لإنجاز المهمة'
    )
    

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('assigned', 'مُكلف'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('on_hold', 'معلق')
    ], string='الحالة', default='draft', tracking=True)
    

    approval_request_id = fields.Many2one(
        'approval.request',
        string='طلب الموافقة المرتبط',
        help='طلب الموافقة الذي أدى لإنشاء هذه المهمة'
    )
    
    execution_notes = fields.Html(
        string='ملاحظات التنفيذ',
        help='ملاحظات حول كيفية تنفيذ المهمة'
    )
    
    completion_date = fields.Datetime(
        string='تاريخ الإنجاز',
        readonly=True
    )
    
    result_summary = fields.Text(
        string='ملخص النتيجة',
        help='ملخص موجز لنتيجة تنفيذ المهمة'
    )
    
    parent_task_id = fields.Many2one(
        'admin.task',
        string='المهمة الرئيسية',
        help='المهمة الرئيسية إذا كانت هذه مهمة فرعية'
    )
    
    subtask_ids = fields.One2many(
        'admin.task',
        'parent_task_id',
        string='المهام الفرعية'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )
    
    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_overdue_status',
        store=True
    )
    
    @api.depends('due_date', 'state')
    def _compute_overdue_status(self):
        now = fields.Datetime.now()
        for task in self:
            task.is_overdue = (
                task.due_date and 
                task.due_date < now and 
                task.state not in ['completed', 'cancelled']
            )
    

    def action_assign(self):
        """تكليف المهمة"""
        self.write({'state': 'assigned'})
    
    def action_start(self):
        """بدء تنفيذ المهمة"""
        self.write({'state': 'in_progress'})
    
    def action_complete(self):
        """إكمال المهمة"""
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
        self._maybe_progress_instance()
    
    def action_cancel(self):
        """إلغاء المهمة"""
        self.write({'state': 'cancelled'})
        self._maybe_progress_instance()
    
    def action_hold(self):
        """تعليق المهمة"""
        self.write({'state': 'on_hold'})
    
    def action_resume(self):
        """استئناف المهمة"""
        self.write({'state': 'assigned'})
        # لا تقدم تلقائي هنا

    def _maybe_progress_instance(self):
        """عند اكتمال/إلغاء جميع مهام الخطوة الحالية، تقدم إلى الخطوة التالية"""
        for task in self:
            inst = task.process_instance_id
            if not inst or not inst.current_step_id:
                continue
            # اعتبر فقط مهام نفس نسخة العملية ونفس الخطوة
            step_id = inst.current_step_id.id
            step_tasks = inst.admin_task_ids.filtered(lambda t: t.workflow_step_id and t.workflow_step_id.id == step_id)
            if not step_tasks:
                continue
            if all(t.state in ['completed', 'cancelled'] for t in step_tasks):
                try:
                    inst.action_next_step()
                except Exception:
                    pass
    
    @api.constrains('parent_task_id')
    def _check_recursion(self):
        """منع التكرار الدائري في المهام"""
        for task in self:
            if task.parent_task_id:
                current = task.parent_task_id
                visited = set()
                while current:
                    if current.id in visited:
                        raise ValidationError(_('لا يمكن إنشاء مهام متداخلة بشكل دائري'))
                    visited.add(current.id)
                    current = current.parent_task_id
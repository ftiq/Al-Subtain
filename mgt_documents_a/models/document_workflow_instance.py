# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class DocumentWorkflowInstance(models.Model):
    """نموذج نسخة تنفيذ العملية"""
    
    _name = 'document.workflow.instance'
    _description = 'نسخة تنفيذ العملية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'
    
    name = fields.Char(
        string='اسم النسخة',
        required=True,
        tracking=True
    )
    
    workflow_process_id = fields.Many2one(
        'workflow.process',
        string='عملية سير العمل',
        required=True,
        tracking=True
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة المرتبطة',
        tracking=True
    )
    
    state = fields.Selection([
        ('initiated', 'مبدوء'),
        ('running', 'قيد التنفيذ'),
        ('waiting', 'في الانتظار'),
        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ('failed', 'فشل')
    ], string='الحالة', default='initiated', tracking=True, required=True)
    
    start_date = fields.Datetime(
        string='تاريخ البداية',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    completion_date = fields.Datetime(
        string='تاريخ الإنجاز',
        tracking=True
    )
    
    due_date = fields.Datetime(
        string='تاريخ الاستحقاق',
        compute='_compute_due_date',
        store=True,
        help='التاريخ المتوقع لإنجاز العملية'
    )
    
    current_step_id = fields.Many2one(
        'workflow.step',
        string='الخطوة الحالية',
        tracking=True
    )
    
    current_step_name = fields.Char(
        string='اسم الخطوة الحالية',
        related='current_step_id.name',
        store=True
    )
    
    admin_task_ids = fields.One2many(
        'admin.task',
        'process_instance_id',
        string='المهام الإدارية',
        help='المهام المنشأة من هذه العملية'
    )
    
    active_tasks_count = fields.Integer(
        string='عدد المهام النشطة',
        compute='_compute_tasks_count',
        store=True
    )
    
    priority = fields.Selection([
        ('0', 'منخفض'),
        ('1', 'عادي'),
        ('2', 'مهم'),
        ('3', 'عاجل'),
        ('4', 'حرج')
    ], string='الأولوية', default='1', tracking=True)
    
    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_overdue_status',
        store=True
    )
    
    trigger_data = fields.Text(
        string='بيانات التفعيل',
        help='البيانات التي أدت لتفعيل العملية',
        default='{}'
    )
    
    result_summary = fields.Text(
        string='ملخص النتيجة',
        help='ملخص موجز لنتيجة تنفيذ العملية'
    )
    
    @api.depends('workflow_process_id.expected_duration', 'start_date')
    def _compute_due_date(self):
        for instance in self:
            if instance.start_date and instance.workflow_process_id.expected_duration:
                instance.due_date = instance.start_date + timedelta(
                    hours=instance.workflow_process_id.expected_duration
                )
            else:
                instance.due_date = False
    
    @api.depends('admin_task_ids.state')
    def _compute_tasks_count(self):
        for instance in self:
            active_tasks = instance.admin_task_ids.filtered(
                lambda t: t.state not in ['completed', 'cancelled']
            )
            instance.active_tasks_count = len(active_tasks)
    
    @api.depends('due_date', 'state')
    def _compute_overdue_status(self):
        now = fields.Datetime.now()
        for instance in self:
            instance.is_overdue = (
                instance.due_date
                and instance.due_date < now
                and instance.state not in ['completed', 'cancelled']
            )
    def action_start(self):
        """بدء تنفيذ العملية"""
        self.write({'state': 'running', 'start_date': fields.Datetime.now()})
    
    def action_complete(self):
        """إكمال العملية"""
        self.write({
            'state': 'completed',
            'completion_date': fields.Datetime.now()
        })
    
    def action_cancel(self):
        """إلغاء العملية"""
        self.write({'state': 'cancelled'})
    
    def action_view_tasks(self):
        """عرض المهام المرتبطة بهذه النسخة من سير العمل"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'admin.task',
            'view_mode': 'kanban,list,form',
            'domain': [('process_instance_id', '=', self.id)],
            'context': {'default_process_instance_id': self.id},
            'target': 'current',
        }

    @api.model
    def check_overdue_instances(self):
        """Cron: Mark/log overdue instances. Keeps method present to prevent cron errors."""
        try:
            overdue = self.search([('is_overdue', '=', True)])
            count = len(overdue)
            if count:
                _logger.info("[WORKFLOW][cron] Overdue instances: %s", count)
            return True
        except Exception as e:
            _logger.warning("[WORKFLOW][cron] check_overdue_instances error: %s", str(e))
            return False

    @api.model
    def cleanup_test_instances(self):
        """Cron: Cleanup old test instances. Keeps method present to prevent cron errors."""
        try:
            threshold = fields.Datetime.now() - timedelta(days=30)
            domain = ['|', ('name', 'ilike', 'اختبار'), ('state', 'in', ['cancelled', 'failed'])]
            old = self.search(domain)
            to_delete = old.filtered(lambda r: (r.create_date or threshold) < threshold)
            if to_delete:
                _logger.info("[WORKFLOW][cron] Cleanup test instances: %s", len(to_delete))
                to_delete.unlink()
            return True
        except Exception as e:
            _logger.warning("[WORKFLOW][cron] cleanup_test_instances error: %s", str(e))
            return False

    def _spawn_tasks_for_step(self, step):
        """Tight integration: generate admin.task for a given workflow step.

        - Links tasks to both process instance and source document.
        - Assigns employee/department based on step responsibility.
        - Sets task type based on step type.
        """
        self.ensure_one()
        if not step:
            return
        actionable_map = {
            'review': 'review_document',
            'approval': 'approve_request',
            'data_entry': 'data_entry',
            'manual': 'execute_action',
            'notification': 'follow_up',
            'wait': 'follow_up',
            'condition': 'verification',
        }
        task_type = actionable_map.get(step.step_type)
        if not task_type:
            return

        assigned_employee = False
        assigned_department = False
        if step.responsible_type == 'specific_user' and step.responsible_user_id:
            assigned_employee = step.responsible_user_id
            assigned_department = assigned_employee.department_id
        elif step.responsible_type == 'department' and step.responsible_department_id:
            assigned_department = step.responsible_department_id
        elif step.responsible_type == 'role' and step.responsible_role:
            domain = [('active', '=', True)]
            if self.document_id and hasattr(self.document_id, 'department_id') and self.document_id.department_id:
                domain.append(('department_id', '=', self.document_id.department_id.id))
            domain.append(('job_id.name', 'ilike', step.responsible_role))
            emp = self.env['hr.employee'].search(domain, limit=1)
            if emp:
                assigned_employee = emp
                assigned_department = emp.department_id

        # Compute due_date
        due = False
        now = fields.Datetime.now()
        if getattr(step, 'deadline_hours', False):
            try:
                due = now + timedelta(hours=step.deadline_hours or 0)
            except Exception:
                due = False
        if not due and self.due_date:
            due = self.due_date
        if not due and self.document_id and getattr(self.document_id, 'target_completion_date', False):
            due = self.document_id.target_completion_date

        name = f"{step.name} - {self.document_id.name if self.document_id else self.name}"
        description = step.description or ''

        vals = {
            'name': name,
            'description': description,
            'task_type': task_type,
            'process_id': self.workflow_process_id.id,
            'process_instance_id': self.id,
            'request_document_id': self.document_id.id if self.document_id else False,
            'workflow_step_id': step.id,
            'due_date': due,
            'state': 'assigned' if (assigned_employee or assigned_department) else 'draft',
        }
        if assigned_employee:
            vals['assigned_employee_id'] = assigned_employee.id
        if assigned_department:
            vals['assigned_department_id'] = assigned_department.id

        self.env['admin.task'].create(vals)

    def action_next_step(self):
        """Advance to the next step (first by sequence). If no next step, complete the instance."""
        for rec in self:
            # Ensure instance is running
            if rec.state in ['initiated', 'waiting']:
                rec.action_start()

            # If no current step, set to first step of process
            if not rec.current_step_id:
                first = self.env['workflow.step'].search([
                    ('process_id', '=', rec.workflow_process_id.id),
                    ('active', '=', True)
                ], order='sequence,id', limit=1)
                if first:
                    rec.current_step_id = first.id
                    # Update document current step and spawn tasks, then continue
                    if rec.document_id:
                        try:
                            rec.document_id.write({'current_step': first.name})
                        except Exception:
                            pass
                    try:
                        rec._spawn_tasks_for_step(first)
                    except Exception:
                        pass
                    rec.message_post(body=_('تم ضبط الخطوة الأولى: %s') % (first.name or ''), message_type='notification')
                    continue
                else:
                    rec.action_complete()
                    continue

            # Move to next step, or complete
            next_steps = rec.current_step_id.next_step_ids
            if next_steps:
                next_step = next_steps.sorted(key=lambda s: (s.sequence, s.id))[0]
                rec.current_step_id = next_step.id
                rec.state = 'running'
                if rec.document_id:
                    try:
                        rec.document_id.write({'current_step': next_step.name})
                    except Exception:
                        pass
                # Create tasks for the new step
                try:
                    rec._spawn_tasks_for_step(next_step)
                except Exception:
                    pass
                rec.message_post(body=_('تم الانتقال إلى الخطوة: %s') % (next_step.name or ''), message_type='notification')
            else:
                # Fallback: advance by sequence within the same process
                fallback = self.env['workflow.step'].search([
                    ('process_id', '=', rec.workflow_process_id.id),
                    ('sequence', '>', rec.current_step_id.sequence),
                    ('active', '=', True)
                ], order='sequence,id', limit=1)
                if fallback:
                    rec.current_step_id = fallback.id
                    rec.state = 'running'
                    if rec.document_id:
                        try:
                            rec.document_id.write({'current_step': fallback.name})
                        except Exception:
                            pass
                    # Create tasks for the fallback step
                    try:
                        rec._spawn_tasks_for_step(fallback)
                    except Exception:
                        pass
                    rec.message_post(body=_('تم الانتقال إلى الخطوة (تلقائياً): %s') % (fallback.name or ''), message_type='notification')
                else:
                    rec.action_complete()

        return {'type': 'ir.actions.client', 'tag': 'reload'}
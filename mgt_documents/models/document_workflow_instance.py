# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import uuid
import logging
from datetime import datetime, timedelta

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
        'process.step',
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
            'name': _('المهام المرتبطة'),
            'res_model': 'admin.task',
            'view_mode': 'kanban,list,form',
            'domain': [('process_instance_id', '=', self.id)],
            'context': {'default_process_instance_id': self.id},
            'target': 'current',
        }
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class ApprovalTaskAssignmentWizard(models.TransientModel):    
    _name = 'approval.task.assignment.wizard'
    _description = 'Approval task assignment wizard'
    
    approver_id = fields.Many2one(
        'approval.approver',
        string='Approver',
        required=True,
        readonly=True
    )
    
    request_id = fields.Many2one(
        'approval.request',
        string='Approval request',
        required=True,
        readonly=True
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='Related document',
        readonly=True
    )
    
    official_directive = fields.Text(
        string='Official directive / memorandum',
        required=True,
        help='Text of the directive or instruction to be executed based on this approval'
    )
    
    assignment_type = fields.Selection([
        ('department', 'Assign to department'),
        ('employee', 'Assign to specific employee'),
        ('both', 'Assign to both department and employee'),
        ('none', 'Assign to none (approval only)')
    ], string='Assignment type', default='department', required=True)
    
    assigned_department_id = fields.Many2one(
        'hr.department',
        string='Assigned department',
        help='Department to be assigned to execute this directive'
    )
    
    assigned_employee_id = fields.Many2one(
        'hr.employee',
        string='Assigned employee',
        help='Employee to be assigned to execute this directive'
    )
    
    task_title = fields.Char(
        string='Task title',
        required=True,
        help='Clear title for the task to be executed'
    )
    
    task_description = fields.Text(
        string='Task description',
        help='Detailed description of the task and the steps to be executed'
    )
    
    task_type = fields.Selection([
        ('execute_directive', 'Execute directive'),
        ('prepare_response', 'Prepare response'),
        ('coordinate_departments', 'Coordinate departments'),
        ('follow_up', 'Follow up'),
        ('archive_process', 'Archive process'),
        ('legal_procedure', 'Legal procedure'),
        ('financial_procedure', 'Financial procedure'),
        ('administrative_procedure', 'Administrative procedure'),
        ('other', 'Other')
    ], string='Task type', default='execute_directive', required=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', required=True)
    
    due_date = fields.Datetime(
        string='Due date',
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(days=7)
    )
    
    approver_notes = fields.Text(
        string='Approver notes',
        help='Additional notes from the approver'
    )
    
    send_notification = fields.Boolean(
        string='Send notification',
        default=True,
        help='Send notification to the assigned user'
    )
    
    notification_message = fields.Text(
        string='Notification message',
        default='You have been assigned a new task based on approval.'
    )
    
    @api.onchange('assignment_type')
    def _onchange_assignment_type(self):
        """Update required fields based on assignment type"""
        if self.assignment_type == 'department':
            self.assigned_employee_id = False
        elif self.assignment_type == 'employee':
            self.assigned_department_id = False
        elif self.assignment_type == 'none':
            self.assigned_department_id = False
            self.assigned_employee_id = False
    
    @api.onchange('assigned_employee_id')
    def _onchange_assigned_employee(self):
        """Update department automatically when selecting employee"""
        if self.assigned_employee_id and self.assignment_type in ['employee', 'both']:
            self.assigned_department_id = self.assigned_employee_id.department_id
    
    @api.onchange('document_id', 'request_id')
    def _onchange_document_or_request(self):
        """Update task data automatically"""
        if self.document_id:
            self.task_title = f"Execute directive related to: {self.document_id.name}"
            
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
        """Check consistency of assignment data"""
        for record in self:
            if record.assignment_type == 'department' and not record.assigned_department_id:
                raise ValidationError(_('You must select a department when choosing "Assign to department"'))
            elif record.assignment_type == 'employee' and not record.assigned_employee_id:
                raise ValidationError(_('You must select an employee when choosing "Assign to specific employee"'))
            elif record.assignment_type == 'both' and (not record.assigned_department_id or not record.assigned_employee_id):
                raise ValidationError(_('You must select both department and employee when choosing "Assign to both department and employee"'))
    
    def action_approve_and_assign(self):
        """Execute approval and assign task"""
        self.ensure_one()
        
        self.approver_id.action_approve_final()
        self.approver_id.write({
            'comment': self.official_directive + 
                      (f"\n\nApprover notes: {self.approver_notes}" if self.approver_notes else "")
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
                self.document_id.message_post(
                    body=f"""
                    <p><strong>New task created based on approval:</strong></p>
                    <ul>
                        <li><strong>Directive:</strong> {self.official_directive}</li>
                        <li><strong>Task title:</strong> {self.task_title}</li>
                        <li><strong>Assigned to:</strong> {self._get_assigned_description()}</li>
                        <li><strong>Due date:</strong> {self.due_date}</li>
                    </ul>
                    """,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note'
                )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Task assigned successfully'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _prepare_task_values(self):
        description = self.task_description or ''
        if self.official_directive:
            description = (description + '\n\n' if description else '') + f"Directive: {self.official_directive}"
        if self.approver_notes:
            description = (description + '\n\n' if description else '') + f"Approver notes: {self.approver_notes}"

        return {
            'name': self.task_title,
            'description': description,
            'task_type': self.task_type,
            'assigned_department_id': self.assigned_department_id.id if self.assigned_department_id else False,
            'assigned_employee_id': self.assigned_employee_id.id if self.assigned_employee_id else False,
            'priority': self.priority,
            'due_date': self.due_date,
            'request_document_id': self.document_id.id if self.document_id else False,
            'approval_request_id': self.request_id.id,
            'state': 'assigned'
        }
    
    def _get_assigned_description(self):
        """Description of the assigned user"""
        if self.assignment_type == 'department':
            return self.assigned_department_id.name
        elif self.assignment_type == 'employee':
            return self.assigned_employee_id.name
        elif self.assignment_type == 'both':
            return f"{self.assigned_employee_id.name} ({self.assigned_department_id.name})"
        else:
            return "Not specified"
    
    def _send_assignment_notification(self, task):
        """Send assignment notification"""
        if self.assigned_employee_id and self.assigned_employee_id.user_id:
            task.message_post(
                body=self.notification_message,
                partner_ids=[self.assigned_employee_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
        
        if self.assigned_department_id and self.assigned_department_id.manager_id and self.assigned_department_id.manager_id.user_id:
            task.message_post(
                body=f"New task assigned to your department: {self.task_title}",
                partner_ids=[self.assigned_department_id.manager_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
    
    def action_approve_without_task(self):
        """Execute approval without task assignment"""
        self.ensure_one()
        
        self.approver_id.action_approve_final()
        
        self.approver_id.write({
            'comment': self.official_directive + 
                      (f"\n\nApprover notes: {self.approver_notes}" if self.approver_notes else "")
        })
        
        if self.document_id:
            self.document_id.message_post(
                body=f"""
                <p><strong>Approval with directive:</strong></p>
                <p>{self.official_directive}</p>
                {f"<p><strong>Approver notes:</strong> {self.approver_notes}</p>" if self.approver_notes else ""}
                """,
                message_type='notification',
                subtype_xmlid='mail.mt_note'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Approval with directive and document saved successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

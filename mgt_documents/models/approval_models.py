# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = 'Approval Category'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, index=True)
    description = fields.Text(string='Description')
    approver = fields.Many2one(
        'hr.employee',
        string='Primary Approver',
        help='Default employee as primary approver for this category (for compatibility with other add-ons)'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='For compatibility with company-dependent field paths'
    )
    automated_sequence = fields.Boolean(
        string='Automated Sequence',
        default=True,
        help='Enable automatic sequence creation for the category (field for XML compatibility)'
    )
    sequence_code = fields.Char(
        string='Sequence Code',
        help='Sequence code for the category (field for XML compatibility)'
    )
    manager_approval = fields.Selection([
        ('approver', 'By Approver'),
        ('required', 'Required')
    ], string='Manager Approval', default='approver')
    approver_sequence = fields.Selection([
        ('unordered', 'Unordered'),
        ('ordered', 'Ordered')
    ], string='Approver Sequence', default='unordered')
    sequence = fields.Integer(string='Sequence', default=10)
    

    approval_type = fields.Selection([
        ('content_review', 'Content Review'),
        ('legal_review', 'Legal Review'),
        ('financial_approval', 'Financial Approval'),
        ('publication_approval', 'Publication Approval'),
        ('archiving_approval', 'Archiving Approval'),
        ('access_permission', 'Access Permission'),
        ('signature_authority', 'Signature Authority'),
        ('security_clearance', 'Security Clearance')
    ], string='Approval Type', default='content_review')


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Internal Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Subject', required=True, tracking=True)
    category_id = fields.Many2one('approval.category', string='Category', tracking=True)
    request_owner_id = fields.Many2one('res.users', string='Request Owner', default=lambda self: self.env.user, tracking=True)
    date_start = fields.Datetime(string='Date Start', default=fields.Datetime.now, tracking=True)
    reason = fields.Text(string='Reason/Details')

    document_id = fields.Many2one('document.document', string='Related Document', ondelete='cascade', index=True)

    request_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'Pending Approval'),
        ('under_approval', 'Under Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Request Status', default='pending', tracking=True)

    approver_ids = fields.One2many('approval.approver', 'request_id', string='Approvers')


    urgency_level = fields.Selection([
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('very_urgent', 'Very Urgent'),
        ('critical', 'Critical')
    ], string='Urgency Level', default='normal', tracking=True)

    confidentiality_level = fields.Selection([
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('top_secret', 'Top Secret')
    ], string='Confidentiality Level', default='internal', tracking=True)

    department_id = fields.Many2one('hr.department', string='Department', tracking=True,
                                    default=lambda self: self.env.user.employee_id.department_id.id if self.env.user.employee_id else False)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company for approval request'
    )

    approval_type_detailed = fields.Selection([
        ('content_review', 'Content Review'),
        ('legal_review', 'Legal Review'),
        ('financial_approval', 'Financial Approval'),
        ('publication_approval', 'Publication Approval'),
        ('archiving_approval', 'Archiving Approval'),
        ('access_permission', 'Access Permission'),
        ('signature_authority', 'Signature Authority'),
        ('security_clearance', 'Security Clearance')
    ], string='Approval Type Detailed', tracking=True)
    

    approval_type = fields.Selection(
        related='approval_type_detailed',
        string='Approval Type',
        store=False,
        readonly=True
    )

    expected_response_date = fields.Datetime(string='Expected Response Date')
    location = fields.Char(string='Location', help='Meeting location or processing location (for compatibility with presentations)')

    date_end = fields.Datetime(string='Date End', related='expected_response_date', store=False)
    
    
    requester_id = fields.Many2one('hr.employee', string='Requester', related='request_owner_id.employee_id', store=False)
    approver_id = fields.Many2one('hr.employee', string='First Approver', compute='_compute_first_approver', store=False)
    auto_escalation = fields.Boolean(string='Auto Escalation', default=True)
    escalation_period = fields.Integer(string='Escalation Period (Hours)', default=24)

    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue', store=True)
    days_since_request = fields.Integer(string='Days Since Request', compute='_compute_days_since_request', store=False)
    approval_chain_progress = fields.Float(string='Approval Chain Progress (%)', compute='_compute_approval_chain_progress', store=False)
    next_approver_info = fields.Char(string='Next Approver', compute='_compute_next_approver_info', store=False)

    related_documents = fields.Many2many('document.document', 'approval_document_rel', 'approval_id', 'document_id', string='Related Documents')
    related_task_ids = fields.One2many('admin.task', 'approval_request_id', string='Related Tasks')
    tasks_count = fields.Integer(string='Number of Tasks', compute='_compute_tasks_count')
    is_my_turn = fields.Boolean(string='My Turn', compute='_compute_is_my_turn')

    ai_recommended_approvers = fields.Text(string='Recommended Approvers')
    risk_assessment = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk')
    ], string='Risk Assessment', compute='_compute_risk_assessment', store=False)
    complexity_score = fields.Float(string='Complexity Score', compute='_compute_complexity_score', store=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                seq = self.env['ir.sequence'].next_by_code('approval.request') or _('ask for approval')
                vals['name'] = seq

            vals.setdefault('request_status', 'pending')
        requests = super().create(vals_list)
        return requests

    @api.depends('approver_ids')
    def _compute_first_approver(self):
        """calculate the first approver for the approval request with mail templates"""
        for rec in self:
            first_approver = rec.approver_ids.sorted('sequence')[:1]
            rec.approver_id = first_approver.employee_id if first_approver else False
    
    @api.depends('expected_response_date', 'request_status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.expected_response_date and rec.expected_response_date < now and rec.request_status in ['new', 'pending', 'under_approval'])

    @api.depends('create_date')
    def _compute_days_since_request(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.create_date:
                rec.days_since_request = (now - rec.create_date).days
            else:
                rec.days_since_request = 0

    @api.depends('approver_ids.status')
    def _compute_approval_chain_progress(self):
        for rec in self:
            total = len(rec.approver_ids)
            approved = len(rec.approver_ids.filtered(lambda a: a.status == 'approved'))
            rec.approval_chain_progress = (approved / total) * 100 if total else 0.0

    @api.depends('approver_ids.status', 'approver_ids.sequence')
    def _compute_next_approver_info(self):
        for rec in self:
            pending = rec.approver_ids.filtered(lambda a: a.status in ['new', 'pending']).sorted('sequence')
            if pending:
                rec.next_approver_info = _('Next Approver: %s') % (pending[0].user_id.name or '')
            else:
                rec.next_approver_info = _('Approval Chain Completed')

    @api.depends('approver_ids.status', 'approver_ids.user_id', 'approver_ids.sequence')
    def _compute_is_my_turn(self):
        uid = self.env.user.id
        for rec in self:
            turn = False
            my_lines = rec.approver_ids.filtered(lambda a: a.user_id.id == uid and a.status in ['new', 'pending'])
            for line in my_lines:
                previous = rec.approver_ids.filtered(lambda a: (a.sequence or 0) < (line.sequence or 0))
                if all(l.status == 'approved' for l in previous):
                    turn = True
                    break
            rec.is_my_turn = turn

    @api.depends('related_task_ids')
    def _compute_tasks_count(self):
        for rec in self:
            rec.tasks_count = len(rec.related_task_ids)


    def _get_my_pending_line(self):
        self.ensure_one()
        uid = self.env.user.id
        
        candidates = self.approver_ids.filtered(lambda a: a.user_id.id == uid and a.status in ['new', 'pending']).sorted('sequence')
        for line in candidates:
            previous = self.approver_ids.filtered(lambda a: (a.sequence or 0) < (line.sequence or 0))
            if all(l.status == 'approved' for l in previous):
                return line
        return False

    def action_open_my_approve_wizard(self):
        self.ensure_one()
        line = self._get_my_pending_line()
        if not line:
            raise UserError(_('No approval line found for you'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Task After Approval'),
            'res_model': 'approval.task.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approver_id': line.id,
                'default_request_id': self.id,
                'default_document_id': self.document_id.id if self.document_id else False,
            }
        }

    def action_my_refuse(self):
        self.ensure_one()
        line = self._get_my_pending_line()
        if not line:
            raise UserError(_('No approval line found for you'))
        line.write({'status': 'refused', 'approval_date': fields.Datetime.now()})
        self.write({'request_status': 'rejected'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Request Rejected.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.depends('urgency_level', 'confidentiality_level', 'approval_type_detailed')
    def _compute_risk_assessment(self):
        for rec in self:
            urgency_risk = {'normal': 1, 'urgent': 2, 'very_urgent': 3, 'critical': 4}.get(rec.urgency_level, 1)
            conf_risk = {'public': 1, 'internal': 2, 'confidential': 3, 'top_secret': 4}.get(rec.confidentiality_level, 1)
            type_risk = {
                'content_review': 1, 'legal_review': 3, 'financial_approval': 3, 'publication_approval': 2,
                'archiving_approval': 1, 'access_permission': 2, 'signature_authority': 4, 'security_clearance': 4
            }.get(rec.approval_type_detailed, 2)
            avg = (urgency_risk + conf_risk + type_risk) / 3
            rec.risk_assessment = 'low' if avg <= 1.5 else 'medium' if avg <= 2.5 else 'high' if avg <= 3.5 else 'critical'

    @api.depends('approver_ids', 'urgency_level', 'confidentiality_level')
    def _compute_complexity_score(self):
        for rec in self:
            complexity = 0
            complexity += len(rec.approver_ids) * 0.5
            complexity += {'normal': 1, 'urgent': 2, 'very_urgent': 3, 'critical': 4}.get(rec.urgency_level, 1)
            complexity += {'public': 1, 'internal': 2, 'confidential': 3, 'top_secret': 4}.get(rec.confidentiality_level, 1)
            rec.complexity_score = min(max(complexity, 1), 10)

    def action_smart_assign_approvers(self):
        for rec in self:
            suggested = []
            if rec.department_id and rec.department_id.manager_id and rec.department_id.manager_id.user_id:
                suggested.append(rec.department_id.manager_id.user_id)
            doc_type = rec.document_id.document_type if rec.document_id else False
            if doc_type in ['contract', 'financial']:
                finance_dept = self.env['hr.department'].search([('name', 'ilike', 'Financial')], limit=1)
                if finance_dept and finance_dept.manager_id and finance_dept.manager_id.user_id:
                    suggested.append(finance_dept.manager_id.user_id)

            seen = set()
            sequence = 10
            for user in suggested:
                if user and user.id not in seen:
                    seen.add(user.id)
                    self.env['approval.approver'].create({
                        'request_id': rec.id,
                        'user_id': user.id,
                        'employee_id': user.employee_id.id if user.employee_id else False,
                        'sequence': sequence,
                        'status': 'new'
                    })
                    sequence += 10
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Approvers assigned successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_escalate_approval(self):
        for rec in self:
            current = rec.approver_ids.filtered(lambda a: a.status == 'pending')
            for approver in current:
                emp = approver.user_id.employee_id
                if emp and emp.parent_id and emp.parent_id.user_id:
                    manager_user = emp.parent_id.user_id
                    self.env['approval.approver'].create({
                        'request_id': rec.id,
                        'user_id': manager_user.id,
                        'employee_id': manager_user.employee_id.id if manager_user.employee_id else False,
                        'sequence': (approver.sequence or 0) + 5,
                        'status': 'new'
                    })
                    rec.message_post(body=_('Escalated approval to %s') % manager_user.name, message_type='notification', subtype_xmlid='mail.mt_note')

    def action_view_document(self):
        self.ensure_one()
        if not self.document_id:
            raise UserError(_('No document linked to this request'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked Document'),
            'res_model': 'document.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('escalation_period')
    def _check_escalation_period(self):
        for rec in self:
            if rec.escalation_period and rec.escalation_period < 1:
                raise ValidationError(_('Escalation period must be at least one hour'))

    @api.model
    def _cron_auto_escalate_overdue_approvals(self):
        overdue = self.search([('request_status', '=', 'pending'), ('auto_escalation', '=', True), ('is_overdue', '=', True)])
        for appr in overdue:
            try:
                appr.action_escalate_approval()
                appr.message_post(body=_('Auto escalated approval due to overdue'), message_type='notification')
            except Exception:
                continue

    @api.model
    def _cron_send_approval_reminders(self):
        pending = self.search([('request_status', '=', 'pending'), ('create_date', '<=', fields.Datetime.now() - timedelta(hours=12))])
        for appr in pending:
            pass  # بعدين راح اضيفة


class ApprovalApprover(models.Model):
    _name = 'approval.approver'
    _description = 'Internal Approver'
    _order = 'sequence, id'

    request_id = fields.Many2one('approval.request', string='request_id', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='user_id', required=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='employee_id')
    status = fields.Selection([
        ('new', 'new'),
        ('pending', 'pending'),
        ('approved', 'approved'),
        ('refused', 'refused')
    ], string='status', default='pending')
    sequence = fields.Integer(string='sequence', default=10)
    comment = fields.Text(string='comment')
    approval_date = fields.Datetime(string='approval_date', readonly=True)
    expected_approval_date = fields.Datetime(string='expected_approval_date')
    is_overdue = fields.Boolean(string='is_overdue', compute='_compute_is_overdue', store=False)

    @api.depends('expected_approval_date', 'status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.expected_approval_date and rec.expected_approval_date < now and rec.status in ['new', 'pending'])

    def action_approve(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Task After Approval'),
            'res_model': 'approval.task.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approver_id': self.id,
                'default_request_id': self.request_id.id,
                'default_document_id': self.request_id.document_id.id if self.request_id.document_id else False,
            }
        }

    def action_approve_final(self):
        self.ensure_one()
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now()})

        req = self.request_id
        if req and not req.approver_ids.filtered(lambda a: a.status not in ['approved']):
            req.write({'request_status': 'approved', 'date_confirmed': fields.Datetime.now()})
        return True

    def action_refuse(self):
        self.ensure_one()
        self.write({'status': 'refused', 'approval_date': fields.Datetime.now()})
        if self.request_id:
            self.request_id.write({'request_status': 'rejected'})
        return True

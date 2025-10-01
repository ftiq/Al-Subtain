# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from dateutil.relativedelta import relativedelta


class HrOvertimeRequest(models.Model):
    _name = 'overtime.request'
    _description = 'Overtime Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', default=lambda self: _('Overtime Request'))
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, index=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today, tracking=True)
    hours = fields.Float(string='Hours', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('converted', 'Converted'),
    ], default='draft', tracking=True, index=True)

    conversion_type = fields.Selection([
        ('leave', 'Convert to Leave Balance'),
        ('money', 'Convert to Money'),
    ], string='Conversion Type', tracking=True)

    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved On', readonly=True)
    rejected_by = fields.Many2one('res.users', string='Rejected By', readonly=True)
    rejected_date = fields.Datetime(string='Rejected On', readonly=True)
    reject_reason = fields.Text(string='Reject Reason')

    is_employee = fields.Boolean(compute='_compute_flags')
    is_approver = fields.Boolean(compute='_compute_flags')
    is_current_approver = fields.Boolean(compute='_compute_is_current_approver', store=False)

    approval_line_ids = fields.One2many('overtime.request.approval', 'request_id', string='Approvals', copy=True)

    attendance_overtime_ids = fields.Many2many(
        'hr.attendance.overtime',
        'overtime_request_attendance_rel',
        'request_id', 'attendance_overtime_id',
        string='Attendance Overtime', copy=False, readonly=True)

    def _check_is_approver(self):
        self.ensure_one()
        user = self.env.user
        if user.has_group('hr.group_hr_user') or user.has_group('hr_holidays.group_hr_holidays_responsible'):
            return True
        department_manager = self.employee_id.department_id.manager_id.user_id
        return bool(department_manager and department_manager.id == user.id)

    @api.depends('employee_id')
    def _compute_flags(self):
        for rec in self:
            user = self.env.user
            rec.is_employee = bool(rec.employee_id.user_id and rec.employee_id.user_id.id == user.id)
            if not rec.employee_id:
                rec.is_approver = False
            else:
                if user.has_group('hr.group_hr_user') or user.has_group('hr_holidays.group_hr_holidays_responsible'):
                    rec.is_approver = True
                else:
                    manager_user = rec.employee_id.department_id.manager_id.user_id
                    rec.is_approver = bool(manager_user and manager_user.id == user.id)

    @api.depends('approval_line_ids.state', 'approval_line_ids.approver_user_id')
    def _compute_is_current_approver(self):
        current_uid = self.env.user.id
        for rec in self:
            rec.is_current_approver = bool(rec.approval_line_ids.filtered(
                lambda l: l.state == 'pending' and l.approver_user_id.id == current_uid
            ))

    @api.constrains('hours')
    def _check_hours(self):
        for rec in self:
            if rec.hours <= 0:
                raise UserError(_('Overtime hours must be greater than 0.'))

    def _build_approval_chain_users(self):
        self.ensure_one()
        users = []
        seen = set()
        emp_user = self.employee_id.user_id
        dept = self.employee_id.department_id
        while dept:
            manager_user = dept.manager_id and dept.manager_id.user_id
            if manager_user and manager_user.id not in seen and (not emp_user or manager_user.id != emp_user.id):
                users.append(manager_user)
                seen.add(manager_user.id)
            dept = dept.parent_id


        return users

    def _ensure_approval_lines(self):
        for rec in self:
            if rec.approval_line_ids:
                continue
            approvers = rec._build_approval_chain_users()
            step = 1
            vals_list = []
            for user in approvers:
                vals_list.append({
                    'request_id': rec.id,
                    'step': step,
                    'approver_user_id': user.id,
                    'state': 'pending',
                })
                step += 1
            if vals_list:
                rec.env['overtime.request.approval'].create(vals_list)
    def action_submit(self):
        for rec in self:
            if not rec.is_employee and not self.env.user.has_group('hr.group_hr_user'):
                raise AccessError(_('Only the employee can submit this request.'))
            rec._ensure_approval_lines()
            rec.write({'state': 'to_approve'})
            next_line = rec.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('step')[:1]
            if next_line and next_line.approver_user_id:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=next_line.approver_user_id.id,
                    summary=_('Overtime approval needed'))
            rec.message_post(body=_('Request submitted for approval.'))
        return True

    def action_approve(self):
        for rec in self:
            line = rec.approval_line_ids.filtered(lambda l: l.state == 'pending' and l.approver_user_id.id == self.env.user.id)[:1]
            if not line:
                raise AccessError(_('No pending approval found for you.'))
            line.write({'state': 'approved', 'date': fields.Datetime.now()})
            remaining = rec.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('step')
            if remaining:
                nxt = remaining[0]
                rec.activity_schedule('mail.mail_activity_data_todo', user_id=nxt.approver_user_id.id, summary=_('Overtime approval needed'))
                rec.message_post(body=_('Step approved by %s. Next approver: %s') % (self.env.user.name, nxt.approver_user_id.name))
                rec.write({'state': 'to_approve'})
            else:
                rec.write({
                    'state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now(),
                })
                rec.message_post(body=_('Request fully approved.'))
        return True

    def action_reject(self):
        for rec in self:
            line = rec.approval_line_ids.filtered(lambda l: l.state == 'pending' and l.approver_user_id.id == self.env.user.id)[:1]
            if not line:
                raise AccessError(_('No pending approval found for you.'))
            if not rec.reject_reason:
                raise UserError(_('Please provide a reject reason.'))
            line.write({'state': 'rejected', 'date': fields.Datetime.now(), 'note': rec.reject_reason})
            rec.write({
                'state': 'rejected',
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
            })
            rec.message_post(body=_('Request rejected by %s: %s') % (self.env.user.name, rec.reject_reason))
        return True

    def _get_hours_per_day(self):
        self.ensure_one()
        return (
            self.employee_id.sudo().resource_calendar_id.hours_per_day
            or self.env.company.resource_calendar_id.hours_per_day
            or 8.0
        )

    def _convert_to_leave(self):
        self.ensure_one()
        hours_per_day = self._get_hours_per_day()
        number_of_days = self.hours / hours_per_day if hours_per_day else 0.0
        if number_of_days <= 0:
            raise UserError(_('Computed number of days must be > 0.'))
        leave_type = self.env.ref('hr_overtime_request.leave_type_comp_time', raise_if_not_found=False)
        if not leave_type:
            raise UserError(_('Compensatory Time Off type is not configured.'))
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'employee_id': self.employee_id.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': number_of_days,
            'name': _('Compensatory time for overtime on %s') % (fields.Date.to_string(self.date),),
            'date_from': fields.Date.today(),
        })
        try:
            allocation.sudo().action_approve()
        except Exception:
            pass
        return allocation

    def _convert_to_money(self):
        self.ensure_one()

        input_type = self.env.ref('hr_overtime_request.input_type_overtime', raise_if_not_found=False)
        if not input_type:
            raise UserError(_('Payslip Input Type OVERTIME is not configured.'))
        payslip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['draft', 'verify']),
            ('date_from', '<=', self.date),
            ('date_to', '>=', self.date),
        ], limit=1)
        if payslip:
            self.env['hr.payslip.input'].create({
                'payslip_id': payslip.id,
                'input_type_id': input_type.id,
                'name': _('Overtime on %s') % (fields.Date.to_string(self.date),),

                'amount': self.hours,
            })
            return True

        payroll_group = self.env.ref('hr_payroll.group_hr_payroll_user', raise_if_not_found=False)
        self.message_post(body=_('No draft payslip found for the period. Payroll should add OVERTIME input (amount=%s hours) to the next payslip.' % self.hours),
                          partner_ids=payroll_group and payroll_group.users.mapped('partner_id').ids or [])
        return False

    def action_convert(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only approved requests can be converted.'))
            if not rec._check_is_approver():
                raise AccessError(_('You are not allowed to convert this request.'))
            if not rec.conversion_type:
                raise UserError(_('Please choose a conversion type.'))
            if rec.conversion_type == 'leave':
                rec._convert_to_leave()
                rec.message_post(body=_('Converted to leave balance.'))
            elif rec.conversion_type == 'money':
                rec._convert_to_money()
                rec.message_post(body=_('Conversion to money initiated.'))
            rec.write({'state': 'converted'})
        return True


    @api.model
    def cron_generate_requests_from_attendance(self):
        ICP = self.env['ir.config_parameter'].sudo()
        autogen_enabled = ICP.get_param('hr_overtime_request.attendance_autogen_enabled', 'True') == 'True'
        if not autogen_enabled:
            return True
        try:
            window_days = int(ICP.get_param('hr_overtime_request.attendance_window_days', '30'))
        except Exception:
            window_days = 30
        use_real = ICP.get_param('hr_overtime_request.attendance_use_real', 'True') == 'True'

        today = fields.Date.today()
        date_from = today - relativedelta(days=window_days)
        Overtime = self.env['hr.attendance.overtime'].sudo()

        ot_lines = Overtime.search([
            ('adjustment', '=', False),
            ('duration', '>', 0),
            ('date', '>=', date_from),
            ('date', '<=', today),
        ])
        if not ot_lines:
            return True

        linked = self.search([('date', '>=', date_from), ('date', '<=', today)])
        linked_ids = set(linked.mapped('attendance_overtime_ids').ids)
        for ot in ot_lines:
            if ot.id in linked_ids:
                continue
            hours = (ot.duration_real if use_real else ot.duration) or 0.0
            if hours <= 0:
                continue

            validation = ot.employee_id.company_id.attendance_overtime_validation or 'by_manager'
            initial_state = 'approved' if validation == 'no_validation' else 'to_approve'
            vals = {
                'employee_id': ot.employee_id.id,
                'date': ot.date,
                'hours': hours,
                'state': initial_state,
                'attendance_overtime_ids': [(6, 0, [ot.id])],
            }
            if initial_state == 'approved':
                vals.update({'approved_by': self.env.user.id, 'approved_date': fields.Datetime.now()})
            req = self.create(vals)
            if initial_state == 'to_approve':

                req._ensure_approval_lines()
                next_line = req.approval_line_ids.filtered(lambda l: l.state == 'pending').sorted('step')[:1]
                if next_line and next_line.approver_user_id:
                    req.activity_schedule('mail.mail_activity_data_todo', user_id=next_line.approver_user_id.id, summary=_('Overtime approval needed'))
            req.message_post(body=_('Auto-generated from Attendance for %s hours') % hours)
        return True


class HrOvertimeApproval(models.Model):
    _name = 'overtime.request.approval'
    _description = 'Overtime Request Approval Step'
    _order = 'request_id, step'

    request_id = fields.Many2one('overtime.request', string='Request', required=True, ondelete='cascade', index=True)
    step = fields.Integer(string='Step', required=True, default=1)
    approver_user_id = fields.Many2one('res.users', string='Approver', required=True, index=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending', required=True, index=True)
    date = fields.Datetime(string='Date')
    note = fields.Text(string='Note')

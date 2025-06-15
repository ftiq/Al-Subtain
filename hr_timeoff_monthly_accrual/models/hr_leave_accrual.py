from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    monthly_alloc_hours = fields.Float(string="Monthly Allocation Hours", default=10.0)
    threshold_hours = fields.Float(string="Low Balance Threshold Hours", default=0.0,
                                   help="Send email alert when remaining hours <= this value")
    annual_alloc_hours = fields.Float(string="Annual Allocation Hours", default=0.0)
    monthly_leave_days = fields.Integer(string="Allowed Leave Days Per Month", default=0,
                                        help="Configure allowed leave days per month.")

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def _cron_accrue_timeoff(self):
        leave_type = self.env.ref('hr_timeoff_monthly_accrual.timeoff_type_time_credit', raise_if_not_found=False)
        if not leave_type or leave_type.monthly_alloc_hours <= 0:
            return
        employees = self.env['hr.employee'].search([])
        today = fields.Date.today()
        month_str = today.strftime('%Y-%m')
        for emp in employees:
            exists = self.search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', leave_type.id),
                ('name', 'ilike', month_str)
            ])
            if exists:
                continue
            accrual = leave_type.monthly_alloc_hours
            vals = {
                'name': f"تراكم إجازات زمنية - {month_str}",
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_hours': accrual,
                'allocation_type': 'add',
                'state': 'confirm',
                'request_date_from': today.replace(day=1),
                'request_date_to': today.replace(day=1),
                'expiration_date': today + timedelta(days=365),
            }
            self.create(vals)
            # Low balance alert
            if leave_type.threshold_hours > 0:
                emp.refresh()
                rem = emp.remaining_timeoff_hours
                if rem <= leave_type.threshold_hours:
                    template = self.env.ref('hr_timeoff_monthly_accrual.email_template_low_timeoff', False)
                    if template:
                        template.send_mail(emp.id, force_send=True)

    @api.model
    def _cron_annual_allocate(self):
        leave_type = self.env.ref('hr_timeoff_monthly_accrual.timeoff_type_time_credit', raise_if_not_found=False)
        if not leave_type or leave_type.annual_alloc_hours <= 0:
            return
        employees = self.env['hr.employee'].search([])
        today = fields.Date.today()
        year_str = today.strftime('%Y')
        for emp in employees:
            exists = self.search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', leave_type.id),
                ('name', 'ilike', year_str)
            ])
            if exists:
                continue
            vals = {
                'name': f"تخصيص سنوي إجازات زمنية - {year_str}",
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'number_of_hours': leave_type.annual_alloc_hours,
                'allocation_type': 'add',
                'state': 'confirm',
                'request_date_from': today,
                'request_date_to': today,
                'expiration_date': today + timedelta(days=365),
            }
            self.create(vals)

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    @api.constrains('number_of_hours', 'holiday_status_id')
    def _check_time_credit_hours(self):
        for rec in self:
            lt = rec.holiday_status_id
            if lt and lt.monthly_alloc_hours and rec.request_unit == 'hour':
                if rec.number_of_hours > lt.monthly_alloc_hours:
                    raise ValidationError(f"لا يمكن طلب أكثر من {lt.monthly_alloc_hours} ساعة في الشهر لهذا النوع من الإجازات.")

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    remaining_timeoff_hours = fields.Float(
        string="Remaining Time-off Hours",
        compute='_compute_remaining_timeoff'
    )

    @api.depends()
    def _compute_remaining_timeoff(self):
        leave_type = self.env.ref('hr_timeoff_monthly_accrual.timeoff_type_time_credit', raise_if_not_found=False)
        for emp in self:
            if not leave_type:
                emp.remaining_timeoff_hours = 0.0
            else:
                allocs = self.env['hr.leave.allocation'].search([
                    ('employee_id','=',emp.id),
                    ('holiday_status_id','=',leave_type.id),
                    ('state','=','confirm'),
                    ('expiration_date','>=',fields.Date.today())
                ])
                total_alloc = sum(a.number_of_hours for a in allocs)
                leaves = self.env['hr.leave'].search([
                    ('employee_id','=',emp.id),
                    ('holiday_status_id','=',leave_type.id),
                    ('state','=','validate')
                ])
                total_taken = sum(l.number_of_hours for l in leaves)
                emp.remaining_timeoff_hours = total_alloc - total_taken
                emp.leave_type_threshold = leave_type.threshold_hours

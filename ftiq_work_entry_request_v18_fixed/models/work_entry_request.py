# -*- coding: utf-8 -*-
from odoo import models, fields, api

LEAVE_TYPES = ["leave_normal","leave_comp","leave_unpaid","leave_sick","leave_paid_days"]

class WorkEntryRequest(models.Model):
    _name = "hr.work.entry.request"
    _description = "Work Entry Request"
    _inherit = ["mail.thread","mail.activity.mixin"]

    name = fields.Char(string="Reference", default=lambda self: self.env['ir.sequence'].next_by_code('hr.work.entry.request') or 'New', readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    date_from = fields.Datetime(string="Start Date", required=True, tracking=True)
    date_to = fields.Datetime(string="End Date", required=True, tracking=True)

    request_type = fields.Selection([
        ("attendance","ساعات إضافية"),
        ("leave_normal","إجازة عادية"),
        ("leave_comp","الإجازة التعويضية"),
        ("home_work","العمل من المنزل"),
        ("leave_unpaid","إجازة غير مدفوعة"),
        ("leave_sick","الإجازة المرضية"),
        ("leave_paid_days","أيام الإجازة المدفوعة"),
        ("out_contract","خارج العقد"),
    ], string="Requested Type", required=True, tracking=True)

    approved_type = fields.Selection([
        ("attendance","ساعات إضافية"),
        ("leave_normal","إجازة عادية"),
        ("leave_comp","الإجازة التعويضية"),
        ("home_work","العمل من المنزل"),
        ("leave_unpaid","إجازة غير مدفوعة"),
        ("leave_sick","الإجازة المرضية"),
        ("leave_paid_days","أيام الإجازة المدفوعة"),
        ("out_contract","خارج العقد"),
    ], string="Approved Type", tracking=True)

    approved_leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type (Final)")
    approved_work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Work Entry Type (Final)")

    state = fields.Selection([("draft","Draft"),("submit","Submitted"),("approve","Approved"),("reject","Rejected")], default="draft", tracking=True)
    note = fields.Text("Notes")
    approval_request_id = fields.Many2one("approval.request", string="Approval Request")

    def action_submit(self):
        approval_type = self.env.ref("approvals.approval_category_data_leaves", raise_if_not_found=False)
        for rec in self:
            approval = self.env["approval.request"].create({
                "name": f"{rec.name} - {rec.employee_id.name}",
                "request_owner_id": self.env.user.id,
                "category_id": approval_type.id if approval_type else False,
                "request_date": fields.Date.today(),
                "reference": f"work_entry_request,{rec.id}",
                "reason": rec.note or "",
            })
            rec.approval_request_id = approval.id
            rec.state="submit"
            rec.message_post(body="تم إرسال الطلب للموافقة.")

    @api.model
    def _cron_check_approvals(self):
        for rec in self.search([("state","=","submit"),("approval_request_id.status","=","approved")]):
            rec._execute_final_action()
        for rec in self.search([("state","=","submit"),("approval_request_id.status","in",["refused","cancelled"])]):
            rec._execute_reject_action()

    def _resolve_final_type(self):
        return self.approved_type or self.request_type

    def _execute_final_action(self):
        final_type=self._resolve_final_type()
        if final_type=="attendance":
            self.env["hr.attendance"].create({"employee_id":self.employee_id.id,"check_in":self.date_from,"check_out":self.date_to})
        elif final_type in LEAVE_TYPES:
            leave_type=self.approved_leave_type_id or self.env["hr.leave.type"].search([],limit=1)
            if leave_type:
                self.env["hr.leave"].create({"employee_id":self.employee_id.id,"holiday_status_id":leave_type.id,"date_from":self.date_from,"date_to":self.date_to,"name":f"Leave ({final_type})"})
        elif final_type=="home_work":
            wet=self.approved_work_entry_type_id or self.env.ref("hr_work_entry.work_entry_type_home_work",raise_if_not_found=False)
            if wet:
                self.env["hr.work.entry"].create({"employee_id":self.employee_id.id,"date_start":self.date_from,"date_stop":self.date_to,"work_entry_type_id":wet.id})
        elif final_type=="out_contract":
            wet=self.approved_work_entry_type_id or self.env.ref("hr_work_entry.work_entry_type_out_of_contract",raise_if_not_found=False)
            if wet:
                self.env["hr.work.entry"].create({"employee_id":self.employee_id.id,"date_start":self.date_from,"date_stop":self.date_to,"work_entry_type_id":wet.id})
        self.state="approve"
        self.message_post(body="✅ تمت الموافقة وتنفيذ الإجراء.")

    def _execute_reject_action(self):
        self.state="reject"
        self.message_post(body="❌ تم رفض الطلب.")

# -*- coding: utf-8 -*-
from odoo import models, fields, api

LEAVE_TYPES = [
    "leave_normal",
    "leave_comp",
    "leave_unpaid",
    "leave_sick",
    "leave_paid_days",
]

class WorkEntryRequest(models.Model):
    _name = "hr.work.entry.request"
    _description = "Work Entry Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Reference", default=lambda self: self.env['ir.sequence'].next_by_code('hr.work.entry.request') or 'New', readonly=True, copy=False)
    employee_id = fields.Many2one("hr.employee", string="Employee", required=True, tracking=True)
    date_from = fields.Datetime(string="Start Date", required=True, tracking=True)
    date_to = fields.Datetime(string="End Date", required=True, tracking=True)

    request_type = fields.Selection([
        ("attendance", "ساعات إضافية"),
        ("leave_normal", "إجازة عادية"),
        ("leave_comp", "الإجازة التعويضية"),
        ("home_work", "العمل من المنزل"),
        ("leave_unpaid", "إجازة غير مدفوعة"),
        ("leave_sick", "الإجازة المرضية"),
        ("leave_paid_days", "أيام الإجازة المدفوعة"),
        ("out_contract", "خارج العقد"),
    ], string="Requested Type", required=True, tracking=True)

    approved_type = fields.Selection([
        ("attendance", "ساعات إضافية"),
        ("leave_normal", "إجازة عادية"),
        ("leave_comp", "الإجازة التعويضية"),
        ("home_work", "العمل من المنزل"),
        ("leave_unpaid", "إجازة غير مدفوعة"),
        ("leave_sick", "الإجازة المرضية"),
        ("leave_paid_days", "أيام الإجازة المدفوعة"),
        ("out_contract", "خارج العقد"),
    ], string="Approved Type", help="النوع النهائي بعد الموافقة", tracking=True)

    approved_leave_type_id = fields.Many2one("hr.leave.type", string="Leave Type (Final)", help="إذا كان النوع النهائي إجازة، اختر نوع الإجازة الهدف.")
    approved_work_entry_type_id = fields.Many2one("hr.work.entry.type", string="Work Entry Type (Final)", help="اختياري: بديل عن القيم الافتراضية للعمل من المنزل/خارج العقد.")

    state = fields.Selection([
        ("draft", "Draft"),
        ("submit", "Submitted"),
        ("approve", "Approved"),
        ("reject", "Rejected"),
    ], default="draft", tracking=True)

    note = fields.Text(string="Notes")

    approval_request_id = fields.Many2one("approval.request", string="Approval Request", readonly=True, copy=False)

    # ========== SUBMIT ==========
    def action_submit(self):
        approval_type = self.env.ref("approvals.approval_category_data_leaves", raise_if_not_found=False)
        for rec in self:
            approval_vals = {
                "name": f"{rec.name} - {rec.employee_id.name}",
                "request_owner_id": self.env.user.id,
                "category_id": approval_type.id if approval_type else False,
                "request_date": fields.Date.today(),
                # reference يسمح لنا نعرف لمن يرجع السجل
                "reference": f"work_entry_request,{rec.id}",
                "reason": rec.note or "",
            }
            approval = self.env["approval.request"].create(approval_vals)
            rec.approval_request_id = approval.id
            rec.state = "submit"

            rec.message_post(
                body=(
                    "تم إرسال الطلب للموافقة.<br/>"
                    f"النوع المطلوب: <b>{dict(rec._fields['request_type'].selection).get(rec.request_type)}</b>"
                ),
                subtype_xmlid="mail.mt_note",
            )

    # ========== CRON ==========
    @api.model
    def _cron_check_approvals(self):
        # موافقات مكتملة
        approved_reqs = self.search([("state", "=", "submit"), ("approval_request_id.status", "=", "approved")])
        for rec in approved_reqs:
            rec._execute_final_action()

        # مرفوضة أو ملغاة
        refused_reqs = self.search([("state", "=", "submit"), ("approval_request_id.status", "in", ["refused", "cancelled"])])
        for rec in refused_reqs:
            rec._execute_reject_action()

    # ========== HELPERS ==========
    def _resolve_final_type(self):
        return self.approved_type or self.request_type

    def _create_attendance(self):
        self.env["hr.attendance"].create({
            "employee_id": self.employee_id.id,
            "check_in": self.date_from,
            "check_out": self.date_to,
        })

    def _create_leave(self, final_type):
        # إذا المستخدم حدد نوع الإجازة بشكل صريح
        leave_type = self.approved_leave_type_id
        if not leave_type:
            # حاول نلقط نوع إجازة بالاسم أو بكود مخصص
            # fallback: أول نوع إجازة متاح
            leave_type = self.env["hr.leave.type"].search([], limit=1)
        if not leave_type:
            return
        self.env["hr.leave"].create({
            "employee_id": self.employee_id.id,
            "holiday_status_id": leave_type.id,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "name": f"Leave ({final_type}) - {self.name}",
        })

    def _create_work_entry(self, xmlid_fallback):
        work_entry_type_id = self.approved_work_entry_type_id.id if self.approved_work_entry_type_id else False
        if not work_entry_type_id:
            try:
                work_entry_type_id = self.env.ref(xmlid_fallback).id
            except Exception:
                # fallback: أول نوع work entry
                wet = self.env["hr.work.entry.type"].search([], limit=1)
                work_entry_type_id = wet.id if wet else False
        if not work_entry_type_id:
            return
        self.env["hr.work.entry"].create({
            "employee_id": self.employee_id.id,
            "date_start": self.date_from,
            "date_stop": self.date_to,
            "work_entry_type_id": work_entry_type_id,
        })

    # ========== FINAL ACTIONS ==========
    def _execute_final_action(self):
        final_type = self._resolve_final_type()

        if final_type == "attendance":
            self._create_attendance()
        elif final_type in LEAVE_TYPES:
            self._create_leave(final_type)
        elif final_type == "home_work":
            self._create_work_entry("hr_work_entry.work_entry_type_home_work")
        elif final_type == "out_contract":
            self._create_work_entry("hr_work_entry.work_entry_type_out_of_contract")

        self.state = "approve"
        self.message_post(
            body=(
                "✅ تمت الموافقة وتنفيذ الإجراء.<br/>"
                f"النوع النهائي: <b>{dict(self._fields['approved_type'].selection).get(self.approved_type or self.request_type)}</b>"
            ),
            subtype_xmlid="mail.mt_note",
        )
        template = self.env.ref("ftiq_work_entry_request.mail_tmpl_work_entry_approved", raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _execute_reject_action(self):
        self.state = "reject"
        self.message_post(body="❌ تم رفض الطلب وفق سلسلة الموافقات.", subtype_xmlid="mail.mt_note")
        template = self.env.ref("ftiq_work_entry_request.mail_tmpl_work_entry_refused", raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    # زر يدوي اختياري للرفض
    def action_reject(self):
        self._execute_reject_action()

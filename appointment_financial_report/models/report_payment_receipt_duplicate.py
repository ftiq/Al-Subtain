# -*- coding: utf-8 -*-
from odoo import api, models


class ReportPaymentReceiptDuplicate(models.AbstractModel):
    _name = 'report.appointment_financial_report.pay_rcpt_dup'
    _description = 'Payment Receipt (Duplicated on same page)'

    def amount_to_text_ar(self, amount, currency):
        cur = currency or self.env.company.currency_id
        try:
            res = cur.amount_to_text(amount) if cur else '{:,.2f}'.format(amount)
        except Exception:
            res = '{:,.2f}'.format(amount)

        if res and not res.strip().endswith('فقط لا غير'):
            res = f"{res} فقط لا غير"
        return res

    def fmt_date(self, dt):
        if not dt:
            return ''
        try:
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return str(dt)

    def fmt_datetime(self, dt):
        if not dt:
            return ''
        try:
            return dt.strftime('%d/%m/%Y %I:%M %p')
        except Exception:
            return str(dt)

    @api.model
    def _get_report_values(self, docids, data=None):
        payments = self.env['account.payment'].browse(docids)
        company = self.env.company
        return {
            'doc_ids': payments.ids,
            'doc_model': 'account.payment',
            'docs': payments,
            'company': company,
            'user': self.env.user,
            'amount_to_text_ar': self.amount_to_text_ar,
            'fmt_date': self.fmt_date,
            'fmt_datetime': self.fmt_datetime,
        }

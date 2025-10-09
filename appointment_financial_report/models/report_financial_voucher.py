# -*- coding: utf-8 -*-
from odoo import api, models, _


class ReportFinancialVoucher(models.AbstractModel):
    _name = 'report.appointment_financial_report.financial_voucher_template'
    _description = 'Financial Voucher Report (Arabic)'

    def get_title(self, move):
        journal_type = getattr(move.journal_id, 'type', False)
        if journal_type == 'sale' or move.move_type in ('out_invoice', 'out_refund'):
            return _('form')

        if journal_type == 'cash':
            amount = 0.0
            default_account = getattr(move.journal_id, 'default_account_id', False)
            if default_account:
                cash_lines = move.line_ids.filtered(lambda l: not l.display_type and l.account_id.id == default_account.id)
                amount = sum(cash_lines.mapped('debit')) - sum(cash_lines.mapped('credit'))
            else:
                lines = move.line_ids.filtered(lambda l: not l.display_type)
                amount = (sum(lines.mapped('debit')) - sum(lines.mapped('credit'))) or 0.0
            return _('receipt') if amount > 0 else _('payment')
        if journal_type == 'general':
            return _('settlement')

        signed = getattr(move, 'amount_total_signed', 0.0) or getattr(move, 'amount_total', 0.0) or 0.0
        if signed:
            return _('receipt') if signed > 0 else _('payment')
        return _('payment')

    def _get_sale_orders(self, move):
        orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
        if not orders and move.invoice_origin:
            names = [n.strip() for n in move.invoice_origin.split(',') if n.strip()]
            if names:
                orders = self.env['sale.order'].search([('name', 'in', names)])
        return orders

    def _get_related_tasks(self, move):
        orders = self._get_sale_orders(move)
        Task = self.env['project.task']
        tasks = move.invoice_line_ids.mapped('sale_line_ids.task_id')
        if orders:
            tasks |= orders.mapped('task_id')
            tasks |= Task.search([('sale_order_id', 'in', orders.ids)])
        return tasks

    def get_book_number(self, move):
        tasks = self._get_related_tasks(move)
        task = tasks[:1]
        return task.book_number if task else ''

    def get_cost_center(self, move):
        """Try to extract a single cost center from invoice lines' analytic distribution.
        Returns the first analytic account code or name.
        """
        AA = self.env['account.analytic.account']
        for line in move.line_ids:
            dist = getattr(line, 'analytic_distribution', None)
            if isinstance(dist, dict) and dist:

                aa_id = int(list(dist.keys())[0])
                aa = AA.browse(aa_id)
                if aa and aa.exists():
                    return aa.code or aa.name or ''
        return ''

    def get_project_name_from_questionnaire(self, move):
        """Return the answer of the first question from FSM task questionnaire.
        Falls back to sale order answers if any.
        """
        tasks = self._get_related_tasks(move)
        task = tasks[:1]
        if task:
            ans = self.env['fsm.task.answer.input'].search([('task_id', '=', task.id)], order='id asc', limit=1)
            if ans:
                return ans.value_answer_id.name or ans.value_text_box or ''

        orders = self._get_sale_orders(move)
        if orders:
            sale_ans = self.env['appointment.sale.answer.input'].search([
                ('sale_order_id', 'in', orders.ids)
            ], order='id asc', limit=1)
            if sale_ans:
                return sale_ans.value_answer_id.name or sale_ans.value_text_box or ''
        return ''

    def amount_to_text_ar(self, amount, currency):
        try:
            txt = currency.amount_to_text(amount)

            if txt:
                only_tr = _('')
                lower_txt = txt.lower()
                if ('only' not in lower_txt) and (only_tr.lower() not in lower_txt):
                    txt = f"{txt} {only_tr}"
            return txt
        except Exception:
            return ''

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)

        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        is_rtl = bool(lang and getattr(lang, 'direction', '') == 'rtl')
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,

            'get_title': self.get_title,
            'get_sale_orders': self._get_sale_orders,
            'get_tasks': self._get_related_tasks,
            'get_book_number': self.get_book_number,
            'get_cost_center': self.get_cost_center,
            'get_project_name': self.get_project_name_from_questionnaire,
            'amount_to_text_ar': self.amount_to_text_ar,
            'is_rtl': is_rtl,
        }

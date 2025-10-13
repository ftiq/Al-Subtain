# -*- coding: utf-8 -*-
from odoo import api, models, fields, _


class ReportFormIntake(models.AbstractModel):
    _name = 'report.appointment_financial_report.form_intake_template'
    _description = 'Form Intake Report'


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
            tasks |= Task.search([('sale_order_id', 'in', orders.ids)])
        return tasks

    def get_book_number(self, move):
        tasks = self._get_related_tasks(move)
        task = tasks[:1]
        return getattr(task, 'book_number', '') if task else ''

    def get_project_name(self, move):
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

    def get_exec_side(self, move):
        tasks = self._get_related_tasks(move)
        names = []
        for t in tasks:
            if getattr(t, 'user_ids', False):
                names += t.user_ids.mapped('name')
        names = [n for n in names if n]
        return ', '.join(sorted(set(names))) if names else ''

    def get_partner_phone(self, move):
        partner = move.partner_id
        return partner.mobile or partner.phone or ''

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

    def get_invoice_rows(self, move):
        """Return rows directly from the invoice lines to mirror the invoice exactly.
        - Skip display-only lines (sections/notes).
        - Use price_unit and quantity from the invoice line.
        - Use price_subtotal for the line total (matches the invoice 'Amount' column by default).
        """
        rows = []
        i = 0
        for line in move.invoice_line_ids.filtered(lambda l: not l.display_type and not getattr(l, 'tax_line_id', False) and not getattr(l, 'exclude_from_invoice_tab', False)):

            exec_names = ''
            samples_count = 0.0
            try:
                so_line = line.sale_line_ids[:1]
                task = so_line and so_line.task_id or False
                if task:
                    rs = self.env['lab.result.set'].search([('sample_id.task_id', '=', task.id)])
                    names = rs.mapped('testers_ids.name') if rs else []
                    if not names:
                        names = task.user_ids.mapped('name')
                    names = [n for n in names if n]
                    if names:
                        exec_names = ', '.join(sorted(set(names)))

                    samples_count = float(getattr(task, 'total_samples_count', 0.0) or 0.0)
                    if not samples_count:
                        samples = self.env['lab.sample'].search([('task_id', '=', task.id)])
                        if samples:
                            qtys = [float(s.quantity or 0.0) for s in samples]
                            samples_count = sum(qtys) if qtys else float(len(samples))
                else:
                    rel_tasks = self._get_related_tasks(move)
                    if rel_tasks:
                        rs = self.env['lab.result.set'].search([('sample_id.task_id', 'in', rel_tasks.ids)])
                        names = rs.mapped('testers_ids.name') if rs else []
                        if not names:
                            names = rel_tasks.mapped('user_ids.name')
                        names = [n for n in names if n]
                        if names:
                            exec_names = ', '.join(sorted(set(names)))
            except Exception:
                exec_names = ''
                samples_count = 0.0
            i += 1
            rows.append({
                'seq': i,
                'name': line.name or (line.product_id and line.product_id.display_name) or '',
                'qty': line.quantity or 0.0,
                'price_unit': line.price_unit or 0.0,
                'subtotal': line.price_subtotal or 0.0,
                'exec': exec_names,
                'samples': samples_count,
            })
        if not rows:
            try:
                orders = self._get_sale_orders(move)
                so_lines = orders.mapped('order_line') if orders else self.env['sale.order.line']
                i = 0
                for so in so_lines:
                    task = getattr(so, 'task_id', False)
                    exec_names = ''
                    samples_count = 0.0
                    if task:
                        rs = self.env['lab.result.set'].search([('sample_id.task_id', '=', task.id)])
                        names = rs.mapped('testers_ids.name') if rs else []
                        if not names:
                            names = task.user_ids.mapped('name')
                        names = [n for n in names if n]
                        if names:
                            exec_names = ', '.join(sorted(set(names)))
                        samples_count = float(getattr(task, 'total_samples_count', 0.0) or 0.0)
                        if not samples_count:
                            samples = self.env['lab.sample'].search([('task_id', '=', task.id)])
                            if samples:
                                qtys = [float(s.quantity or 0.0) for s in samples]
                                samples_count = sum(qtys) if qtys else float(len(samples))
                    i += 1
                    rows.append({
                        'seq': i,
                        'name': so.name or (so.product_id and so.product_id.display_name) or '',
                        'qty': so.product_uom_qty or 0.0,
                        'price_unit': so.price_unit or 0.0,
                        'subtotal': so.price_subtotal or ((so.price_unit or 0.0) * (so.product_uom_qty or 0.0)),
                        'exec': exec_names,
                        'samples': samples_count,
                    })
            except Exception:
                pass
        return rows

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        is_rtl = bool(lang and getattr(lang, 'direction', '') == 'rtl')
        company = self.env.company
        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.move',
            'docs': docs,

            'get_book_number': self.get_book_number,
            'get_project_name': self.get_project_name,
            'get_exec_side': self.get_exec_side,
            'get_partner_phone': self.get_partner_phone,
            'amount_to_text_ar': self.amount_to_text_ar,
            'get_invoice_rows': self.get_invoice_rows,

            'is_rtl': is_rtl,
            'company': company,
            'user': self.env.user,
            'print_datetime': fields.Datetime.context_timestamp(self, fields.Datetime.now()),
        }

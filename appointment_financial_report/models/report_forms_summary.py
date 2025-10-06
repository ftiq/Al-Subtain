# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, models, fields


class ReportFormsSummary(models.AbstractModel):
    _name = 'report.appointment_financial_report.forms_summary_template'
    _description = 'Forms Summary (Grouped)'

    def _get_sale_orders_from_moves(self, moves):
        orders = self.env['sale.order']
        if not moves:
            return orders
        for mv in moves:
            orders |= mv.invoice_line_ids.mapped('sale_line_ids.order_id')
            if not mv.invoice_line_ids and mv.invoice_origin:
                names = [n.strip() for n in mv.invoice_origin.split(',') if n.strip()]
                if names:
                    orders |= self.env['sale.order'].search([('name', 'in', names)])
        return orders

    def _get_tasks_from_orders_or_move(self, move, orders):
        Task = self.env['project.task']
        tasks = move.invoice_line_ids.mapped('sale_line_ids.task_id')
        if orders:
            tasks |= Task.search([('sale_order_id', 'in', orders.ids)])
        return tasks

    def _format_amount(self, currency, amount):
        try:
            s = currency.format(amount or 0.0)

            return (s or '').replace('\xa0', ' ')
        except Exception:
            return '{:,.2f}'.format(amount or 0.0)

    @api.model
    def _get_report_values(self, docids, data=None):
        wizard = self.env['forms.summary.wizard'].browse(docids)
        if not wizard:
            return {}
        date_from = min(wizard.mapped('date_from'))
        date_to = max(wizard.mapped('date_to'))
        company = wizard[0].company_id
        journal_ids = wizard[0].journal_ids.ids
        only_posted = bool(wizard[0].only_posted)

        domain = [
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('company_id', '=', company.id),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
        ]
        if journal_ids:
            domain.append(('journal_id', 'in', journal_ids))
        if only_posted:
            domain.append(('state', '=', 'posted'))

        moves = self.env['account.move'].search(domain, order='invoice_date, name')

        groups = defaultdict(list)

        for mv in moves:
            orders = self._get_sale_orders_from_moves(mv)
            key = (orders and orders[0].name) or (mv.invoice_origin or mv.name)
            groups[key].append(mv)


        sections = []
        for form_no, mv_list in groups.items():
            rows = []
            seq = 0
            for mv in mv_list:
                seq += 1
                partner = mv.partner_id
                currency = mv.currency_id
                total = mv.amount_total or 0.0
                residual = mv.amount_residual or 0.0
                paid = (total - residual) if total else 0.0

                orders = self._get_sale_orders_from_moves(mv)
                tasks = self._get_tasks_from_orders_or_move(mv, orders)
                task = tasks[:1]
                project_name = ''
                test_type = ''
                lab_code = ''
                unit_price = 0.0
                if task:

                    ans = self.env['fsm.task.answer.input'].search([('task_id', '=', task.id)], order='id asc', limit=1)
                    if ans:
                        project_name = ans.value_answer_id.name or ans.value_text_box or ''

                    if task.form_line_ids:
                        test_type = task.form_line_ids[0].sample_type_id and task.form_line_ids[0].sample_type_id.name or ''

                        mls = task.form_line_ids.mapped('move_id.move_line_ids')
                        if mls:
                            lab_code = mls[0].field_code or ''

                    if orders:
                        so_line = orders[0].order_line.filtered(lambda l: l.task_id.id == task.id)
                        if so_line:
                            unit_price = so_line[0].price_unit or 0.0

                rows.append({
                    'seq': seq,
                    'date': mv.invoice_date or mv.date,
                    'partner': partner.display_name,
                    'lab_code': lab_code,
                    'total': total,
                    'paid': paid,
                    'due': residual,
                    'payment_kind': 'Cash' if mv.journal_id.type == 'cash' else ('Bank' if mv.journal_id.type == 'bank' else ''),
                    'exec_side': (getattr(task, 'user_ids', False) and task.user_ids[:1].name) if task else '',
                    'project': project_name,
                    'book_no': task.book_number if task else '',
                    'count': task.total_samples_count if task else 0,
                    'price': unit_price or total,
                    'currency': currency,
                    'test_type': test_type,
                })

            totals = {
                'total': sum(r['total'] for r in rows),
                'paid': sum(r['paid'] for r in rows),
                'due': sum(r['due'] for r in rows),
                'count': sum(r.get('count') or 0 for r in rows),
            }

            sections.append({
                'form_no': form_no,
                'rows': rows,
                'totals': totals,
            })


        grand = {
            'forms_count': len(sections),
            'rows_count': sum(len(s['rows']) for s in sections),
            'total': sum(s['totals']['total'] for s in sections) if sections else 0.0,
            'paid': sum(s['totals']['paid'] for s in sections) if sections else 0.0,
            'due': sum(s['totals']['due'] for s in sections) if sections else 0.0,
            'count': sum(s['totals']['count'] for s in sections) if sections else 0,
        }

        return {
            'doc_ids': wizard.ids,
            'doc_model': 'forms.summary.wizard',
            'docs': wizard,
            'date_from': date_from,
            'date_to': date_to,
            'company': company,
            'sections': sections,
            'grand': grand,
            'format_amount': self._format_amount,
        }

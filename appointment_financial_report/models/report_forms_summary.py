# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import api, models, fields
from datetime import datetime


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

        # Group each move by invoice name (form_no = invoice number)
        for mv in moves:
            key = mv.name
            groups[key].append(mv)


        sections = []
        for form_no, mv_list in groups.items():
            rows = []
            seq = 0
            for mv in mv_list:
                partner = mv.partner_id
                currency = mv.currency_id
                total = mv.amount_total or 0.0
                residual = mv.amount_residual or 0.0
                paid = (total - residual) if total else 0.0
                
                orders = self._get_sale_orders_from_moves([mv])
                tasks = self._get_tasks_from_orders_or_move(mv, orders)
                
                # If no tasks, show one row for the invoice
                if not tasks:
                    seq += 1
                    rows.append({
                        'seq': seq,
                        'date': mv.invoice_date or mv.date,
                        'partner': partner.display_name,
                        'book_number': '',
                        'total': total,
                        'paid': paid,
                        'due': residual,
                        'exec_side': '',
                        'project': '',
                        'count': 0,
                        'price': total,
                        'currency': currency,
                        'test_type': '',
                    })
                else:
                    # Show one row per task
                    for task in tasks:
                        seq += 1
                        
                        # Get amounts per task from invoice lines
                        inv_lines = mv.invoice_line_ids.filtered(
                            lambda l: any(sl.task_id.id == task.id for sl in l.sale_line_ids)
                        )
                        task_total = sum(inv_lines.mapped('price_total')) if inv_lines else (total / len(tasks))
                        task_ratio = (task_total / total) if total else (1.0 / len(tasks))
                        task_paid = paid * task_ratio
                        task_due = residual * task_ratio
                        
                        # Unit price from SO or invoice lines
                        unit_price = 0.0
                        if orders:
                            so_lines = orders.mapped('order_line').filtered(lambda l: l.task_id.id == task.id)
                            if so_lines:
                                unit_price = so_lines[0].price_unit or 0.0
                        if not unit_price and inv_lines:
                            unit_price = inv_lines[0].price_unit or 0.0
                        
                        # Project name from questionnaire
                        project_name = ''
                        ans = self.env['fsm.task.answer.input'].search([('task_id', '=', task.id)], order='id asc', limit=1)
                        if ans:
                            project_name = ans.value_answer_id.name or ans.value_text_box or ''
                        
                        # Test type
                        test_type = ''
                        if getattr(task, 'form_line_ids', False) and task.form_line_ids:
                            test_type = task.form_line_ids[0].sample_type_id and task.form_line_ids[0].sample_type_id.name or ''
                        
                        # Book number
                        book_number = getattr(task, 'assignment_reference_book_number', '') or \
                                     getattr(task, 'assignment_book_number', '') or \
                                     getattr(task, 'book_number', '') or ''
                        
                        # Executed by
                        exec_side = ''
                        if getattr(task, 'user_ids', False):
                            names = task.user_ids.mapped('name')
                            if names:
                                exec_side = ', '.join(names)
                        
                        rows.append({
                            'seq': seq,
                            'date': mv.invoice_date or mv.date,
                            'partner': partner.display_name,
                            'book_number': book_number,
                            'total': task_total,
                            'paid': task_paid,
                            'due': task_due,
                            'exec_side': exec_side,
                            'project': project_name,
                            'count': getattr(task, 'total_samples_count', 0) or 0,
                            'price': unit_price or task_total,
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

        # Determine interface direction from language
        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        is_rtl = bool(lang and getattr(lang, 'direction', '') == 'rtl')

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
            'is_rtl': is_rtl,
            'user': self.env.user,
            'print_datetime': fields.Datetime.context_timestamp(self, datetime.utcnow()),
        }

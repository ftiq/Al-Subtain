# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderProjectColumns(models.Model):
    _inherit = 'sale.order'

    project_name = fields.Char(string='اسم المشروع', compute='_compute_project_name', store=True)
    fsm_products_display = fields.Text(string='المنتجات', compute='_compute_fsm_products_display', store=True)
    appointment_datetime = fields.Datetime(string='موعد الحجز')
    appointment_status = fields.Selection([
        ('future', 'قادم'),
        ('overdue', 'متجاوز'),
        ('confirmed', 'مؤكد'),
    ], string='حالة الموعد', compute='_compute_appointment_status', store=True, tracking=True, searchable=False)

    @api.depends('appointment_answer_ids.value_answer_id', 'appointment_answer_ids.value_text_box')
    def _compute_project_name(self):
        for order in self:
            name = ''
            if order.appointment_answer_ids:
                qa = order.appointment_answer_ids[0]
                if qa.value_text_box:
                    name = qa.value_text_box
                elif qa.value_answer_id:
                    name = qa.value_answer_id.name
            order.project_name = name

    @api.depends('order_line.product_id.name', 'order_line.task_id', 'order_line.task_id.is_fsm')
    def _compute_fsm_products_display(self):
        for order in self:
            products = []
            fsm_tasks = order.order_line.filtered(lambda line: line.task_id and line.task_id.is_fsm).mapped('task_id')
            
            if fsm_tasks:
                for line in order.order_line:
                    if line.product_id and line.product_id.name and line.display_type in (False, 'product'):
                        products.append(line.product_id.name)
                
                unique_products = list(set(products))
                order.fsm_products_display = '\n'.join(unique_products) if unique_products else ''
            else:
                order.fsm_products_display = ''

    @api.depends('appointment_datetime', 'state')
    def _compute_appointment_status(self):
        now = fields.Datetime.now()
        for order in self:
            if not order.appointment_datetime:
                order.appointment_status = False
            elif order.state in ('sale', 'done'):
                order.appointment_status = 'confirmed'
            else:
                order.appointment_status = 'future' if order.appointment_datetime > now else 'overdue'

    def _search_fsm_products(self, operator, value):
        """البحث في المنتجات المرتبطة بمهام FSM"""
        if operator == 'ilike' and value:
            sale_orders = self.env['sale.order'].search([
                ('order_line.product_id.name', 'ilike', value),
                ('order_line.task_id.is_fsm', '=', True)
            ])
            return [('id', 'in', sale_orders.ids)]
        return [] 
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FsmTaskServiceLine(models.Model):
    _name = 'fsm.task.service.line'
    _description = 'FSM Task Service Products'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain=[('is_service_fsm', '=', True)])
    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True, store=True)
    currency_id = fields.Many2one(related='product_id.currency_id', string='Currency', readonly=True, store=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', currency_field='currency_id', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    def _sync_sale_order_line(self):

        for line in self:
            if not line.task_id:
                continue
            if line.quantity is None or line.quantity < 0:
                continue

            if line.quantity == 0 and not line.task_id.sale_order_id:
                continue

            line.product_id.with_context(fsm_task_id=line.task_id.id).set_fsm_quantity(line.quantity)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_sale_order_line()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in ['quantity', 'product_id', 'task_id']):
            self._sync_sale_order_line()
        return res

    def unlink(self):
        for line in self:
            if line.task_id:
                line.product_id.with_context(fsm_task_id=line.task_id.id).set_fsm_quantity(0)
        return super().unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    service_line_ids = fields.One2many(
        'fsm.task.service.line',
        'task_id',
        string='Service Products',
        default=lambda self: self._default_service_lines()
    )

    @api.model
    def _default_service_lines(self):


        return [] 
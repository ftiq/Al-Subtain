# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ProjectTaskMiscFields(models.Model):
    _inherit = 'project.task'

    move_ids_display = fields.Char(string='Moves Summary', readonly=True, copy=False)

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', compute='_compute_sale_order', store=False)

    def _compute_sale_order(self):
        SaleLine = self.env['sale.order.line']
        for task in self:
            line = SaleLine.search([('task_id', '=', task.id)], limit=1)
            task.sale_order_id = line.order_id if line else False

    def action_open_receipt(self):
        """Open the stock receipt linked to the task (stock_receipt_id)."""
        self.ensure_one()
        if not self.stock_receipt_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_receipt_id.id,
        }

    def action_open_sale_order(self):
        """Open the sale order linked to the task, if any."""
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        } 
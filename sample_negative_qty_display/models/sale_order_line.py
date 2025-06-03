from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Display Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=False,
    )

    @api.depends('product_uom_qty')
    def _compute_display_qty(self):
        for line in self:
            line.display_qty = abs(line.product_uom_qty)

    def _inverse_display_qty(self):
        for line in self:
            line.product_uom_qty = -abs(line.display_qty)

    @api.onchange('display_qty')
    def _onchange_display_qty(self):
        for line in self:
            line.product_uom_qty = -abs(line.display_qty)

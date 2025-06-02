from odoo import models, fields, api

SAMPLE_PRODUCT_ID = 735  # عدّل هذا إلى رقم المنتج الفعلي لديك

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=False
    )

    @api.depends('product_id', 'product_uom_qty')
    def _compute_display_qty(self):
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID:
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

    def _inverse_display_qty(self):
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID:
                line.product_uom_qty = -abs(line.display_qty)
            else:
                line.product_uom_qty = line.display_qty

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID:
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

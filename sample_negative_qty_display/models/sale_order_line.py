from odoo import models, fields, api

SAMPLE_PRODUCT_ID = 735  # عدل حسب المنتج

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Quantity',
        compute='_compute_display_qty',
        store=False,
    )

    @api.depends('product_uom_qty', 'product_id')
    def _compute_display_qty(self):
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID:
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID and line.product_uom_qty > 0:
                line.product_uom_qty = -abs(line.product_uom_qty)
        return records

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID and line.product_uom_qty > 0:
                line.product_uom_qty = -abs(line.product_uom_qty)
        return res

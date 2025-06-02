from odoo import models, fields, api

SAMPLE_PRODUCT_ID = 735  # عدّل إلى ID منتج العينات

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=True,
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

    @api.model
    def create(self, vals):
        if 'product_id' in vals and vals.get('product_uom_qty'):
            if vals['product_id'] == SAMPLE_PRODUCT_ID:
                vals['product_uom_qty'] = -abs(vals['product_uom_qty'])
        return super().create(vals)

    def write(self, vals):
        if 'product_id' in vals or 'product_uom_qty' in vals:
            for line in self:
                product_id = vals.get('product_id', line.product_id.id)
                qty = vals.get('product_uom_qty', line.product_uom_qty)
                if product_id == SAMPLE_PRODUCT_ID and qty > 0:
                    vals['product_uom_qty'] = -abs(qty)
        return super().write(vals)

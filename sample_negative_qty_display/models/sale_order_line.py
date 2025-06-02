from odoo import models, fields, api

SAMPLE_PRODUCT_ID = 735  # عدل هذا إلى رقم المنتج المطلوب

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=False,
    )

    @api.depends('product_uom_qty', 'product_id')
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'product_id' in vals and 'product_uom_qty' in vals:
                if vals['product_id'] == SAMPLE_PRODUCT_ID:
                    vals['product_uom_qty'] = -abs(vals['product_uom_qty'])
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # بعد الكتابة، نعكس قيمة product_uom_qty للسطر إذا المنتج هو المطلوب
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID and line.product_uom_qty > 0:
                line.product_uom_qty = -abs(line.product_uom_qty)
        return res

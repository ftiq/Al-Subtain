from odoo import models, fields, api

SAMPLE_PRODUCT_ID = 735  # عدل الرقم حسب المنتج المطلوب

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Display Quantity',
        default=0.0,
    )

    @api.onchange('display_qty')
    def _onchange_display_qty(self):
        for line in self:
            if line.product_id and line.product_id.id == SAMPLE_PRODUCT_ID:
                # نغير الكمية الحقيقية إلى سالبة
                line.product_uom_qty = -abs(line.display_qty)
            else:
                # لباقي المنتجات نحتفظ بالكمية كما هي
                line.product_uom_qty = line.display_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('product_id') == SAMPLE_PRODUCT_ID and 'display_qty' in vals:
                vals['product_uom_qty'] = -abs(vals['display_qty'])
            elif 'display_qty' in vals:
                vals['product_uom_qty'] = vals['display_qty']
        return super().create(vals_list)

    def write(self, vals):
        if 'display_qty' in vals or 'product_id' in vals:
            for line in self:
                product_id = vals.get('product_id', line.product_id.id)
                display_qty = vals.get('display_qty', line.display_qty)
                if product_id == SAMPLE_PRODUCT_ID:
                    vals['product_uom_qty'] = -abs(display_qty)
                else:
                    vals['product_uom_qty'] = display_qty
        return super().write(vals)

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Display Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=False,
    )

    @api.model
    def _get_sample_product_id(self):
        # جلب id من xml id
        product = self.env.ref('__export__.product_template_735_e00f2af9', raise_if_not_found=False)
        return product.id if product else False

    @api.depends('product_id', 'product_uom_qty')
    def _compute_display_qty(self):
        sample_id = self._get_sample_product_id()
        for line in self:
            if line.product_id and line.product_id.id == sample_id:
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

    def _inverse_display_qty(self):
        sample_id = self._get_sample_product_id()
        for line in self:
            if line.product_id and line.product_id.id == sample_id:
                line.product_uom_qty = -abs(line.display_qty)
            else:
                line.product_uom_qty = line.display_qty

    @api.onchange('display_qty', 'product_id')
    def _onchange_display_qty(self):
        sample_id = self._get_sample_product_id()
        for line in self:
            if line.product_id and line.product_id.id == sample_id:
                line.product_uom_qty = -abs(line.display_qty)
            else:
                line.product_uom_qty = line.display_qty

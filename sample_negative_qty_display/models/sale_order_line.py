from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    display_qty = fields.Float(
        string='Display Quantity',
        compute='_compute_display_qty',
        inverse='_inverse_display_qty',
        store=False,
        help='يظهر القيمة الموجبة لكن يخزنها كقيمة سالبة للمنتج المحدد'
    )

    @api.depends('product_uom_qty', 'product_id.product_tmpl_id')
    def _compute_display_qty(self):
        for line in self:
            if line.product_id.product_tmpl_id.id == 735:
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

    def _inverse_display_qty(self):
        for line in self:
            if line.product_id.product_tmpl_id.id == 735:
                line.product_uom_qty = -abs(line.display_qty) if line.display_qty else 0.0
            else:
                line.product_uom_qty = line.display_qty

    @api.onchange('product_id')
    def _onchange_product_make_qty_negative(self):
        if self.product_id and self.product_id.product_tmpl_id.id == 735:
            self.product_uom_qty = -abs(self.product_uom_qty or 1)

    @api.onchange('display_qty')
    def _onchange_display_qty(self):
        self._inverse_display_qty()

    @api.model
    def create(self, vals):
        if vals.get('product_id'):
            # لو جلبت الـ template id عبر المنتج
            product = self.env['product.product'].browse(vals['product_id'])
            if product.product_tmpl_id.id == 735:
                qty = vals.get('product_uom_qty', 0.0) or 0.0
                if qty > 0:
                    vals['product_uom_qty'] = -qty
        return super().create(vals)

    def write(self, vals):
        for line in self:
            product = line.product_id
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
            qty = vals.get('product_uom_qty', line.product_uom_qty)
            if product.product_tmpl_id.id == 735 and qty > 0:
                vals['product_uom_qty'] = -qty
        return super().write(vals)

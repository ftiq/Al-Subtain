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
            if line.product_id.product_tmpl_id.id == 735:  # العينات المستلمة
                line.display_qty = abs(line.product_uom_qty)
            else:
                line.display_qty = line.product_uom_qty

    def _inverse_display_qty(self):
        for line in self:
            if line.product_id.product_tmpl_id.id == 735:
                # يخزنها كسالب دائماً
                line.product_uom_qty = -abs(line.display_qty) if line.display_qty else 0.0
            else:
                # يخزنها كما هي
                line.product_uom_qty = line.display_qty

    @api.onchange('display_qty')
    def _onchange_display_qty(self):
        self._inverse_display_qty()  # استدعاء نفس الدالة المستخدمة في inverse

# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    partner_phone = fields.Char(
        string='هاتف العميل',
        related='partner_id.phone',
        readonly=True,
        store=False
    )
    
    partner_email = fields.Char(
        string='بريد العميل',
        related='partner_id.email', 
        readonly=True,
        store=False
    )
    

    products_info = fields.Json(
        string='معلومات المنتجات',
        compute='_compute_products_info',
        store=False
    )

    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_products_info(self):
        """حساب معلومات المنتجات لعرضها في الـ widget"""
        for order in self:
            products = []
            for line in order.order_line.filtered(lambda l: l.product_id and l.display_type in (False, 'product')):
                products.append({
                    'name': line.product_id.name,
                    'qty': line.product_uom_qty,
                    'uom': line.product_uom.name if line.product_uom else '',
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })
            order.products_info = products 
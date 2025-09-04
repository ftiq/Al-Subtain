# -*- coding: utf-8 -*-
from odoo import models, api, fields


class SaleOrderLineSamplePricing(models.Model):
    _inherit = 'sale.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [self._adjust_pricing(vals) for vals in vals_list]
        return super().create(vals_list)

    def write(self, vals):
        if any(key in vals for key in ['product_id', 'product_uom_qty']):
            for line in self:
                updated_vals = line._adjust_pricing(dict(vals))
                super(SaleOrderLineSamplePricing, line).write(updated_vals)
            return True
        return super().write(vals)

    def _adjust_pricing(self, vals):
        """تعديل السعر وفق السعر الثابت للعينة إذا وُجد"""
        product = self.env['product.product'].browse(vals.get('product_id')) if vals.get('product_id') else getattr(self, 'product_id', False)
        if not product:
            return vals
        sample_product = product.product_tmpl_id.related_sample_product_id
        if not sample_product:
            return vals


        param_key = f'appointment_products.fixed_price_{sample_product.id}'
        fixed_price_val = self.env['ir.config_parameter'].sudo().get_param(param_key)
        try:
            fixed_price = float(fixed_price_val) if fixed_price_val else 0.0
        except (ValueError, TypeError):
            fixed_price = 0.0
        if fixed_price <= 0:
            return vals


        qty = vals.get('product_uom_qty')
        if qty is None:
            qty = getattr(self, 'product_uom_qty', 1)
        qty = float(qty) or 1

        base_price = product.list_price
        if qty <= 1:
            unit_price = fixed_price
        else:
            total_price = fixed_price + (qty - 1) * base_price
            unit_price = total_price / qty
        vals['price_unit'] = unit_price
        return vals 
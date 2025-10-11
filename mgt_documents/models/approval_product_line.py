# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ApprovalProductLine(models.Model):


    _name = 'approval.product.line'
    _description = 'سطر منتج للموافقة '
    _order = 'id desc'

    name = fields.Char(string='الوصف')
    request_id = fields.Many2one('approval.request', string='طلب الموافقة', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='الشركة', default=lambda self: self.env.company, index=True)
    product_id = fields.Many2one('product.product', string='المنتج')
    quantity = fields.Float(string='الكمية', default=1.0)
    price_unit = fields.Float(string='سعر الوحدة')
    product_uom_id = fields.Many2one('uom.uom', string='وحدة القياس')
    currency_id = fields.Many2one('res.currency', string='العملة', default=lambda self: self.env.company.currency_id)
    price_subtotal = fields.Monetary(string='المجموع', currency_field='currency_id', compute='_compute_amount', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_amount(self):
        for line in self:
            qty = line.quantity or 0.0
            price = line.price_unit or 0.0
            line.price_subtotal = qty * price

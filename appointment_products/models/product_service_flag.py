# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_service_fsm = fields.Boolean(string='الخدمة', help='حدد إذا كان هذا المنتج يمثل خدمة ميدانية.') 
    is_sample_product = fields.Boolean(
        string='منتج العينات', 
        help='حدد إذا كان هذا المنتج يمثل منتج عينات.'
    )

    @api.constrains('is_sample_product')
    def _check_single_sample_product(self):
        """التأكد من وجود منتج عينات واحد فقط وتعيين التتبع التسلسلي"""
        prevent_dup_param = self.env['ir.config_parameter'].sudo().get_param('appointment_products.prevent_duplicate_sample_product', 'False')
        prevent_dup = str(prevent_dup_param).lower() in ('true', '1')
        for product in self:
            if product.is_sample_product and prevent_dup:
                other_samples = self.env['product.template'].search([
                    ('is_sample_product', '=', True),
                    ('id', '!=', product.id)
                ])
                if other_samples:
                    raise ValidationError(_(
                        'يمكن أن يكون هناك منتج عينات واحد فقط في النظام.\n'
                        'منتج العينات الحالي هو: %s\n'
                        'يرجى إلغاء تحديد منتج العينات الحالي أولاً.'
                    ) % other_samples[0].name)

            if product.is_sample_product and product.tracking != 'serial':
                product.write({'tracking': 'serial'})

    @api.model
    def create(self, vals):
        """التحقق أثناء الإنشاء"""
        prevent_dup_param = self.env['ir.config_parameter'].sudo().get_param('appointment_products.prevent_duplicate_sample_product', 'False')
        prevent_dup = str(prevent_dup_param).lower() in ('true', '1')
        if vals.get('is_sample_product'):
            if prevent_dup:
                existing_sample = self.env['product.template'].search([
                    ('is_sample_product', '=', True)
                ], limit=1)
                if existing_sample:
                    raise ValidationError(_(
                        'يمكن أن يكون هناك منتج عينات واحد فقط في النظام.\n'
                        'منتج العينات الحالي هو: %s\n'
                        'يرجى إلغاء تحديد منتج العينات الحالي أولاً.'
                    ) % existing_sample.name)


            vals['tracking'] = 'serial'
        
        return super(ProductTemplate, self).create(vals)

    def write(self, vals):
        """التحقق أثناء التحديث"""
        prevent_dup_param = self.env['ir.config_parameter'].sudo().get_param('appointment_products.prevent_duplicate_sample_product', 'False')
        prevent_dup = str(prevent_dup_param).lower() in ('true', '1')

        if vals.get('is_sample_product'):
            if prevent_dup:
                for product in self:
                    existing_sample = self.env['product.template'].search([
                        ('is_sample_product', '=', True),
                        ('id', '!=', product.id)
                    ], limit=1)
                    if existing_sample:
                        raise ValidationError(_(
                            'يمكن أن يكون هناك منتج عينات واحد فقط في النظام.\n'
                            'منتج العينات الحالي هو: %s\n'
                            'يرجى إلغاء تحديد منتج العينات الحالي أولاً.'
                        ) % existing_sample.name)


            vals['tracking'] = 'serial'
        
        elif 'is_sample_product' in vals and not vals['is_sample_product']:

            for product in self:
                if product.is_sample_product and product.tracking == 'serial':
                    vals['tracking'] = 'none'
        
        return super(ProductTemplate, self).write(vals)
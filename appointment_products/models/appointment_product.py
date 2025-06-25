# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AppointmentTypeProduct(models.Model):
    _name = 'appointment.type.product'
    _description = 'منتجات نوع الموعد'
    _rec_name = 'product_id'

    appointment_type_id = fields.Many2one(
        'appointment.type', 
        string='نوع الموعد',
        ondelete='cascade', 
        required=True
    )
    product_id = fields.Many2one(
        'product.product', 
        string='المنتج',
        required=True
    )
    uom_id = fields.Many2one(
        related='product_id.uom_id', 
        string='وحدة القياس', 
        readonly=True,
        store=True
    )
    price = fields.Float(
        related='product_id.list_price',
        string='السعر',
        readonly=True,
        store=True
    )
    currency_id = fields.Many2one(
        related='product_id.currency_id',
        string='العملة',
        readonly=True
    )


class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    product_ids = fields.One2many(
        'appointment.type.product', 
        'appointment_type_id', 
        string='المنتجات'
    )
    product_count = fields.Integer(
        compute='_compute_product_count', 
        string='عدد المنتجات'
    )

    @api.depends('product_ids')
    def _compute_product_count(self):
        for appointment_type in self:
            appointment_type.product_count = len(appointment_type.product_ids)

    def action_open_product_selector(self):
        self.ensure_one()
        existing_product_ids = self.product_ids.mapped('product_id').ids
        return {
            'name': _('تحديد المنتجات'),
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.product.selector',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_appointment_type_id': self.id,
                'search_default_filter_sale_ok': 1,
                'search_default_group_by_categ_id': 1,
            },
        }


class AppointmentProductSelector(models.TransientModel):
    _name = 'appointment.product.selector'
    _description = 'أداة اختيار المنتجات للمواعيد'
    
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='نوع الموعد',
        required=True
    )
    product_ids = fields.Many2many(
        'product.product',
        string='المنتجات',
        domain=[('sale_ok', '=', True)],
        required=True
    )
    product_category_id = fields.Many2one(
        'product.category',
        string='فئة المنتج',
        help='تصفية المنتجات حسب الفئة'
    )
    name_search = fields.Char(
        string='بحث',
        help='البحث عن منتجات بالاسم أو الرمز'
    )
    min_price = fields.Float(
        string='الحد الأدنى للسعر',
        help='تصفية المنتجات بالحد الأدنى للسعر'
    )
    max_price = fields.Float(
        string='الحد الأقصى للسعر',
        help='تصفية المنتجات بالحد الأقصى للسعر'
    )
    tag_ids = fields.Many2many(
        'product.tag',
        string='العلامات',
        help='تصفية المنتجات حسب العلامات'
    )
    available_only = fields.Boolean(
        string='المنتجات المتوفرة فقط',
        default=True,
        help='عرض المنتجات المتوفرة فقط'
    )
    
    @api.onchange('product_category_id', 'name_search', 'min_price', 'max_price', 'tag_ids', 'available_only')
    def _onchange_filter_fields(self):
        domain = [('sale_ok', '=', True)]
        

        if self.product_category_id:
            domain.append(('categ_id', 'child_of', self.product_category_id.id))
        

        if self.name_search:
            search_term = self.name_search.strip()
            domain.append('|')
            domain.append(('name', 'ilike', search_term))
            domain.append(('default_code', 'ilike', search_term))
        

        if self.min_price > 0:
            domain.append(('list_price', '>=', self.min_price))
        if self.max_price > 0:
            domain.append(('list_price', '<=', self.max_price))
        

        if self.tag_ids:
            domain.append(('product_tag_ids', 'in', self.tag_ids.ids))
        

        if self.available_only:
            domain.append(('qty_available', '>', 0))
            
        return {'domain': {'product_ids': domain}}
    
    def action_add_products(self):
        self.ensure_one()
        existing_product_ids = self.appointment_type_id.product_ids.mapped('product_id').ids
        products_to_add = [
            (0, 0, {'product_id': product_id})
            for product_id in self.product_ids.ids
            if product_id not in existing_product_ids
        ]
        
        if products_to_add:
            self.appointment_type_id.write({
                'product_ids': products_to_add
            })
            message = _('تمت إضافة %s منتج(ات) بنجاح') % len(products_to_add)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('نجاح'),
                    'message': message,
                    'sticky': False,
                    'type': 'success',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تنبيه'),
                    'message': _('لم تتم إضافة أي منتجات جديدة. قد تكون المنتجات المحددة موجودة بالفعل.'),
                    'sticky': False,
                    'type': 'warning',
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
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
    
    related_sample_product_id = fields.Many2one(
        'product.template',
        string='منتج العينات المرتبط',
        help='اختر منتج العينات الذي سيتم استخدامه مع هذا المنتج',
        domain=lambda self: [('is_sample_product', '=', True)]
    )
    
    sample_info = fields.Char(
        string='معلومات العينة',
        compute='_compute_sample_info',
        help='معلومات حول علاقة هذا المنتج بمنتجات العينات'
    )

    hole_count = fields.Integer(
        string='عدد الفتحات',
        default=0,
        help='عدد الفتحات في الطابوق / العينة (مطلوب للمنتجات المصنفة كمنتج عينات)'
    )

    test_template_ids = fields.Many2many(
        'lab.test.template',
        'product_test_template_rel',
        'product_id',
        'template_id',
        string='قوالب الفحص المتاحة',
        help='قوالب الفحص التي يمكن تطبيقها على هذا المنتج'
    )
    
    default_test_template_ids = fields.Many2many(
        'lab.test.template',
        'product_default_test_template_rel',
        'product_id',
        'template_id',
        string='قوالب الفحص الافتراضية',
        help='قوالب الفحص التي يتم تطبيقها تلقائياً على العينات من هذا المنتج'
    )
    
    test_template_count = fields.Integer(
        string='عدد قوالب الفحص',
        compute='_compute_test_template_count'
    )

    test_flow_template_id = fields.Many2one(
        'lab.test.flow.template',
        string='خطة الفحص الافتراضية',
        help='يتم استخدام هذه الخطة تلقائياً عند إنشاء عينة لهذا المنتج. إذا كانت محددة، سيتم إخفاء حقول اختيار القوالب اليدوية.'
    )

    @api.depends('test_template_ids')
    def _compute_test_template_count(self):
        for product in self:
            product.test_template_count = len(product.test_template_ids)

    @api.depends('is_sample_product', 'related_sample_product_id')
    def _compute_sample_info(self):
        """حساب معلومات العينة بناءً على الحقول المرتبطة"""
        for product in self:
            if product.is_sample_product:
                linked_products_count = self.search_count([
                    ('related_sample_product_id', '=', product.id)
                ])
                if linked_products_count > 0:
                    product.sample_info = f'منتج عينات - مرتبط بـ {linked_products_count} منتج(ات)'
                else:
                    product.sample_info = 'منتج عينات - غير مرتبط بأي منتج'
            elif product.related_sample_product_id:
                product.sample_info = f'يستخدم العينة: {product.related_sample_product_id.name}'
            else:
                product.sample_info = 'لا يستخدم عينات'

    @api.onchange('is_sample_product')
    def _onchange_is_sample_product(self):
        """إذا تم تحديد المنتج كمنتج عينات، قم بمسح الحقل المرتبط"""
        if self.is_sample_product:
            self.related_sample_product_id = False
            return {
                'domain': {
                    'related_sample_product_id': [('id', '=', False)]
                }
            }
        else:
            return {
                'domain': {
                    'related_sample_product_id': [('is_sample_product', '=', True)]
                }
            }

    @api.onchange('test_template_ids')
    def _onchange_test_template_ids(self):
        """تحديث المجال للقوالب الافتراضية"""
        return {
            'domain': {
                'default_test_template_ids': [('id', 'in', self.test_template_ids.ids)]
            }
        }

    def action_view_test_templates(self):
        """عرض قوالب الفحص المرتبطة بالمنتج"""
        action = self.env.ref('appointment_products.action_lab_test_template').read()[0]
        if len(self.test_template_ids) == 1:
            action['views'] = [(self.env.ref('appointment_products.view_lab_test_template_form').id, 'form')]
            action['res_id'] = self.test_template_ids.id
        else:
            action['domain'] = [('id', 'in', self.test_template_ids.ids)]
        return action

    @api.model
    def get_sample_products_domain(self):
        """إرجاع domain لمنتجات العينات المتاحة"""
        return [('is_sample_product', '=', True)]

    @api.model
    def get_sample_products_list(self):
        """إرجاع قائمة بجميع منتجات العينات المتاحة"""
        sample_products = self.search([('is_sample_product', '=', True)])
        return [(product.id, product.name) for product in sample_products]

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

    @staticmethod
    def _format_sample_name(name):
        """أعد صياغة الاسم لإضافة شرطة قبل آخر كلمة إن لم تكن موجودة"""
        if not name:
            return name
        if ' - ' in name:
            return name

        parts = name.rsplit(' ', 1)
        if len(parts) == 2:
            return f"{parts[0]} - {parts[1]}"
        return f"{name} -"

    @api.model_create_multi
    def create(self, vals_list):
        prevent_dup_param = self.env['ir.config_parameter'].sudo().get_param('appointment_products.prevent_duplicate_sample_product', 'False')
        prevent_dup = str(prevent_dup_param).lower() in ('true', '1')

        for vals in vals_list:
            is_sample = vals.get('is_sample_product')

            if is_sample and prevent_dup:
                existing_sample = self.env['product.template'].search([('is_sample_product', '=', True)], limit=1)
                if existing_sample:
                    raise ValidationError(_('يمكن أن يكون هناك منتج عينات واحد فقط في النظام.\nمنتج العينات الحالي هو: %s\nيرجى إلغاء تحديد منتج العينات الحالي أولاً.') % existing_sample.name)

            if is_sample and vals.get('name'):
                vals['name'] = self._format_sample_name(vals['name'])

            if is_sample:
                vals['tracking'] = 'serial'
                vals['related_sample_product_id'] = False

        return super(ProductTemplate, self).create(vals_list)

    def write(self, vals):
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
                        raise ValidationError(_('يمكن أن يكون هناك منتج عينات واحد فقط في النظام.\nمنتج العينات الحالي هو: %s\nيرجى إلغاء تحديد منتج العينات الحالي أولاً.') % existing_sample.name)

        if 'name' in vals or 'is_sample_product' in vals:
            for rec in self:
                will_be_sample = vals.get('is_sample_product', rec.is_sample_product)
                if will_be_sample:
                    new_name = vals.get('name', rec.name)
                    vals.setdefault('name', self._format_sample_name(new_name))

        if vals.get('is_sample_product'):
            vals['tracking'] = 'serial'
            vals['related_sample_product_id'] = False
        elif 'is_sample_product' in vals and not vals['is_sample_product']:
            for product in self:
                if product.is_sample_product and product.tracking == 'serial':
                    vals['tracking'] = 'none'

        return super(ProductTemplate, self).write(vals)

    @api.constrains('name', 'is_sample_product')
    def _check_sample_name_has_dash(self):
        """تأكد من أن اسم منتج العينات يحتوي على " - """ 
        for rec in self.filtered(lambda r: r.is_sample_product):
            if ' - ' not in rec.name:
                raise ValidationError(_('يجب أن يحتوي اسم منتج العينات على " - " قبل آخر كلمة، مثال: "العينات المستلمة - طابوق".'))

    @api.constrains('is_sample_product', 'hole_count')
    def _check_hole_count_required(self):
        for rec in self:
            if rec.is_sample_product and rec.hole_count <= 0:
                raise ValidationError(_('عدد الفتحات يجب أن يكون أكبر من الصفر للمنتج المصنف كمنتج عينات.'))


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    related_sample_product_id = fields.Many2one(
        related='product_tmpl_id.related_sample_product_id',
        string='منتج العينات المرتبط',
        help='اختر منتج العينات الذي سيتم استخدامه مع هذا المنتج',
        readonly=False,
        store=True
    )
    
    sample_info = fields.Char(
        related='product_tmpl_id.sample_info',
        string='معلومات العينة',
        readonly=True
    )
    
    test_template_ids = fields.Many2many(
        related='product_tmpl_id.test_template_ids',
        string='قوالب الفحص المتاحة',
        readonly=False
    )
    
    default_test_template_ids = fields.Many2many(
        related='product_tmpl_id.default_test_template_ids',
        string='قوالب الفحص الافتراضية',
        readonly=False
    )

    def action_view_test_templates(self):
        """Delegate to the template method so أن الزر يعمل في نموذج product.product أيضاً"""
        self.ensure_one()
        return self.product_tmpl_id.action_view_test_templates()
# -*- coding: utf-8 -*-
import ast
import logging
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SampleProductConfig(models.TransientModel):
    _name = 'sample.product.config'
    _description = 'إعداد منتجات العينات'
    _rec_name = 'sample_product_id'

    config_settings_id = fields.Many2one(
        'res.config.settings',
        string='إعدادات التكوين',
        ondelete='cascade',
        index=True
    )
    sample_product_id = fields.Many2one(
        'product.template',
        string='منتج العينات',
        domain=[('is_sample_product', '=', True)],
        required=True,
        index=True
    )
    samples_per_unit = fields.Integer(
        string='العينة الواحدة تساوي',
        required=True,
        help='عدد العينات التي تمثل وحدة واحدة لهذا المنتج'
    )
    
    currency_id = fields.Many2one(
        related='sample_product_id.currency_id',
        string='العملة',
        readonly=True,
        store=True
    )
    fixed_price = fields.Monetary(
        string='السعر الثابت',
        currency_field='currency_id',
        help='قيمة السعر الثابت لهذا المنتج عند احتساب العينات'
    )

    _sql_constraints = [
        ('positive_samples_per_unit', 'CHECK(samples_per_unit > 0)', 
         'عدد العينات لكل وحدة يجب أن يكون أكبر من صفر'),
        ('positive_fixed_price', 'CHECK(fixed_price >= 0)', 
         'السعر الثابت يجب أن يكون أكبر من أو يساوي صفر'),
        ('unique_sample_product_config', 'UNIQUE(config_settings_id, sample_product_id)', 
         'لا يمكن تكرار منتج العينات في نفس إعدادات التكوين')
    ]

    @api.constrains('samples_per_unit', 'fixed_price')
    def _check_positive_values(self):
        """التحقق من أن القيم موجبة"""
        for rec in self:
            if rec.samples_per_unit <= 0:
                raise ValidationError(_('عدد العينات لكل وحدة يجب أن يكون أكبر من صفر'))
            if rec.fixed_price < 0:
                raise ValidationError(_('السعر الثابت يجب أن يكون أكبر من أو يساوي صفر'))


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_advanced_samples = fields.Boolean(
        string='تمكين العينات المتقدمة',
        help='تفعيل النظام المتقدم للعينات مع المجموعات والرموز الحقلية',
        config_parameter='appointment_products.enable_advanced_samples'
    )
    
    auto_generate_field_codes = fields.Boolean(
        string='توليد رموز حقلية تلقائياً',
        help='توليد رموز حقلية تلقائياً عند إنشاء مجموعات العينات',
        config_parameter='appointment_products.auto_generate_field_codes'
    )
    
    link_samples_to_trucks = fields.Boolean(
        string='ربط العينات بالسيارات',
        help='ربط العينات بأرقام السيارات تلقائياً',
        config_parameter='appointment_products.link_samples_to_trucks'
    )
    
    samples_per_unit = fields.Integer(
        string='العينة الواحدة تساوي (عام)',
        default=50000,
        help='عدد العينات التي تمثل وحدة واحدة في الكمية (إعداد عام)',
        config_parameter='appointment_products.samples_per_unit'
    )
    
    sample_product_configs = fields.One2many(
        'sample.product.config',
        'config_settings_id',
        string='إعدادات منتجات العينات'
    )


    
    approval_manager_ids = fields.Many2many(
        'res.users',
        string='مديري الموافقة',
        help='المستخدمون المسؤولون عن الموافقة على العينات'
    )
    
    auto_generate_lab_code = fields.Boolean(
        string='تمكين الترقيم التلقائي للرمز المختبري',
        config_parameter='appointment_products.auto_generate_lab_code'
    )

    allow_lab_code_duplicates = fields.Boolean(
        string='السماح بتكرار الرمز المختبري',
        config_parameter='appointment_products.allow_lab_code_duplicates'
    )
    
    use_lab_code_as_barcode = fields.Boolean(
        string='استخدام الرمز المختبري كباركود في البطاقات',
        config_parameter='appointment_products.use_lab_code_as_barcode'
    )
    
    use_qr_code_labels = fields.Boolean(
        string='استخدام QR Code بدلاً من الباركود في البطاقات',
        config_parameter='appointment_products.use_qr_code_labels'
    )
    
    prevent_edit_lab_code = fields.Boolean(
        string='منع تعديل الرمز المختبري بعد إنشائه',
        help='عند التفعيل، لا يُسمح للمستخدمين بتعديل الحقل "الرمز المختبري" بعد أن يتم إنشاؤه لأول مرة.',
        config_parameter='appointment_products.prevent_edit_lab_code'
    )
    
    prevent_duplicate_sample_product = fields.Boolean(
        string='منع تكرار منتج العينات',
        help='عند التفعيل، لا يمكن تعيين أكثر من منتج واحد كمنتج عينات في نفس الوقت.',
        config_parameter='appointment_products.prevent_duplicate_sample_product'
    )
    
    auto_field_code_on_creation = fields.Boolean(
        string='توليد الرمز الحقلي عند إنشاء السجل',
        help='عند التفعيل، سيتم إنشاء الرمز الحقلي (Lot/Serial) تلقائياً عند إنشاء السجل مباشرة.',
        config_parameter='appointment_products.auto_field_code_on_creation'
    )

    apply_discount_incomplete_samples = fields.Boolean(
        string='تطبيق خصم على العينات غير المكتملة',
        help='عند التفعيل، إذا كانت الكمية الفعلية من العينات أقل من الكمية المفترضة لكل وحدة، يطبّق النظام خصماً نسبياً على سطر عرض السعر.',
        config_parameter='appointment_products.apply_discount_incomplete_samples'
    )

    max_image_size_mb = fields.Integer(
        string='الحد الأقصى لحجم الصورة (ميجابايت)',
        default=10,
        help='الحد الأقصى المسموح به لحجم كل صورة مرفقة. اترك القيمة صفر لتعطيل التحقق.',
        config_parameter='appointment_products.max_image_size_mb'
    )

    @api.onchange('prevent_duplicate_sample_product')
    def _onchange_prevent_duplicate_sample_product(self):
        """عند تفعيل منع التكرار، مسح إعدادات منتجات العينات المتعددة"""
        if self.prevent_duplicate_sample_product:
            self.sample_product_configs = [(5, 0, 0)]

    @api.model
    def default_get(self, fields_list):
        """تحميل إعدادات منتجات العينات الحالية"""
        res = super().default_get(fields_list)
        
        if 'sample_product_configs' in fields_list:
            sample_products = self.env['product.template'].search([('is_sample_product', '=', True)])
            configs = []
            
            for product in sample_products:
                param_key = f'appointment_products.samples_per_unit_{product.id}'
                saved_value = self.env['ir.config_parameter'].sudo().get_param(param_key)
                param_key_price = f'appointment_products.fixed_price_{product.id}'
                saved_price = self.env['ir.config_parameter'].sudo().get_param(param_key_price)
                
                configs.append((0, 0, {
                    'sample_product_id': product.id,
                    'samples_per_unit': int(saved_value) if saved_value else False,
                    'fixed_price': float(saved_price) if saved_price else 0.0
                }))
            
            res['sample_product_configs'] = configs
        
        return res
    
    @api.model
    def get_values(self):
        """تحميل القيم من المعاملات"""
        try:
            res = super(ResConfigSettings, self).get_values()

            approval_manager_ids = self.env['ir.config_parameter'].sudo().get_param(
                'appointment_products.approval_manager_ids', '[]'
            )
            
            manager_ids = []
            if approval_manager_ids and approval_manager_ids != 'False':
                try:
                    result = ast.literal_eval(approval_manager_ids)
                    if isinstance(result, (list, tuple)):
                        manager_ids = [int(x) for x in result if str(x).isdigit()]
                    elif isinstance(result, (int, str)) and str(result).isdigit():
                        manager_ids = [int(result)]
                except (ValueError, SyntaxError, TypeError):
                    try:
                        if ',' in approval_manager_ids:
                            manager_ids = [int(x.strip()) for x in approval_manager_ids.split(',') if x.strip().isdigit()]
                        elif approval_manager_ids.strip().isdigit():
                            manager_ids = [int(approval_manager_ids.strip())]
                    except Exception as e:
                        _logger.warning("خطأ في تحليل معرفات مديري الموافقة: %s", str(e))
            
            res['approval_manager_ids'] = [(6, 0, manager_ids)]
            return res
            
        except Exception as e:
            _logger.error("خطأ في تحميل إعدادات التكوين: %s", str(e))
            return super(ResConfigSettings, self).get_values()

    def set_values(self):
        """حفظ القيم في المعاملات"""
        try:
            super(ResConfigSettings, self).set_values()

            self.env['ir.config_parameter'].sudo().set_param(
                'appointment_products.approval_manager_ids',
                str(self.approval_manager_ids.ids)
            )
            
            for config in self.sample_product_configs:
                if config.sample_product_id:
                    param_key = f'appointment_products.samples_per_unit_{config.sample_product_id.id}'
                    self.env['ir.config_parameter'].sudo().set_param(param_key, str(config.samples_per_unit))
                    
                    param_key_price = f'appointment_products.fixed_price_{config.sample_product_id.id}'
                    self.env['ir.config_parameter'].sudo().set_param(param_key_price, str(config.fixed_price))
            
            _logger.info("تم حفظ إعدادات التكوين بنجاح")
            
        except Exception as e:
            _logger.error("خطأ في حفظ إعدادات التكوين: %s", str(e))
            raise UserError(_("فشل في حفظ الإعدادات: %s") % str(e))
        

        for config in self.sample_product_configs:
            if config.sample_product_id:
                if config.samples_per_unit:
                    param_key = f'appointment_products.samples_per_unit_{config.sample_product_id.id}'
                    self.env['ir.config_parameter'].sudo().set_param(param_key, str(config.samples_per_unit))

                param_price_key = f'appointment_products.fixed_price_{config.sample_product_id.id}'
                self.env['ir.config_parameter'].sudo().set_param(param_price_key, str(config.fixed_price or 0.0)) 
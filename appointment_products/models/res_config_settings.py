# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    samples_per_unit = fields.Integer(
        string='العينة الواحدة تساوي',
        default=50000,
        help='عدد العينات التي تمثل وحدة واحدة في الكمية',
        config_parameter='appointment_products.samples_per_unit'
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
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        approval_manager_ids = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.approval_manager_ids', '[]'
        )
        
        manager_ids = []
        if approval_manager_ids and approval_manager_ids != 'False':
            try:
                import ast
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
                except:
                    pass
        
        res['approval_manager_ids'] = [(6, 0, manager_ids)]
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()

        self.env['ir.config_parameter'].sudo().set_param(
            'appointment_products.approval_manager_ids',
            str(self.approval_manager_ids.ids)
        ) 
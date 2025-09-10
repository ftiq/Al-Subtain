# -*- coding: utf-8 -*-
import json
from odoo import fields, models, api, _


class ProductSubtypeTestPlanWizard(models.TransientModel):
    """نافذة منبثقة لتحرير خطط فحص الأنواع الفرعية للمنتج"""
    _name = 'product.subtype.test.plan.wizard'
    _description = 'معالج خطط فحص الأنواع الفرعية للمنتج'
    
    product_id = fields.Many2one(
        'product.template',
        string='المنتج',
        required=True
    )
    
    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع العينة',
        required=True
    )
    
    line_ids = fields.One2many(
        'product.subtype.test.plan.wizard.line',
        'wizard_id',
        string='سطور خطط الفحص'
    )
    
    @api.model
    def default_get(self, fields_list):
        """تعيين القيم الافتراضية وإنشاء السطور للأنواع الفرعية"""
        result = super().default_get(fields_list)
        
        if 'product_id' in result and 'sample_type_id' in result:
            product = self.env['product.template'].browse(result['product_id'])
            sample_type = self.env['lab.sample.type'].browse(result['sample_type_id'])
            
            if product.exists() and sample_type.exists():

                existing_plans = {}
                if product.subtype_test_plans_json:
                    try:
                        existing_plans = json.loads(product.subtype_test_plans_json)
                    except (json.JSONDecodeError, TypeError):
                        existing_plans = {}
                

                lines = []
                for subtype in sample_type.subtype_ids.sorted('sequence'):
                    test_plan_id = existing_plans.get(str(subtype.id))
                    lines.append((0, 0, {
                        'subtype_id': subtype.id,
                        'test_flow_template_id': test_plan_id if test_plan_id else False,
                    }))
                
                result['line_ids'] = lines
        
        return result
    
    def action_save(self):
        """حفظ خطط الفحص في المنتج"""
        self.ensure_one()
        

        plans_data = {}
        for line in self.line_ids:
            if line.test_flow_template_id:
                plans_data[str(line.subtype_id.id)] = line.test_flow_template_id.id
        

        self.product_id.write({
            'subtype_test_plans_json': json.dumps(plans_data) if plans_data else False
        })
        
        return {'type': 'ir.actions.act_window_close'}


class ProductSubtypeTestPlanWizardLine(models.TransientModel):
    """سطر في معالج خطط فحص الأنواع الفرعية"""
    _name = 'product.subtype.test.plan.wizard.line'
    _description = 'سطر معالج خطط فحص الأنواع الفرعية'
    
    wizard_id = fields.Many2one(
        'product.subtype.test.plan.wizard',
        string='المعالج',
        required=True,
        ondelete='cascade'
    )
    
    subtype_id = fields.Many2one(
        'lab.sample.subtype',
        string='النوع الفرعي',
        required=True
    )
    
    subtype_name = fields.Char(
        related='subtype_id.name',
        string='اسم النوع الفرعي',
        readonly=True
    )
    
    subtype_code = fields.Char(
        related='subtype_id.code',
        string='رمز النوع الفرعي',
        readonly=True
    )
    
    test_flow_template_id = fields.Many2one(
        'lab.test.flow.template',
        string='خطة الفحص',
        help='اختر خطة الفحص لهذا النوع الفرعي'
    )
    
    @api.onchange('subtype_id')
    def _onchange_subtype_id(self):
        """تحديث domain خطة الفحص حسب نوع العينة"""
        if self.subtype_id and self.wizard_id.sample_type_id:
            return {
                'domain': {
                    'test_flow_template_id': [
                        ('sample_type_id', '=', self.wizard_id.sample_type_id.id)
                    ]
                }
            }
        return {'domain': {'test_flow_template_id': []}}

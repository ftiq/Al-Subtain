# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import ast
import operator
import math
import logging
import json

_logger = logging.getLogger(__name__)


class LabComputationEngine(models.TransientModel):
    """محرك الحسابات التلقائية للمعايير المحسوبة"""
    _name = 'lab.computation.engine'
    _description = 'محرك الحسابات التلقائية'

    @api.model
    def execute_formula(self, formula, variables, series_data=None):
        """
        تنفيذ معادلة حساب آمنة
        
        Args:
            formula (str): المعادلة المكتوبة بـ Python
            variables (dict): متغيرات الحساب
            series_data (dict): بيانات السلاسل للحسابات المتقدمة
        
        Returns:
            float: نتيجة الحساب
        """
        if not formula or not isinstance(formula, str):
            return 0.0
            
        try:
            formula = formula.strip()
            if not formula:
                return 0.0
            

            if not isinstance(variables, dict):
                variables = {}
            

            safe_dict = self._create_safe_environment(series_data or {})
            safe_dict.update(variables)
            

            if 'result =' in formula:
                exec(formula, safe_dict)
                result = safe_dict.get('result', 0)
            else:
                result = eval(formula, safe_dict)
            

            if result is None:
                return 0.0
            if isinstance(result, (int, float)):
                return float(result)
            else:
                _logger.warning("نتيجة المعادلة ليست رقماً: %s", type(result))
                return 0.0
                
        except ZeroDivisionError:
            _logger.error("خطأ قسمة على صفر في المعادلة: %s", formula)
            raise UserError(_('خطأ قسمة على صفر في المعادلة'))
        except ValueError as e:
            _logger.error("خطأ في القيمة في المعادلة %s: %s", formula, str(e))
            raise UserError(_('خطأ في القيمة في المعادلة: %s') % str(e))
        except Exception as e:
            _logger.error("خطأ في تنفيذ المعادلة %s: %s", formula, str(e))
            raise UserError(_('خطأ في حساب المعادلة: %s') % str(e))
    
    @api.model
    def _create_safe_environment(self, series_data):
        """إنشاء بيئة آمنة لتنفيذ المعادلات مع دوال متقدمة

        Args:
            series_data (dict): {
                'CODE': [values across العينات]
            }
        """
        import statistics
        
        def avg(values):
            if isinstance(values, (list, tuple)):
                return sum(values) / len(values) if values else 0
            return values
        
        def stdev(values):
            if isinstance(values, (list, tuple)) and len(values) > 1:
                return statistics.stdev(values)
            return 0
        
        def median(values):
            if isinstance(values, (list, tuple)) and values:
                return statistics.median(values)
            return values
        
        def mode(values):
            if isinstance(values, (list, tuple)) and values:
                try:
                    return statistics.mode(values)
                except statistics.StatisticsError:
                    return values[0] 
            return values
        
        def nthroot(x, n):
            return pow(x, 1.0/n) if n != 0 else 0
        
        def abslist(values):
            if isinstance(values, (list, tuple)):
                return [abs(x) for x in values]
            return abs(values)
        
        def roundup(x, precision=0):
            multiplier = 10 ** precision
            return math.ceil(x * multiplier) / multiplier
        
        def rounddown(x, precision=0):
            multiplier = 10 ** precision
            return math.floor(x * multiplier) / multiplier
        
        def degrees(radians):
            return math.degrees(radians)
        
        def radians(degrees):
            return math.radians(degrees)
        
        def clamp(value, min_val, max_val):
            return max(min_val, min(value, max_val))
        
        def percentage(part, total):
            return (part / total * 100) if total != 0 else 0
        
        def weighted_avg(values, weights):
            if isinstance(values, (list, tuple)) and isinstance(weights, (list, tuple)):
                if len(values) == len(weights):
                    total_weight = sum(weights)
                    if total_weight != 0:
                        return sum(v * w for v, w in zip(values, weights)) / total_weight
            return 0

        def _get_series(code):
            return series_data.get(code) or []

        def avg_series(code):
            vals = _get_series(code)
            return sum(vals) / len(vals) if vals else 0

        def max_series(code):
            vals = _get_series(code)
            return max(vals) if vals else 0

        def min_series(code):
            vals = _get_series(code)
            return min(vals) if vals else 0
        
        return {
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'pow': pow,
            'len': len,
            
            'avg': avg,
            'mean': avg,
            'median': median,
            'mode': mode,
            'stdev': stdev,
            'variance': lambda x: stdev(x) ** 2 if isinstance(x, (list, tuple)) else 0,
            'count': len,
            
            'sqrt': math.sqrt,
            'nthroot': nthroot,
            'cbrt': lambda x: nthroot(x, 3),
            'abslist': abslist,
            
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'sinh': math.sinh,
            'cosh': math.cosh,
            'tanh': math.tanh,
            'asinh': math.asinh,
            'acosh': math.acosh,
            'atanh': math.atanh,
            
            'log': math.log,
            'log10': math.log10,
            'log2': math.log2,
            'ln': math.log,
            'exp': math.exp,
            
            'ceil': math.ceil,
            'floor': math.floor,
            'roundup': roundup,
            'rounddown': rounddown,
            'trunc': math.trunc,
            
            'degrees': degrees,
            'radians': radians,
            
            'clamp': clamp,
            'percentage': percentage,
            'weighted_avg': weighted_avg,

            'avg_series': avg_series,
            'max_series': max_series,
            'min_series': min_series,
            
            'pi': math.pi,
            'e': math.e,
            'tau': math.tau,
            'inf': math.inf,
            
            'True': True,
            'False': False,
            'None': None,
            
            'math': math,
            
            '__builtins__': {},
            '__import__': None,
            'eval': None,
            'exec': None,
            'open': None,
            'input': None,
            'raw_input': None,
        }
    
    @api.model
    def get_function_suggestions(self, partial_input='', limit=20):
        """إرجاع قائمة مقترحات لأسماء الدوال/الثوابت بناءً على المدخل الجزئي.

        تستند القائمة إلى المفاتيح المتاحة في البيئة الآمنة للمحرك. يتم استبعاد
        أي مفاتيح داخلية أو محجوزة (مثل __builtins__).

        Args:
            partial_input (str): الجزء الذي أدخله المستخدم من اسم الدالة.
            limit (int): أقصى عدد من المقترحات المراد إرجاعها.

        Returns:
            list[str]: قائمة أسماء مقترحة مُرتبة أبجديًا.
        """
        try:
            safe_keys = self._create_safe_environment({}).keys()
            excluded = {
                '__builtins__', '__import__', 'eval', 'exec', 'open',
                'input', 'raw_input', 'math', 'True', 'False', 'None'
            }

            partial_lower = (partial_input or '').lower()
            suggestions = [
                key for key in safe_keys
                if key not in excluded and key.lower().startswith(partial_lower)
            ]

            return sorted(suggestions)[:limit]
        except Exception as e:
            _logger.error(_("Error fetching function suggestions: %s"), str(e))
            return []
    
    @api.model
    def validate_formula(self, formula):
        """التحقق من صحة المعادلة قبل الحفظ"""
        try:
            if 'result =' in formula:
                ast.parse(formula)
            else:
                ast.parse(formula, mode='eval')
            return True, ''
        except SyntaxError as e:
            return False, f'خطأ في صيغة المعادلة: {str(e)}'
        except Exception as e:
            return False, f'خطأ في المعادلة: {str(e)}'
    
    @api.model
    def get_formula_examples(self):
        """إرجاع أمثلة على المعادلات الشائعة"""
        return {
            'concrete_compression': {
                'name': 'مقاومة الضغط للخرسانة',
                'formula': 'result = load / area',
                'description': 'الحمل ÷ المساحة',
                'variables': ['load', 'area']
            },
            'absorption_rate': {
                'name': 'نسبة الامتصاص',
                'formula': 'result = ((wet_weight - dry_weight) / dry_weight) * 100',
                'description': '((الوزن الرطب - الوزن الجاف) ÷ الوزن الجاف) × 100',
                'variables': ['wet_weight', 'dry_weight']
            },
            'density': {
                'name': 'الكثافة',
                'formula': 'result = mass / volume',
                'description': 'الكتلة ÷ الحجم',
                'variables': ['mass', 'volume']
            },
            'void_ratio': {
                'name': 'معامل الفراغات',
                'formula': 'result = (total_volume - solid_volume) / solid_volume',
                'description': '(الحجم الكلي - حجم المواد الصلبة) ÷ حجم المواد الصلبة',
                'variables': ['total_volume', 'solid_volume']
            },
            'modulus_elasticity': {
                'name': 'معامل المرونة',
                'formula': 'result = stress / strain',
                'description': 'الإجهاد ÷ الانفعال',
                'variables': ['stress', 'strain']
            },
            'bearing_capacity': {
                'name': 'قدرة التحمل',
                'formula': 'result = load / area * safety_factor',
                'description': 'الحمل ÷ المساحة × معامل الأمان',
                'variables': ['load', 'area', 'safety_factor']
            },
            'penetration_resistance': {
                'name': 'مقاومة الاختراق',
                'formula': 'result = penetration_load / penetration_area',
                'description': 'حمل الاختراق ÷ مساحة الاختراق',
                'variables': ['penetration_load', 'penetration_area']
            },
            'settlement_calculation': {
                'name': 'حساب الهبوط',
                'formula': 'result = (load * depth) / (elastic_modulus * area)',
                'description': '(الحمل × العمق) ÷ (معامل المرونة × المساحة)',
                'variables': ['load', 'depth', 'elastic_modulus', 'area']
            },
            'slump_flow': {
                'name': 'انتشار الخرسانة',
                'formula': 'result = (d1 + d2) / 2',
                'description': '(القطر الأول + القطر الثاني) ÷ 2',
                'variables': ['d1', 'd2']
            },
            'fineness_modulus': {
                'name': 'معامل النعومة',
                'formula': 'result = sum([sieve_retained_4_75, sieve_retained_2_36, sieve_retained_1_18, sieve_retained_0_6, sieve_retained_0_3, sieve_retained_0_15]) / 100',
                'description': 'مجموع النسب المتراكمة المتبقية على المناخل ÷ 100',
                'variables': ['sieve_retained_4_75', 'sieve_retained_2_36', 'sieve_retained_1_18', 'sieve_retained_0_6', 'sieve_retained_0_3', 'sieve_retained_0_15']
            }
        }
    
    @api.model
    def get_standard_formulas_by_material(self, material_type):
        """إرجاع المعادلات القياسية حسب نوع المادة"""
        all_formulas = self.get_formula_examples()
        
        material_formulas = {
            'concrete': ['concrete_compression', 'absorption_rate', 'density', 'slump_flow'],
            'steel': ['modulus_elasticity', 'density'],
            'masonry': ['concrete_compression', 'absorption_rate', 'density'],
            'soil': ['bearing_capacity', 'void_ratio', 'density', 'penetration_resistance', 'settlement_calculation'],
            'aggregate': ['fineness_modulus', 'density', 'absorption_rate'],
            'asphalt': ['density', 'penetration_resistance'],
        }
        
        if material_type in material_formulas:
            return {key: all_formulas[key] for key in material_formulas[material_type] if key in all_formulas}
        
        return all_formulas
    
    @api.model
    def test_formula(self, formula, test_variables=None, sample_id=None):
        """اختبار المعادلة مع قيم تجريبية"""
        if not test_variables:
            test_variables = {
                'load': 100,
                'area': 10,
                'wet_weight': 110,
                'dry_weight': 100,
                'mass': 50,
                'volume': 25,
                'stress': 200,
                'strain': 0.01,
                'safety_factor': 3,
                'depth': 5,
                'elastic_modulus': 20000,
                'd1': 150,
                'd2': 160
            }
        
        try:

            result = self.execute_formula(formula, test_variables)
            
            response = {
                'success': True,
                'result': result,
                'message': f'نتيجة الاختبار: {result}'
            }
            
            return response
            
        except Exception as e:
            return {
                'success': False,
                'result': 0,
                'message': f'خطأ في الاختبار: {str(e)}'
            }


class LabTestCriterionInherit(models.Model):
    """إضافة وظائف الحساب لنموذج المعايير"""
    _inherit = 'lab.test.criterion'
    
    def action_test_formula(self):
        """اختبار معادلة الحساب"""
        if not self.computation_formula:
            raise UserError(_('لا توجد معادلة حساب لاختبارها!'))
        
        computation_engine = self.env['lab.computation.engine']
        test_result = computation_engine.test_formula(self.computation_formula)
        
        if test_result['success']:
            message = _('اختبار المعادلة نجح!\nالنتيجة: %s') % test_result['result']
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('نجح الاختبار'),
                    'message': message,
                    'type': 'success'
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('فشل الاختبار'),
                    'message': test_result['message'],
                    'type': 'danger'
                }
            }
    
    def action_show_formula_examples(self):
        """عرض أمثلة المعادلات"""
        computation_engine = self.env['lab.computation.engine']
        material_type = self.template_id.industry_type or 'concrete'
        formulas = computation_engine.get_standard_formulas_by_material(material_type)
        
        wizard = self.env['lab.formula.examples.wizard'].create({
            'criterion_id': self.id,
            'material_type': material_type,
            'formulas_json': json.dumps(formulas, ensure_ascii=False)
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('أمثلة المعادلات'),
            'res_model': 'lab.formula.examples.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new'
        }
    
    @api.constrains('computation_formula')
    def _check_formula_syntax(self):
        """التحقق من صحة صيغة المعادلة"""
        for record in self:
            if record.computation_formula and record.is_computed_field:
                computation_engine = self.env['lab.computation.engine']
                is_valid, error_message = computation_engine.validate_formula(record.computation_formula)
                
                if not is_valid:
                    raise ValidationError(_('خطأ في معادلة الحساب: %s') % error_message)


class LabFormulaExamplesWizard(models.TransientModel):
    """معالج عرض أمثلة المعادلات"""
    _name = 'lab.formula.examples.wizard'
    _description = 'معالج أمثلة المعادلات'
    
    criterion_id = fields.Many2one('lab.test.criterion', string='المعيار')
    material_type = fields.Char(string='نوع المادة')
    formulas_json = fields.Text(string='المعادلات')
    selected_formula_key = fields.Selection([], string='المعادلة المختارة')
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'formulas_json' in res and res['formulas_json']:
            try:
                formulas = json.loads(res['formulas_json'])
                formula_options = [(key, value['name']) for key, value in formulas.items()]
                self._fields['selected_formula_key'].selection = formula_options
            except:
                pass
        return res
    
    def action_apply_formula(self):
        """تطبيق المعادلة المختارة"""
        if not self.selected_formula_key or not self.formulas_json:
            raise UserError(_('يجب اختيار معادلة أولاً!'))
        
        try:
            formulas = json.loads(self.formulas_json)
            selected_formula = formulas[self.selected_formula_key]
            
            self.criterion_id.write({
                'computation_formula': selected_formula['formula'],
                'help_text': selected_formula['description'],
                'is_computed_field': True,
                'is_input_field': False
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تم تطبيق المعادلة'),
                    'message': _('تم تطبيق معادلة: %s') % selected_formula['name'],
                    'type': 'success'
                }
            }
            
        except Exception as e:
            raise UserError(_('خطأ في تطبيق المعادلة: %s') % str(e)) 
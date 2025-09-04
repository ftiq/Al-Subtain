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
    def execute_formula(self, formula, variables, series_data=None, context_result_set=None):
        """
        تنفيذ معادلة حساب آمنة
        
        Args:
            formula (str): المعادلة المكتوبة بـ Python
            variables (dict): متغيرات الحساب
            series_data (dict): بيانات السلاسل للحسابات المتقدمة
            context_result_set (recordset): مجموعة النتائج الحالية (للوصول لبيانات العينة)
        
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
            

            safe_dict = self._create_safe_environment(series_data or {}, context_result_set)
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
    def _create_safe_environment(self, series_data, context_result_set=None):
        """
        إنشاء بيئة آمنة لتنفيذ المعادلات
        
        Args:
            series_data (dict): {
                'CODE': [values across العينات]
            }
            context_result_set (recordset): مجموعة النتائج الحالية
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
            
        def get_factor():
            """الحصول على قيمة Factor من مجموعة النتائج الحالية
            Returns:
                int: قيمة Factor (عدد الأيام المتجاوزة)
            """
            if not context_result_set:
                return 0
            return getattr(context_result_set, 'factor', 0)
        
        def multiply_by_factor(value):
            """تصحيح القيمة بناءً على Factor (القسمة للحصول على القوة الحقيقية عند 28 يوم)
            Args:
                value: القيمة المراد تصحيحها
            Returns:
                float: القيمة مصححة بناءً على Factor أو القيمة الأصلية إذا كان Factor = 0
            """
            factor_value = get_factor()
            if factor_value > 0:  # فقط إذا كان هناك تأخير
                # حساب عامل التصحيح (5% لكل يوم تأخير)
                correction_factor = 1.0 + (factor_value * 0.05)
                corrected_value = value / correction_factor
                _logger.info(f"multiply_by_factor: Factor = {factor_value}, القيمة الأصلية = {value}, عامل التصحيح = {correction_factor}, القيمة المصححة = {corrected_value}")
                return corrected_value
            return value
        
        def sample_avg_across_sets(code):
            """حساب متوسط القيم عبر مجموعات النتائج المختلفة
            المنطق:
            1. إذا طلب COMP_STRENGTH_CONCRETE: يبحث عن القراءات الأساسية أولاً
            2. إذا لم توجد قراءات أساسية: يبحث عن AVG_COMP_STRENGTH_CONCRETE
            3. إذا طلب معيار آخر: يبحث عنه مباشرة
            4. **جديد**: للمتوسط الإجمالي يتجاهل 7 أيام والاحتياط ويحسب فقط من 28 يوم
            
            TODO: يمكن استخدام الأدوات المشتركة:
            return self.env['lab.data.utils'].get_cross_sets_average(
                context_result_set.sample_id, code, age_days='28', 
                primary_fallback='AVG_COMP_STRENGTH_CONCRETE' if code == 'COMP_STRENGTH_CONCRETE' else None
            )
            """
            if not context_result_set or not context_result_set.sample_id:
                _logger.warning(f"sample_avg_across_sets: No context_result_set or sample_id for {code}")
                return 0
                
            sample = context_result_set.sample_id
            _logger.info(f"sample_avg_across_sets: Looking for {code} in sample {sample.name}")
            

            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG'
            )
            
            if code in ['COMP_STRENGTH_CONCRETE', 'AVG_COMP_STRENGTH_CONCRETE'] and context_result_set.template_id.code == 'CONCRETE_OVERALL_AVG':
                all_result_sets = all_result_sets.filtered(
                    lambda rs: rs.concrete_age_days == '28'
                )
                _logger.info(f"sample_avg_across_sets: تم تفلتر مجموعات 28 يوم فقط. عدد المجموعات: {len(all_result_sets)}")
            else:
                _logger.info(f"sample_avg_across_sets: عدد عام للمجموعات: {len(all_result_sets)}")
            

            values = []
            primary_code = code
            fallback_code = None
            

            if code == 'COMP_STRENGTH_CONCRETE':
                fallback_code = 'AVG_COMP_STRENGTH_CONCRETE'
                _logger.info(f"sample_avg_across_sets: Will try {primary_code} first, then fallback to {fallback_code}")
            
            for result_set in all_result_sets:
                _logger.info(f"sample_avg_across_sets: Checking result set {result_set.name} (template: {result_set.template_id.code})")
                
                result_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == primary_code
                )
                _logger.info(f"sample_avg_across_sets: Found {len(result_lines)} lines with criterion {primary_code} in {result_set.name}")
                

                for line in result_lines:
                    _logger.info(f"sample_avg_across_sets: Line {line.criterion_id.code} value_numeric: {line.value_numeric}")
                    if line.value_numeric and line.value_numeric > 0:
                        values.append(line.value_numeric)
                        _logger.info(f"sample_avg_across_sets: Added value {line.value_numeric} from {line.criterion_id.code}")
                    else:
                        try:
                            line._compute_value() 
                            if line.value_numeric and line.value_numeric > 0:
                                values.append(line.value_numeric)
                                _logger.info(f"sample_avg_across_sets: Added recomputed value {line.value_numeric} from {line.criterion_id.code}")
                        except Exception as e:
                            _logger.debug(f"sample_avg_across_sets: Failed to recompute {line.criterion_id.code}: {e}")
            
            if not values and fallback_code:
                _logger.info(f"sample_avg_across_sets: No values found for {primary_code}, trying fallback {fallback_code}")
                
                for result_set in all_result_sets:
                    result_lines = result_set.result_line_ids.filtered(
                        lambda line: line.criterion_id.code == fallback_code
                    )
                    _logger.info(f"sample_avg_across_sets: Found {len(result_lines)} fallback lines with {fallback_code} in {result_set.name}")
                    
                    for line in result_lines:
                        _logger.info(f"sample_avg_across_sets: Fallback line {line.criterion_id.code} value_numeric: {line.value_numeric}")
                        if line.value_numeric and line.value_numeric > 0:
                            values.append(line.value_numeric)
                            _logger.info(f"sample_avg_across_sets: Added fallback value {line.value_numeric} from {line.criterion_id.code}")
                        else:
                            try:
                                line._compute_value() 
                                if line.value_numeric and line.value_numeric > 0:
                                    values.append(line.value_numeric)
                                    _logger.info(f"sample_avg_across_sets: Added recomputed fallback value {line.value_numeric}")
                            except Exception as e:
                                _logger.debug(f"sample_avg_across_sets: Failed to recompute fallback {fallback_code}: {e}")
            
            _logger.info(f"sample_avg_across_sets: Final values for {code}: {values}")
            
            if values:
                avg_value = sum(values) / len(values)
                _logger.info(f"sample_avg_across_sets: Average for {code}: {avg_value} (from {len(values)} values)")
                return avg_value
            else:
                _logger.warning(f"sample_avg_across_sets: No valid values found for {code} or its fallback")
                return 0
        
        def sample_avg_consecutive_groups(code, group_size):
            """حساب متوسط المجموعات المتتابعة
            Args:
                code: رمز المعيار
                group_size: عدد المجموعات في كل متوسط (3 أو 4)
            Returns:
                float: متوسط أفضل مجموعات متتابعة
            """
            if not context_result_set or not context_result_set.sample_id:
                _logger.warning(f"sample_avg_consecutive_groups: No context for {code}")
                return 0
                
            sample = context_result_set.sample_id
            
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG' and rs.concrete_group_no
            ).sorted('concrete_group_no')
            
            result_sets_28d = all_result_sets.filtered(lambda rs: rs.concrete_age_days == '28')
            result_sets_28d = all_result_sets.filtered(lambda rs: rs.concrete_age_days == '28')
            
            if len(result_sets_28d) < group_size:
                _logger.warning(f"sample_avg_consecutive_groups: Not enough groups ({len(result_sets_28d)}) for size {group_size}")
                return 0
            
            group_averages = []
            for result_set in result_sets_28d:
                avg_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append(avg_lines[0].value_numeric)
            
            if len(group_averages) < group_size:
                _logger.warning(f"sample_avg_consecutive_groups: Not enough averages ({len(group_averages)}) for size {group_size}")
                return 0
            
            consecutive_averages = []
            for i in range(len(group_averages) - group_size + 1):
                consecutive_group = group_averages[i:i + group_size]
                consecutive_avg = sum(consecutive_group) / len(consecutive_group)
                consecutive_averages.append(consecutive_avg)
                _logger.debug(f"Consecutive groups {i+1}-{i+group_size}: {consecutive_avg:.2f}")
            
            best_avg = max(consecutive_averages) if consecutive_averages else 0
            _logger.debug(f"sample_avg_consecutive_groups: Best consecutive average: {best_avg}")
            return best_avg

        def sample_avg_last_groups(code, group_count):
            """حساب متوسط آخر مجموعات
            Args:
                code: رمز المعيار  
                group_count: عدد المجموعات الأخيرة
            Returns:
                float: متوسط آخر مجموعات
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG' and rs.concrete_group_no
            ).sorted('concrete_group_no')
            
            result_sets_28d = all_result_sets.filtered(lambda rs: rs.concrete_age_days == '28')
            
            if len(result_sets_28d) < group_count:
                return 0
            
            last_sets = result_sets_28d[-group_count:]
            
            group_averages = []
            for result_set in last_sets:
                avg_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append(avg_lines[0].value_numeric)
            
            return sum(group_averages) / len(group_averages) if group_averages else 0

        def check_individual_results_compliance(code, fc_prime, tolerance):
            """فحص مطابقة النتائج المنفردة
            Args:
                code: رمز المعيار
                fc_prime: مقاومة التصميم  
                tolerance: التسامح المسموح
            Returns:
                float: 1 إذا جميع النتائج مطابقة، 0 إذا كان هناك نتائج غير مطابقة
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            min_allowed = fc_prime - tolerance
            
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG'
            )
            
            non_compliant_count = 0
            total_count = 0
            
            for result_set in all_result_sets:
                individual_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == 'COMP_STRENGTH_CONCRETE'
                )
                for line in individual_lines:
                    if line.value_numeric is not None:
                        total_count += 1
                        if line.value_numeric < min_allowed:
                            non_compliant_count += 1
                            _logger.debug(f"Non-compliant result: {line.value_numeric} < {min_allowed}")
            
            _logger.debug(f"Individual compliance check: {non_compliant_count}/{total_count} non-compliant")
            return 1.0 if non_compliant_count == 0 else 0.0

        def sample_std_deviation(code):
            """حساب الانحراف المعياري للعينة
            Args:
                code: رمز المعيار
            Returns:
                float: الانحراف المعياري
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            
            all_values = []
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG'
            )
            
            for result_set in all_result_sets:
                lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == code
                )
                for line in lines:
                    if line.value_numeric is not None and line.value_numeric > 0:
                        all_values.append(line.value_numeric)
            
            if len(all_values) < 2:
                return 0
            
            mean_val = sum(all_values) / len(all_values)
            
            variance = sum((x - mean_val) ** 2 for x in all_values) / (len(all_values) - 1)
            std_dev = variance ** 0.5
            
            _logger.debug(f"Standard deviation for {code}: {std_dev:.2f} (n={len(all_values)})")
            return std_dev

        def sample_count_tested_groups(code):
            """عد المجموعات المفحوصة (فقط مجموعات 28 يوم)
            Args:
                code: رمز المعيار
            Returns:
                int: عدد مجموعات 28 يوم المفحوصة
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            
            tested_groups = sample.result_set_ids.filtered(
                lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                           rs.concrete_group_no and
                           rs.concrete_age_days == '28')
            )
            
            count = len(tested_groups)
            _logger.debug(f"Tested groups count (28 days only): {count}")
            return count
        
        def sample_avg_specific_groups(code, group_numbers):
            """حساب متوسط مجموعات محددة بأرقامها
            Args:
                code: رمز المعيار
                group_numbers: قائمة بأرقام المجموعات [2, 3, 4, 5]
            Returns:
                float: متوسط المجموعات المحددة
            """
            if not context_result_set or not context_result_set.sample_id:
                _logger.warning(f"sample_avg_specific_groups: No context for {code}")
                return 0
                
            sample = context_result_set.sample_id
            

            selected_groups = []
            for group_no in group_numbers:
                result_sets = sample.result_set_ids.filtered(
                    lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                               rs.concrete_group_no == group_no and 
                               rs.concrete_age_days == '28')
                )
                
                if result_sets:
                    result_set = result_sets[0]  
                    avg_lines = result_set.result_line_ids.filtered(
                        lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                    )
                    if avg_lines and avg_lines[0].value_numeric:
                        selected_groups.append(avg_lines[0].value_numeric)
                        _logger.info(f"Group {group_no}: {avg_lines[0].value_numeric}")
            
            if not selected_groups:
                _logger.warning(f"sample_avg_specific_groups: No groups found for numbers {group_numbers}")
                return 0
            
            result = sum(selected_groups) / len(selected_groups)
            _logger.info(f"Specific groups {group_numbers} average: {result:.2f}")
            return result

        def sample_min_group_average(code):
            """إيجاد أقل متوسط مجموعة
            Args:
                code: رمز المعيار
            Returns:
                float: أقل متوسط مجموعة
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            
            group_averages = []
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                           rs.concrete_group_no and rs.concrete_age_days == '28')
            )
            
            for result_set in all_result_sets:
                avg_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append(avg_lines[0].value_numeric)
            
            if not group_averages:
                return 0
            
            min_avg = min(group_averages)
            _logger.info(f"Minimum group average: {min_avg}")
            return min_avg

        def sample_max_group_average(code):
            """إيجاد أعلى متوسط مجموعة
            Args:
                code: رمز المعيار
            Returns:
                float: أعلى متوسط مجموعة
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            
            group_averages = []
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                           rs.concrete_group_no and rs.concrete_age_days == '28')
            )
            
            for result_set in all_result_sets:
                avg_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append(avg_lines[0].value_numeric)
            
            if not group_averages:
                return 0
            
            max_avg = max(group_averages)
            _logger.info(f"Maximum group average: {max_avg}")
            return max_avg

        def get_criterion_from_sample_tests(criterion_code):
            """جلب قيمة معيار من فحوصات أخرى في نفس العينة
            Args:
                criterion_code: رمز المعيار المطلوب جلبه (مثل AREA_A)
            Returns:
                float: قيمة المعيار إذا وجد، وإلا None
            """
            if not context_result_set or not context_result_set.sample_id:
                return None
                
            sample = context_result_set.sample_id
            

            current_sample_no = 1  
            if hasattr(context_result_set, 'result_line_ids') and context_result_set.result_line_ids:
                first_line = context_result_set.result_line_ids[0]
                if hasattr(first_line, 'sample_no') and first_line.sample_no:
                    current_sample_no = first_line.sample_no
            
            _logger.info(f"Searching for criterion {criterion_code} for sample {current_sample_no}")
            
            for result_set in sample.result_set_ids:
                if result_set.id == context_result_set.id:
                    continue
                    
                _logger.info(f"Checking result set: {result_set.template_id.name if result_set.template_id else 'Unknown'}")
                
                matching_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == criterion_code and 
                                line.sample_no == current_sample_no
                )
                
                if matching_lines and matching_lines[0].value_numeric is not None and matching_lines[0].value_numeric > 0:
                    _logger.info(f"Found {criterion_code} value: {matching_lines[0].value_numeric} for sample {current_sample_no}")
                    return matching_lines[0].value_numeric
                    
                summary_lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == criterion_code and 
                                (not hasattr(line, 'sample_no') or line.sample_no == 0 or 
                                 getattr(line.criterion_id, 'is_summary_field', False))
                )
                if summary_lines and summary_lines[0].value_numeric is not None and summary_lines[0].value_numeric > 0:
                    _logger.info(f"Found summary {criterion_code} value: {summary_lines[0].value_numeric}")
                    return summary_lines[0].value_numeric
            
            _logger.warning(f"Criterion {criterion_code} not found in sample tests")
            return None

        def calculate_uncertainty_stress_value(code):
            """حساب قيمة عدم التأكد في الإجهاد حسب ISO/IEC 17025
            Args:
                code: رمز المعيار
            Returns:
                float: قيمة عدم التأكد المحسوبة
            """
            if not context_result_set or not context_result_set.sample_id:
                return 0
                
            sample = context_result_set.sample_id
            

            all_values = []
            all_result_sets = sample.result_set_ids.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG'
            )
            
            for result_set in all_result_sets:
                lines = result_set.result_line_ids.filtered(
                    lambda line: line.criterion_id.code == code
                )
                for line in lines:
                    if line.value_numeric is not None and line.value_numeric > 0:
                        all_values.append(line.value_numeric)
            
            if len(all_values) < 3:  
                return 0
            
            mean_val = sum(all_values) / len(all_values)
            variance = sum((x - mean_val) ** 2 for x in all_values) / (len(all_values) - 1)
            std_dev = variance ** 0.5
            
            if mean_val > 0:
                k_factor = 2.0
                instrument_uncertainty = 0.5  
                instrument_uncertainty = 0.5  
                method_uncertainty = std_dev / (len(all_values) ** 0.5)
                

                combined_uncertainty = ((instrument_uncertainty ** 2) + (method_uncertainty ** 2)) ** 0.5
                expanded_uncertainty = k_factor * combined_uncertainty
                
                _logger.debug(f"Uncertainty calculation: mean={mean_val:.2f}, std_dev={std_dev:.2f}, expanded_uncertainty={expanded_uncertainty:.3f}")
                return round(expanded_uncertainty, 3)
            else:
                return 0
        
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
            'sample_avg_across_sets': sample_avg_across_sets,
            'sample_avg_consecutive_groups': sample_avg_consecutive_groups,
            'sample_avg_last_groups': sample_avg_last_groups,
            'check_individual_results_compliance': check_individual_results_compliance,
            'sample_std_deviation': sample_std_deviation,
            'sample_count_tested_groups': sample_count_tested_groups,
            'sample_avg_specific_groups': sample_avg_specific_groups,
            'sample_min_group_average': sample_min_group_average,
            'sample_max_group_average': sample_max_group_average,
            'get_criterion_from_sample_tests': get_criterion_from_sample_tests,
            'calculate_uncertainty_stress_value': calculate_uncertainty_stress_value,
            'get_factor': get_factor,
            'multiply_by_factor': multiply_by_factor,
            
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

            result = self.execute_formula(formula, test_variables, context_result_set=None)
            
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
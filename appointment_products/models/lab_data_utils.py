# -*- coding: utf-8 -*-
from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class LabDataUtils(models.AbstractModel):
    """مرافق مشتركة لاستخراج ومعالجة بيانات المختبر
    
    هذا النموذج المجرد يوفر دوال مساعدة مشتركة يمكن استخدامها في:
    - محرك الحسابات (lab.computation.engine)
    - معالج التصدير (lab.sample.excel.export.wizard)
    - أي نموذج آخر يحتاج معالجة بيانات المختبر
    """
    _name = 'lab.data.utils'
    _description = 'Lab Data Utilities'

    @api.model
    def format_value(self, value, precision=2):
        """تنسيق قيمة رقمية لعرضها في التقارير
        
        Args:
            value: Value to format
            precision: Number of decimal places
            
        Returns:
            str: Formatted value as string
        """
        try:
            if value is None:
                return ''
            formatted = ('{0:.' + str(precision) + 'f}').format(float(value))
            return formatted.rstrip('0').rstrip('.')
        except Exception:
            return ''

    @api.model
    def get_result_lines_by_codes(self, sample_or_result_set, criterion_codes):
        """
        Extract result lines based on criterion codes
        
        Args:
            sample_or_result_set: Sample or result set
            criterion_codes: List of criterion codes
            
        Returns:
            recordset: Matching result lines
        """
        if not criterion_codes:
            return self.env['lab.result.line']
            
        codes = [c.upper() for c in criterion_codes if c]
        
        if hasattr(sample_or_result_set, 'result_set_ids'):

            all_lines = self.env['lab.result.line']
            for result_set in sample_or_result_set.result_set_ids:
                lines = result_set.result_line_ids.filtered(
                    lambda l: l.criterion_id and (l.criterion_id.code or '').upper() in codes
                )
                all_lines |= lines
            return all_lines
        else:

            return sample_or_result_set.result_line_ids.filtered(
                lambda l: l.criterion_id and (l.criterion_id.code or '').upper() in codes
            )

    @api.model
    def extract_values_from_lines(self, result_lines, sort_by_sample=True):
        """استخراج
        Extract numeric values from result lines
        
        Args:
            result_lines: Result lines
            sort_by_sample: Sort by sample number
            
        Returns:
            list: List of numeric values
        """
        if sort_by_sample:
            result_lines = result_lines.sorted(lambda l: (getattr(l, 'sample_no', 0) or 0, l.id or 0))
        
        values = []
        for line in result_lines:
            val = getattr(line, 'result_value_computed', None)
            if not val:
                val = line.value_numeric
            
            if val is not None:
                try:
                    values.append(float(val))
                except Exception:
                    pass
        return values

    @api.model
    def get_sample_values_list(self, sample, criterion_codes, sort_by_sample=True):
        """Extract list of values from sample by criterion codes
        
        Args:
            sample: Sample
            criterion_codes: List of criterion codes
            sort_by_sample: Sort by sample number
            
        Returns:
            list: List of numeric values
        """
        lines = self.get_result_lines_by_codes(sample, criterion_codes)
        return self.extract_values_from_lines(lines, sort_by_sample)

    @api.model
    def get_sample_first_value(self, sample, criterion_codes):
        """Extract first value from sample by criterion codes
        
        Args:
            sample: Sample
            criterion_codes: List of criterion codes
            
        Returns:
            float: First value or 0.0
        """
        values = self.get_sample_values_list(sample, criterion_codes)
        return values[0] if values else 0.0

    @api.model
    def get_result_set_values_list(self, result_set, criterion_code, sort_by_sample=True):
        """Extract list of values from one result set
        
        Args:
            result_set: Result set
            criterion_code: Criterion code
            sort_by_sample: Sort by sample number
            

        Returns:
            list: List of numeric values
        """
        lines = result_set.result_line_ids.filtered(
            lambda l: l.criterion_id.code == criterion_code
        )
        
        if sort_by_sample:
            lines = lines.sorted('sample_no')
        
        values = []
        for line in lines:

            val = line.value_numeric
            if (val is None or val == 0) and line.criterion_id.test_type == 'computed':
                val = line.result_value_computed
            
            if val is not None:
                try:
                    values.append(float(val))
                except Exception:
                    pass
        return values

    @api.model
    def get_criterion_limits(self, sample, criterion_codes):
        """Extract criterion limits (minimum and maximum) from sample
        
        Args:
            sample: Sample
            criterion_codes: List of criterion codes
            
        Returns:
            tuple: (Minimum, Maximum) or (None, None)
        """
        lines = self.get_result_lines_by_codes(sample, criterion_codes)
        for line in lines:
            if line.criterion_id:
                return (line.criterion_id.min_value, line.criterion_id.max_value)
        return (None, None)

    @api.model
    def calculate_series_statistics(self, values):
        """Calculate basic statistics for a list of values
        
        Args:
            values: List of numeric values
            
        Returns:
            dict: Statistics (mean, max, min, count)
        """
        if not values:
            return {
                'avg': 0.0,
                'max': 0.0,
                'min': 0.0,
                'count': 0,
                'sum': 0.0
            }
        
        try:
            float_values = [float(v) for v in values if v is not None]
            if not float_values:
                return {
                    'avg': 0.0,
                    'max': 0.0,
                    'min': 0.0,
                    'count': 0,
                    'sum': 0.0
                }
            
            return {
                'avg': sum(float_values) / len(float_values),
                'max': max(float_values),
                'min': min(float_values),
                'count': len(float_values),
                'sum': sum(float_values)
            }
        except Exception as e:
            _logger.error("Error calculating statistics: %s", str(e))
            return {
                'avg': 0.0,
                'max': 0.0,
                'min': 0.0,
                'count': 0,
                'sum': 0.0
            }

    @api.model
    def filter_concrete_result_sets(self, sample, age_days=None, exclude_overall=True):
        """Filter concrete result sets
        
        Args:
            sample: Sample
            age_days: Age of concrete required ('7', '28', 'reserve') or None for all
            exclude_overall: Exclude overall average
            

        Returns:
            recordset: Filtered result sets
        """
        result_sets = sample.result_set_ids
        

        if exclude_overall:
            result_sets = result_sets.filtered(
                lambda rs: rs.template_id.code != 'CONCRETE_OVERALL_AVG'
            )
        
    
        result_sets = result_sets.filtered(
            lambda rs: getattr(rs, 'is_concrete_sample', False)
        )
        

        if age_days:
            result_sets = result_sets.filtered(
                lambda rs: rs.concrete_age_days == age_days
            )
        
        return result_sets.sorted('concrete_group_no')

    @api.model
    def get_cross_sets_average(self, sample, criterion_code, age_days='28', primary_fallback=None):
        """Calculate average of values across different result sets
        
        Args:
            sample: Sample
            criterion_code: Primary criterion code
            age_days: Age of concrete required
            primary_fallback: Alternative criterion code if primary not found
            
        Returns:
            float: Calculated average
        """
        result_sets = self.filter_concrete_result_sets(sample, age_days)
        
        values = []
        for result_set in result_sets:

            lines = result_set.result_line_ids.filtered(
                lambda l: l.criterion_id.code == criterion_code
            )
            
            if lines and lines[0].value_numeric:
                values.append(lines[0].value_numeric)
            elif primary_fallback:

                fallback_lines = result_set.result_line_ids.filtered(
                    lambda l: l.criterion_id.code == primary_fallback
                )
                if fallback_lines and fallback_lines[0].value_numeric:
                    values.append(fallback_lines[0].value_numeric)
        
        stats = self.calculate_series_statistics(values)
        return stats['avg']
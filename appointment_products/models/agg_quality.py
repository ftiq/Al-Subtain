# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


SIEVE_CODE_TO_LABEL = {
    '75MM': '75 mm',
    '50MM': '50 mm',
    '25MM': '25 mm',
    '9_5MM': '9.5 mm',
    '4_75MM': '4.75 mm',
    '2_36MM': '2.36 mm',
    '0_3MM': '0.3 mm',
    '0_075MM': '0.075 mm',
}

SIEVE_CODE_TO_PASS_CRIT = {
    '75MM': 'PASS_75MM_PCT',
    '50MM': 'PASS_50MM_PCT',
    '25MM': 'PASS_25MM_PCT',
    '9_5MM': 'PASS_9_5MM_PCT',
    '4_75MM': 'PASS_4_75MM_PCT',
    '2_36MM': 'PASS_2_36MM_PCT',
    '0_3MM': 'PASS_0_3MM_PCT',
    '0_075MM': 'PASS_0_075MM_PCT',
}


class LabAggQualityRange(models.Model):
    _name = 'lab.agg.quality.range'
    _description = 'حدود التدرج (R6/2003) لكل منخل'
    _order = 'sequence, id'

    company_id = fields.Many2one(
        'res.company', string='الشركة', required=True, readonly=True,
        default=lambda self: self.env.company)

    result_set_id = fields.Many2one('lab.result.set', string='مجموعة النتائج', ondelete='cascade', index=True)

    sequence = fields.Integer(string='التسلسل', default=10)

    sieve_code = fields.Selection(
        selection=[(k, v) for k, v in SIEVE_CODE_TO_LABEL.items()],
        string='رمز المنخل', required=True)

    sieve_label = fields.Char(string='المنخل', compute='_compute_labels', store=True)

    # حدود الفئات الافتراضية (قابلة للتعديل لكل مجموعة نتائج)
    min_A = fields.Float(string='A الأدنى')
    max_A = fields.Float(string='A الأعلى')
    min_B = fields.Float(string='B الأدنى')
    max_B = fields.Float(string='B الأعلى')
    min_C = fields.Float(string='C الأدنى')
    max_C = fields.Float(string='C الأعلى')
    min_D = fields.Float(string='D الأدنى')
    max_D = fields.Float(string='D الأعلى')

    # الحدود الفعالة حسب الفئة المختارة
    effective_min = fields.Float(string='الحد الأدنى (مُطبق)', compute='_compute_effective_limits', store=True)
    effective_max = fields.Float(string='الحد الأعلى (مُطبق)', compute='_compute_effective_limits', store=True)

    # قيمة %المار من جدول النتائج
    actual_passing = fields.Float(string='% المار الفعلي', compute='_compute_actual_passing', store=False)

    # المطابقة لهذا المنخل
    is_within_range = fields.Boolean(string='مطابق', compute='_compute_is_within', store=False)

    @api.depends('sieve_code')
    def _compute_labels(self):
        for rec in self:
            rec.sieve_label = SIEVE_CODE_TO_LABEL.get(rec.sieve_code, rec.sieve_code)

    @api.depends('result_set_id.agg_selected_class', 'min_A', 'max_A', 'min_B', 'max_B', 'min_C', 'max_C', 'min_D', 'max_D')
    def _compute_effective_limits(self):
        for rec in self:
            cls = rec.result_set_id.agg_selected_class or 'A'
            if cls == 'A':
                rec.effective_min, rec.effective_max = rec.min_A or 0.0, rec.max_A or 0.0
            elif cls == 'B':
                rec.effective_min, rec.effective_max = rec.min_B or 0.0, rec.max_B or 0.0
            elif cls == 'C':
                rec.effective_min, rec.effective_max = rec.min_C or 0.0, rec.max_C or 0.0
            else:
                rec.effective_min, rec.effective_max = rec.min_D or 0.0, rec.max_D or 0.0

    @api.depends(
        'result_set_id.result_line_ids.value_numeric',
        'result_set_id.result_line_ids.result_value_computed',
        'result_set_id.result_line_ids.criterion_id',
    )
    def _compute_actual_passing(self):
        for rec in self:
            rec.actual_passing = 0.0
            rs = rec.result_set_id
            if not rs or not rs.result_line_ids:
                continue
            code = SIEVE_CODE_TO_PASS_CRIT.get(rec.sieve_code)
            if not code:
                continue
            line = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == code)[:1]
            # خذ بعين الاعتبار الحقول المحسوبة المخزنة في result_value_computed عند الحاجة
            val = 0.0
            if line:
                val = line[0].value_numeric or getattr(line[0], 'result_value_computed', 0.0) or 0.0
            rec.actual_passing = float(val)

    @api.depends('effective_min', 'effective_max', 'actual_passing')
    def _compute_is_within(self):
        for rec in self:
            if rec.effective_min == 0.0 and rec.effective_max == 0.0:
                rec.is_within_range = True  # لا حدود معرفة => اعتبره مقبولاً حتى يضبط المستخدم
                continue
            val = rec.actual_passing
            lo = rec.effective_min if rec.effective_min is not None else 0.0
            hi = rec.effective_max if rec.effective_max is not None else 100.0
            # سماحية صغيرة لمشاكل التقريب العشري
            tol = 1e-2
            rec.is_within_range = ((val + tol) >= lo) and ((val - tol) <= hi)


# ترتيب المناخل لعرضها وإنشاءها
SIEVE_ORDER = [
    '75MM', '50MM', '25MM', '9_5MM', '4_75MM', '2_36MM', '0_3MM', '0_075MM'
]

# الحدود الافتراضية حسب الصورة (R6/2003) - قيم يمكن تعديلها على مستوى كل فحص
# ملاحظة: القيم الفارغة تُترك صفر/صفر ويُعتبر السطر "غير محدد" حتى يضبط المستخدم
DEFAULT_AGG_RANGES = {
    '75MM': {
        'A': (100, 100),
        'B': (100, 100),
        'C': (0, 0),
        'D': (0, 0),
    },
    '50MM': {
        'A': (95, 100),
        'B': (100, 100),
        'C': (0, 0),
        'D': (0, 0),
    },
    '25MM': {
        'A': (0, 0),
        'B': (75, 95),
        'C': (100, 100),
        'D': (100, 100),
    },
    '9_5MM': {
        'A': (30, 65),
        'B': (40, 75),
        'C': (50, 85),
        'D': (60, 100),
    },
    '4_75MM': {
        'A': (25, 55),
        'B': (30, 60),
        'C': (35, 65),
        'D': (50, 85),
    },
    '2_36MM': {
        'A': (16, 42),
        'B': (21, 47),
        'C': (26, 52),
        'D': (42, 72),
    },
    '0_3MM': {
        'A': (7, 18),
        'B': (14, 28),
        'C': (14, 28),
        'D': (23, 42),
    },
    '0_075MM': {
        'A': (2, 8),
        'B': (5, 15),
        'C': (5, 15),
        'D': (5, 15),
    },
}


def build_default_range_lines():
    """إرجاع قائمة قواميس لإنشاء أسطر الحدود الافتراضية لفحص التدرج.
    تُستخدم عند إنشاء مجموعة نتائج جديدة لقالب AGG_QUALITY_SIEVE.
    """
    lines = []
    for idx, code in enumerate(SIEVE_ORDER, start=1):
        cls = DEFAULT_AGG_RANGES.get(code, {})
        a = cls.get('A', (0.0, 0.0))
        b = cls.get('B', (0.0, 0.0))
        c = cls.get('C', (0.0, 0.0))
        d = cls.get('D', (0.0, 0.0))
        lines.append({
            'sequence': idx * 10,
            'sieve_code': code,
            'min_A': a[0], 'max_A': a[1],
            'min_B': b[0], 'max_B': b[1],
            'min_C': c[0], 'max_C': c[1],
            'min_D': d[0], 'max_D': d[1],
        })
    return lines

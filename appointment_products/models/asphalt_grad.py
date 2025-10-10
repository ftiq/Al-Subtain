# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

# Asphalt mix sieves used in client sheets (in mm)
SIEVE_CODE_TO_LABEL_ASPHALT = {
    '37_5MM': '37.5 mm',
    '25MM': '25 mm',
    '19MM': '19 mm',
    '12_5MM': '12.5 mm',
    '9_5MM': '9.5 mm',
    '4_75MM': '4.75 mm',
    '2_36MM': '2.36 mm',
    '0_3MM': '0.3 mm',
    '0_075MM': '0.075 mm',
}

# Map sieve code -> criterion code that stores %Passing value in result lines for asphalt mix template
SIEVE_CODE_TO_PASS_CRIT_ASPHALT = {
    '37_5MM': 'PASS_37_5MM_PCT',
    '25MM': 'PASS_25MM_PCT',
    '19MM': 'PASS_19MM_PCT',
    '12_5MM': 'PASS_12_5MM_PCT',
    '9_5MM': 'PASS_9_5MM_PCT',
    '4_75MM': 'PASS_4_75MM_PCT',
    '2_36MM': 'PASS_2_36MM_PCT',
    '0_3MM': 'PASS_0_3MM_PCT',
    '0_075MM': 'PASS_0_075MM_PCT',
}

ASPHALT_SIEVE_ORDER = [
    '37_5MM', '25MM', '19MM', '12_5MM', '9_5MM', '4_75MM', '2_36MM', '0_3MM', '0_075MM'
]

# Default SPEC limits per layer. Start with Binder (رابطة) from user's sheet. Others left as zeros (to be set by user).
DEFAULT_SPEC_LIMITS = {
    'BINDER': {  # طبقة رابطة
        '37_5MM': (100.0, 100.0),
        '25MM': (90.0, 100.0),
        '19MM': (76.0, 90.0),
        '12_5MM': (56.0, 80.0),
        '9_5MM': (48.0, 74.0),
        '4_75MM': (29.0, 59.0),
        '2_36MM': (19.0, 45.0),
        '0_3MM': (5.0, 17.0),
        '0_075MM': (2.0, 8.0),
    },
    # To be provided/confirmed; initialized to zeros so UI shows unspecified until user sets them
    'SURFACE': {code: (0.0, 0.0) for code in ASPHALT_SIEVE_ORDER},  # سطحية
    'BASE': {code: (0.0, 0.0) for code in ASPHALT_SIEVE_ORDER},     # أساس
}

# Default FORMULA limits for Binder from user's sheet (editable by user). Others mirror SPEC by default (or zeros).
DEFAULT_FORMULA_LIMITS = {
    'BINDER': {
        '37_5MM': (100.0, 100.0),
        '25MM': (90.0, 100.0),
        '19MM': (75.3, 87.3),
        '12_5MM': (58.5, 70.5),
        '9_5MM': (48.0, 58.8),
        '4_75MM': (37.2, 49.2),
        '2_36MM': (26.3, 34.3),
        '0_3MM': (5.7, 13.7),
        '0_075MM': (2.5, 6.5),
    },
    'SURFACE': {code: (0.0, 0.0) for code in ASPHALT_SIEVE_ORDER},
    'BASE': {code: (0.0, 0.0) for code in ASPHALT_SIEVE_ORDER},
}


def _get_layer_key_from_sample(sample):
    """Return 'BINDER' | 'SURFACE' | 'BASE' based on sample.subtype.
    Fallback to 'BINDER' if unknown.
    """
    try:
        st = getattr(sample, 'sample_subtype_id', False)
        code = (st.code or '').upper() if st else ''
    except Exception:
        code = ''
    if 'BINDER' in code or 'رابط' in code:
        return 'BINDER'
    if 'SURFACE' in code or 'سطح' in code:
        return 'SURFACE'
    if 'BASE' in code or 'اساس' in code or 'أساس' in code:
        return 'BASE'

    # Fallback: infer from product name/default_code when subtype not set
    try:
        prod = getattr(sample, 'product_id', False)
        pname = (prod.name or '') if prod else ''
        pcode = (prod.default_code or '') if (prod and hasattr(prod, 'default_code')) else ''
        text = f"{pname} {pcode}".upper()
    except Exception:
        pname = ''
        text = ''

    if ('SURFACE' in text) or ('سطح' in pname):
        return 'SURFACE'
    if ('BASE' in text) or ('اساس' in pname) or ('أساس' in pname):
        return 'BASE'
    if ('BINDER' in text) or ('رابط' in pname):
        return 'BINDER'
    return 'BINDER'


def build_default_asphalt_grad_lines(sample=None):
    """Build default rows for asphalt gradation table.
    If sample is provided, seed SPEC/FORMULA from the appropriate layer dictionary.
    Returns list of dicts ready for create().
    """
    layer = _get_layer_key_from_sample(sample) if sample else 'BINDER'
    spec_map = DEFAULT_SPEC_LIMITS.get(layer, DEFAULT_SPEC_LIMITS['BINDER'])
    formula_map = DEFAULT_FORMULA_LIMITS.get(layer, DEFAULT_FORMULA_LIMITS['BINDER'])
    lines = []
    for idx, code in enumerate(ASPHALT_SIEVE_ORDER, start=1):
        s_lo, s_hi = spec_map.get(code, (0.0, 0.0))
        f_lo, f_hi = formula_map.get(code, (s_lo, s_hi))
        lines.append({
            'sequence': idx * 10,
            'sieve_code': code,
            'spec_min': s_lo,
            'spec_max': s_hi,
            'formula_min': f_lo,
            'formula_max': f_hi,
        })
    return lines


class LabAsphaltGradRange(models.Model):
    _name = 'lab.asphalt.grad.range'
    _description = 'حدود تدرج الخلطة الإسفلتية (SPEC ثابت + FORMULA قابلة للتعديل)'
    _order = 'sequence, id'

    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True,
                                 default=lambda self: self.env.company)
    result_set_id = fields.Many2one('lab.result.set', string='مجموعة النتائج', ondelete='cascade', index=True)
    sequence = fields.Integer(string='التسلسل', default=10)

    sieve_code = fields.Selection(
        selection=[(k, v) for k, v in SIEVE_CODE_TO_LABEL_ASPHALT.items()],
        string='رمز المنخل', required=True)
    sieve_label = fields.Char(string='المنخل', compute='_compute_labels', store=True)

    # Fixed spec limits (read-only in views)
    spec_min = fields.Float(string='حد المواصفة الأدنى')
    spec_max = fields.Float(string='حد المواصفة الأعلى')

    # Editable formula limits
    formula_min = fields.Float(string='حد المعادلة الأدنى')
    formula_max = fields.Float(string='حد المعادلة الأعلى')

    # Effective limits for evaluation (same as formula)
    effective_min = fields.Float(string='الحد الأدنى (مُطبق)', compute='_compute_effective_limits', store=True)
    effective_max = fields.Float(string='الحد الأعلى (مُطبق)', compute='_compute_effective_limits', store=True)

    # Actual %Passing pulled from result lines
    actual_passing = fields.Float(string='% المار الفعلي', compute='_compute_actual_passing', store=False)

    # Booleans for visual cues
    spec_ok = fields.Boolean(string='ضمن المواصفة', compute='_compute_ok_flags', store=False)
    formula_ok = fields.Boolean(string='ضمن المعادلة', compute='_compute_ok_flags', store=False)
    both_ok = fields.Boolean(string='مطابق (المعادلة + المواصفة)', compute='_compute_ok_flags', store=False)

    @api.depends('sieve_code')
    def _compute_labels(self):
        for rec in self:
            rec.sieve_label = SIEVE_CODE_TO_LABEL_ASPHALT.get(rec.sieve_code, rec.sieve_code)

    @api.depends('formula_min', 'formula_max')
    def _compute_effective_limits(self):
        for rec in self:
            rec.effective_min = rec.formula_min or 0.0
            rec.effective_max = rec.formula_max or 0.0

    @api.depends('result_set_id.result_line_ids.value_numeric',
                 'result_set_id.result_line_ids.result_value_computed',
                 'result_set_id.result_line_ids.criterion_id')
    def _compute_actual_passing(self):
        for rec in self:
            rec.actual_passing = 0.0
            rs = rec.result_set_id
            if not rs or not rs.result_line_ids:
                continue
            code = SIEVE_CODE_TO_PASS_CRIT_ASPHALT.get(rec.sieve_code)
            if not code:
                continue
            line = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == code)[:1]
            val = 0.0
            if line:
                val = line[0].value_numeric or getattr(line[0], 'result_value_computed', 0.0) or 0.0
            rec.actual_passing = float(val)

    @api.depends('spec_min', 'spec_max', 'formula_min', 'formula_max', 'actual_passing')
    def _compute_ok_flags(self):
        tol = 1e-2
        for rec in self:
            v = float(rec.actual_passing or 0.0)
            # Spec check only if defined (non-zero range)
            if float(rec.spec_min or 0.0) == 0.0 and float(rec.spec_max or 0.0) == 0.0:
                spec_ok = True  # unspecified -> consider okay
            else:
                lo = float(rec.spec_min or 0.0)
                hi = float(rec.spec_max or 0.0)
                spec_ok = ((v + tol) >= lo) and ((v - tol) <= hi)
            # Formula check only if defined (non-zero range)
            if float(rec.formula_min or 0.0) == 0.0 and float(rec.formula_max or 0.0) == 0.0:
                formula_ok = True  # unspecified -> consider okay
            else:
                lo_f = float(rec.formula_min or 0.0)
                hi_f = float(rec.formula_max or 0.0)
                formula_ok = ((v + tol) >= lo_f) and ((v - tol) <= hi_f)
            rec.spec_ok = spec_ok
            rec.formula_ok = formula_ok
            rec.both_ok = bool(spec_ok and formula_ok)

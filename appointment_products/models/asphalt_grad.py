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

# Default SPEC limits per layer. Binder (رابطة) مأخوذة من ورقة العميل.
# SURFACE و BASE تمت تعبئتها وفق الجداول الظاهرة في الصور/CSV (عمود A كحدود أساسية قابلة للتعديل لاحقاً).
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
    # طبقة سطحية (من الصور/CSV - عمود A)
    'SURFACE': {  # سطحية
        '37_5MM': (100.0, 100.0),
        '25MM': (0.0, 0.0),
        '19MM': (30.0, 65.0),
        '12_5MM': (25.0, 55.0),
        '9_5MM': (16.0, 42.0),
        '4_75MM': (7.0, 18.0),
        '2_36MM': (2.0, 8.0),
        '0_3MM': (5.0, 15.0),
        '0_075MM': (2.0, 8.0),
    },
    # طبقة أساس (من الصور/CSV - عمود A)
    'BASE': {     # أساس
        '37_5MM': (100.0, 100.0),
        '25MM': (100.0, 100.0),
        '19MM': (30.0, 65.0),
        '12_5MM': (25.0, 55.0),
        '9_5MM': (16.0, 42.0),
        '4_75MM': (7.0, 18.0),
        '2_36MM': (2.0, 8.0),
        '0_3MM': (3.5, 7.5),
        '0_075MM': (2.0, 6.0),
    },
}

# Default FORMULA limits. Binder من ورقة العميل. لبقية الطبقات اعتمدنا نفس حدود SPEC كقيمة ابتدائية قابلة للتعديل في الواجهة.
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
    'SURFACE': {
        '37_5MM': (100.0, 100.0),
        '25MM': (0.0, 0.0),
        '19MM': (30.0, 65.0),
        '12_5MM': (25.0, 55.0),
        '9_5MM': (16.0, 42.0),
        '4_75MM': (7.0, 18.0),
        '2_36MM': (2.0, 8.0),
        '0_3MM': (5.0, 15.0),
        '0_075MM': (2.0, 8.0),
    },
    'BASE': {
        '37_5MM': (100.0, 100.0),
        '25MM': (100.0, 100.0),
        '19MM': (30.0, 65.0),
        '12_5MM': (25.0, 55.0),
        '9_5MM': (16.0, 42.0),
        '4_75MM': (7.0, 18.0),
        '2_36MM': (2.0, 8.0),
        '0_3MM': (3.5, 7.5),
        '0_075MM': (2.0, 6.0),
    },
}


def _make_by_class(base_map):
    """Create a per-class dict {'A': map, 'B': map, 'C': map, 'D': map}.
    Initially we duplicate A into B/C/D so the user can later adjust them
    in code based on images/CSVs. This avoids empty (0,0) bounds.
    """
    by_class = {}
    for layer_key, sieve_map in base_map.items():
        # shallow copy per class to allow independent edits
        a_map = {k: tuple(v) for k, v in sieve_map.items()}
        by_class[layer_key] = {
            'A': {k: tuple(v) for k, v in a_map.items()},
            'B': {k: tuple(v) for k, v in a_map.items()},
            'C': {k: tuple(v) for k, v in a_map.items()},
            'D': {k: tuple(v) for k, v in a_map.items()},
        }
    return by_class


# Class-based defaults. A is the current DEFAULT_* content; B/C/D are placeholders
# initially equal to A until the user updates them to match client sheets (columns B/C/D).
DEFAULT_SPEC_LIMITS_BY_CLASS = _make_by_class(DEFAULT_SPEC_LIMITS)
DEFAULT_FORMULA_LIMITS_BY_CLASS = _make_by_class(DEFAULT_FORMULA_LIMITS)


def get_asphalt_class_maps(sample, cls='A'):
    """Return (spec_map, formula_map) for the asphalt mix based on sample layer and class A/B/C/D.
    Falls back to class 'A' and then to DEFAULT_* if class not found.
    """
    layer = _get_layer_key_from_sample(sample) if sample else 'BINDER'
    sel = (cls or 'A').upper()
    spec_by_layer = DEFAULT_SPEC_LIMITS_BY_CLASS.get(layer) or {}
    form_by_layer = DEFAULT_FORMULA_LIMITS_BY_CLASS.get(layer) or {}
    spec_map = spec_by_layer.get(sel) or DEFAULT_SPEC_LIMITS.get(layer, {})
    formula_map = form_by_layer.get(sel) or DEFAULT_FORMULA_LIMITS.get(layer, {})
    return spec_map, formula_map

# Override SURFACE per-class limits based on provided A/B/C/D table
try:
    surf_spec = DEFAULT_SPEC_LIMITS_BY_CLASS.get('SURFACE', {})
    surf_form = DEFAULT_FORMULA_LIMITS_BY_CLASS.get('SURFACE', {})
    # 37.5 mm: B/C/D are unspecified
    for k in ('B', 'C', 'D'):
        if k in surf_spec:
            surf_spec[k]['37_5MM'] = (0.0, 0.0)
        if k in surf_form:
            surf_form[k]['37_5MM'] = (0.0, 0.0)
    # 25 mm
    if 'B' in surf_spec:
        surf_spec['B']['25MM'] = (75.0, 95.0)
    if 'B' in surf_form:
        surf_form['B']['25MM'] = (75.0, 95.0)
    if 'C' in surf_spec:
        surf_spec['C']['25MM'] = (100.0, 100.0)
    if 'C' in surf_form:
        surf_form['C']['25MM'] = (100.0, 100.0)
    if 'D' in surf_spec:
        surf_spec['D']['25MM'] = (100.0, 100.0)
    if 'D' in surf_form:
        surf_form['D']['25MM'] = (100.0, 100.0)
    # 19 mm
    for k, rng in {
        'A': (30.0, 65.0),
        'B': (40.0, 75.0),
        'C': (50.0, 85.0),
        'D': (60.0, 100.0),
    }.items():
        if k in surf_spec:
            surf_spec[k]['19MM'] = rng
        if k in surf_form:
            surf_form[k]['19MM'] = rng
    # 12.5 mm
    for k, rng in {
        'A': (25.0, 55.0),
        'B': (30.0, 60.0),
        'C': (35.0, 65.0),
        'D': (50.0, 85.0),
    }.items():
        if k in surf_spec:
            surf_spec[k]['12_5MM'] = rng
        if k in surf_form:
            surf_form[k]['12_5MM'] = rng
    # 9.5 mm
    for k, rng in {
        'A': (16.0, 42.0),
        'B': (21.0, 47.0),
        'C': (26.0, 52.0),
        'D': (42.0, 72.0),
    }.items():
        if k in surf_spec:
            surf_spec[k]['9_5MM'] = rng
        if k in surf_form:
            surf_form[k]['9_5MM'] = rng
    # 4.75 mm
    for k, rng in {
        'A': (7.0, 18.0),
        'B': (14.0, 28.0),
        'C': (14.0, 28.0),
        'D': (23.0, 42.0),
    }.items():
        if k in surf_spec:
            surf_spec[k]['4_75MM'] = rng
        if k in surf_form:
            surf_form[k]['4_75MM'] = rng
    # 2.36 mm
    for k, rng in {
        'A': (2.0, 8.0),
        'B': (5.0, 15.0),
        'C': (5.0, 15.0),
        'D': (5.0, 20.0),
    }.items():
        if k in surf_spec:
            surf_spec[k]['2_36MM'] = rng
        if k in surf_form:
            surf_form[k]['2_36MM'] = rng
except Exception:
    # حماية من أي خطأ أثناء الاستيراد
    pass

# Temporary: mirror SURFACE class overrides into BINDER and BASE so toggle A/B/C/D affects all layers
try:
    surf_spec = DEFAULT_SPEC_LIMITS_BY_CLASS.get('SURFACE', {})
    surf_form = DEFAULT_FORMULA_LIMITS_BY_CLASS.get('SURFACE', {})
    for layer_key in ('BINDER', 'BASE'):
        lspec = DEFAULT_SPEC_LIMITS_BY_CLASS.get(layer_key)
        lform = DEFAULT_FORMULA_LIMITS_BY_CLASS.get(layer_key)
        if not lspec or not lform:
            continue
        for cls in ('A', 'B', 'C', 'D'):
            sm = surf_spec.get(cls)
            fm = surf_form.get(cls)
            if sm:
                # keep existing keys not in SURFACE map (e.g., 0.3/0.075 unchanged)
                for k, v in sm.items():
                    lspec[cls][k] = v
            if fm:
                for k, v in fm.items():
                    lform[cls][k] = v
except Exception:
    pass


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


def build_default_asphalt_grad_lines(sample=None, cls='A'):
    """Build default rows for asphalt gradation table.
    If sample is provided, seed SPEC/FORMULA from the appropriate layer and selected class (A/B/C/D).
    Returns list of dicts ready for create().
    """
    spec_map, formula_map = get_asphalt_class_maps(sample, cls or 'A')
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

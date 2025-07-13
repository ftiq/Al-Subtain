# -*- coding: utf-8 -*-
from odoo import fields, models, _


class LabSampleSubtype(models.Model):
    """نموذج يمثل النوع الفرعي للعينة (مثلاً: خرسانة جاهزة، خرسانة سابقة الصب...)."""
    _name = 'lab.sample.subtype'
    _description = 'نوع فرعي للعينة'
    _order = 'sequence, name'

    _check_company_auto = True

    name = fields.Char(string='الاسم', required=True, translate=True)
    code = fields.Char(string='الرمز', required=True, index=True)
    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع العينة',
        required=True,
        ondelete='cascade',
    )
    description = fields.Text(string='الوصف')
    sequence = fields.Integer(string='التسلسل', default=10)
    active = fields.Boolean(string='نشط', default=True)
    

    efflorescence_level = fields.Selection([
        ('none', 'لا يوجد'),
        ('light', 'خفيف'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
    ], string='درجة التزهر المسموحة', default='none',
       help='درجة التزهر المسموحة لهذا النوع الفرعي من العينة')

    hole_count = fields.Integer(
        string='عدد الفتحات',
        default=0,
        help='عدد الفتحات في هذا النوع الفرعي للطابوق/العينة'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('unique_code_per_type', 'unique(code, sample_type_id)',
         'رمز النوع الفرعي يجب أن يكون فريداً ضمن نوع العينة!'),
    ] 
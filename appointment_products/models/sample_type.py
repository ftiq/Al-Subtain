# -*- coding: utf-8 -*-
from odoo import fields, models, _


class LabSampleType(models.Model):
    """نموذج يمثل نوع العينة (خرسانة، تربة، أسفلت...)"""
    _name = 'lab.sample.type'
    _description = 'نوع العينة'
    _order = 'sequence, name'

    _check_company_auto = True

    name = fields.Char(string='الاسم', required=True, translate=True)
    code = fields.Char(string='الرمز', required=True, index=True)
    description = fields.Text(string='الوصف')
    sequence = fields.Integer(string='التسلسل', default=10)
    active = fields.Boolean(string='نشط', default=True)

    subtype_ids = fields.One2many(
        'lab.sample.subtype',
        'sample_type_id',
        string='الأنواع الفرعية'
    )

    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True, default=lambda self: self.env.company)

    initial_volume_m3 = fields.Integer(string='حجم الشريحة الأولى (م³)', default=80,
                                       help='الحجم بالـ م³ الذي يستلزم أخذ الشريحة الأولى من العينات')
    repeat_volume_m3 = fields.Integer(string='حجم التكرار (م³)', default=50,
                                      help='يتم أخذ عينة إضافية كل هذه الكمية بعد الشريحة الأولى')
    sets_first_stage = fields.Integer(string='عدد العينات في الشريحة الأولى', default=4,
                                      help='عدد العينات (Sample Sets) في الشريحة الأولى')
    cubes_per_set = fields.Integer(string='عدد المكعبات لكل عينة', default=3,
                                   help='عدد المكعبات الأساسية في كل عينة')
    extra_cubes_per_set = fields.Integer(string='مكعبات إضافية لكل عينة', default=2,
                                         help='مثل مكعب 7 أيام واحتياطي')
    age_days_list = fields.Char(string='أعمار الاختبار (أيام)', default='7,28',
                                help='قائمة مفصولة بفواصل لأعمار اختبار المكعبات الإضافية')

    _sql_constraints = [
        ('unique_code', 'unique(code, company_id)', 'يجب أن يكون رمز نوع العينة فريداً داخل الشركة!'),
    ] 
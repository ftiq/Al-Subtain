# -*- coding: utf-8 -*-
from odoo import fields, models, _


class LabConcreteTruck(models.Model):
    """شاحنة خرسانة مرتبطة بعملية الصبّ لتتبع توزيع المكعبات."""
    _name = 'lab.concrete.truck'
    _description = 'Concrete Truck'
    _order = 'name'

    name = fields.Char(string='رقم الشاحنة', required=True)
    capacity_m3 = fields.Float(string='الحمولة (م³)', default=10.0)
    note = fields.Char(string='ملاحظات')

    cube_ids = fields.One2many('lab.sample.cube', 'truck_id', string='المكعبات')

    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_name_company', 'unique(name, company_id)', 'رقم الشاحنة يجب أن يكون فريداً داخل الشركة!'),
    ] 
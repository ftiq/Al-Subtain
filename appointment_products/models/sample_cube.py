# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class LabSampleCube(models.Model):
    """يمثل مكعب اختبار ضمن عينة خرسانة"""
    _name = 'lab.sample.cube'
    _description = 'Concrete Sample Cube'
    _order = 'sample_id, set_no, cube_index'

    name = fields.Char(string='المرجع', required=True, copy=False, default=lambda self: _('New'))

    sample_id = fields.Many2one('lab.sample', string='العينة', required=True, ondelete='cascade', index=True)

    set_no = fields.Integer(string='رقم العينة الفرعية', required=True)
    cube_index = fields.Integer(string='رقم المكعب داخل العينة', required=True)

    cube_type = fields.Selection([
        ('core', 'أساسي'),
        ('extra', 'إضافي')
    ], string='نوع المكعب', default='core')

    age_days = fields.Integer(string='عمر الاختبار (أيام)', default=28)

    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_cube', 'unique(sample_id, set_no, cube_index)', 'رقم المكعب مكرر داخل العينة!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name') in (False, _('New')):
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.sample.cube') or _('New')
        return super().create(vals)

 
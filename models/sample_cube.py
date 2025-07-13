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

    truck_id = fields.Many2one('lab.concrete.truck', string='الشاحنة')

    company_id = fields.Many2one('res.company', string='الشركة', required=True, readonly=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_cube', 'unique(sample_id, set_no, cube_index)', 'رقم المكعب مكرر داخل العينة!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name') in (False, _('New')):
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.sample.cube') or _('New')
        return super().create(vals)

    @api.constrains('truck_id', 'cube_type', 'set_no')
    def _check_truck_distribution(self):
        for cube in self.filtered(lambda c: c.cube_type == 'core'):
            sibling_core = cube.search([
                ('sample_id', '=', cube.sample_id.id),
                ('set_no', '=', cube.set_no),
                ('cube_type', '=', 'core'),
                ('id', '!=', cube.id)
            ])
            if cube.truck_id and sibling_core.filtered(lambda s: s.truck_id == cube.truck_id):
                raise UserError(_('يجب ألا يتكرر رقم الشاحنة داخل نفس العينة الفرعية للمكعبات الأساسية، إلا إذا تركت الحقل فارغاً.')) 
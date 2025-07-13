# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class LabGenerateCubesWizard(models.TransientModel):
    _name = 'lab.generate.cubes.wizard'
    _description = 'معالج توليد مكعبات الخرسانة'

    sample_id = fields.Many2one('lab.sample', string='العينة', required=True)
    volume_m3 = fields.Float(string='حجم الصبّ (م³)', required=True, default=80.0)
    truck_ids = fields.Many2many('lab.concrete.truck', string='الشاحنات المتاحة')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            res['sample_id'] = active_id
        return res

    def action_generate(self):
        self.ensure_one()
        if self.volume_m3 <= 0:
            raise UserError(_('الرجاء إدخال حجم صبّ صالح (>0).'))
        self.sample_id.action_generate_concrete_cubes(self.volume_m3, self.truck_ids.ids)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lab.sample',
            'name': _('Sample'),
            'view_mode': 'form',
            'res_id': self.sample_id.id,
            'target': 'current',
        } 
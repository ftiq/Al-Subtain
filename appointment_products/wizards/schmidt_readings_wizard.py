# -*- coding: utf-8 -*-
import json
from statistics import mean
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SchmidtReadingsWizard(models.TransientModel):
    _name = 'schmidt.readings.wizard'
    _description = 'Wizard: Enter 10 RN readings for a Schmidt point and compute average'

    point_id = fields.Many2one(
        'project.task.schmidt.point',
        string='point_id', required=True, ondelete='cascade')

    r1 = fields.Float(string='r1')
    r2 = fields.Float(string='r2')
    r3 = fields.Float(string='r3')
    r4 = fields.Float(string='r4')
    r5 = fields.Float(string='r5')
    r6 = fields.Float(string='r6')
    r7 = fields.Float(string='r7')
    r8 = fields.Float(string='r8')
    r9 = fields.Float(string='r9')
    r10 = fields.Float(string='r10')

    rn_avg_preview = fields.Float(string='rn_avg_preview', compute='_compute_preview', digits=(16, 2))

    @api.depends('r1','r2','r3','r4','r5','r6','r7','r8','r9','r10')
    def _compute_preview(self):
        for w in self:
            vals = [v for v in [w.r1,w.r2,w.r3,w.r4,w.r5,w.r6,w.r7,w.r8,w.r9,w.r10] if (v is not None and v > 0)]
            if vals:
                try:
                    w.rn_avg_preview = round(mean(vals), 0)
                except Exception:
                    w.rn_avg_preview = 0.0
            else:
                w.rn_avg_preview = 0.0

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        point_id = self.env.context.get('default_point_id')
        if point_id:
            point = self.env['project.task.schmidt.point'].browse(point_id)

            if point and point.rn_readings_json:
                try:
                    arr = json.loads(point.rn_readings_json)
                    for idx, key in enumerate(['r1','r2','r3','r4','r5','r6','r7','r8','r9','r10']):
                        if idx < len(arr):
                            res[key] = arr[idx]
                except Exception:
                    pass
        return res

    def action_apply(self):
        self.ensure_one()
        if not self.point_id:
            raise ValidationError(_('لم يتم تحديد النقطة.'))
        readings = [self.r1, self.r2, self.r3, self.r4, self.r5, self.r6, self.r7, self.r8, self.r9, self.r10]
        vals = [v for v in readings if (v is not None and v > 0)]
        if len(vals) < 3:

            raise ValidationError(_('يرجى إدخال 3 قراءات صالحة على الأقل (> 0).'))
        try:
            avg_val = round(mean(vals), 0)
        except Exception:
            avg_val = 0.0

        self.point_id.write({
            'rn_avg': avg_val,
            'rn_readings_json': json.dumps(readings),
        })

        return {
            'type': 'ir.actions.act_window_close'
        }

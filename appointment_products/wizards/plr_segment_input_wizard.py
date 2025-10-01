# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PLRSegmentInputWizard(models.TransientModel):
    _name = 'plr.segment.input.wizard'
    _description = 'PLR Segment Input Wizard'

    segment_id = fields.Many2one('project.task.plr.segment', string='المقطع', required=True)
    station_range = fields.Char(string='مدى المقطع', related='segment_id.station_range', readonly=True)

    line_ids = fields.One2many('plr.segment.input.line.wizard', 'wizard_id', string='محطات 50 م')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        seg_id = self.env.context.get('default_segment_id')
        if seg_id:
            seg = self.env['project.task.plr.segment'].browse(seg_id)
            seg_len = max(0, int((seg.end_m or 0) - (seg.start_m or 0)))
            step = 50
            count = (seg_len + step - 1) // step if step else 0
            lines = []
            start = 0
            for i in range(count):
                end = min(start + step, seg_len)
                abs_start = int(seg.start_m or 0) + start
                abs_end = int(seg.start_m or 0) + end
                lines.append((0, 0, {
                    'station_label': f"{abs_start}-{abs_end}",
                    'irr_459_count': 0,
                    'irr_610_count': 0,
                    'irr_gt10_count': 0,
                }))
                start += step
            res['line_ids'] = lines
        return res

    def action_apply(self):
        self.ensure_one()
        seg = self.segment_id
        if not seg:
            raise ValidationError(_('لا يوجد مقطع محدد.'))
        sum_459 = sum(self.line_ids.mapped('irr_459_count'))
        sum_610 = sum(self.line_ids.mapped('irr_610_count'))
        sum_gt10 = sum(self.line_ids.mapped('irr_gt10_count'))
        seg.write({
            'irr_459_count': int(sum_459 or 0),
            'irr_610_count': int(sum_610 or 0),
            'irr_gt10_count': int(sum_gt10 or 0),
        })
        return { 'type': 'ir.actions.act_window_close' }


class PLRSegmentInputLineWizard(models.TransientModel):
    _name = 'plr.segment.input.line.wizard'
    _description = 'PLR Segment Input Line Wizard'

    wizard_id = fields.Many2one('plr.segment.input.wizard', string='المعالج', required=True, ondelete='cascade')
    station_label = fields.Char(string='المحطة (50 م)')

    irr_459_count = fields.Integer(string='4.0–5.9 مم', default=0)
    irr_610_count = fields.Integer(string='6.0–10.0 مم', default=0)
    irr_gt10_count = fields.Integer(string='> 10 مم', default=0)

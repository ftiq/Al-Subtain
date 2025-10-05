# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from math import ceil
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
            task = seg.task_id
            step = int(getattr(task, 'plr_reading_step', 50) or 50)
            start_m = int(seg.start_m or 0)
            end_m = int(seg.end_m or 0)
            if end_m < start_m:
                end_m = start_m

            start_index = (start_m // step) + 1
            end_index = int(ceil(end_m / float(step)))

            lines = []
            Reading = self.env['project.task.plr.reading']
            for idx in range(start_index, end_index + 1):
                start_abs = (idx - 1) * step
                end_abs = min(idx * step, end_m)
                reading = Reading.search([('task_id', '=', task.id), ('reading_index', '=', idx)], limit=1)
                if not reading:

                    reading = Reading.create({
                        'task_id': task.id,
                        'reading_index': idx,
                        'station_label': f"{start_abs}-{end_abs}",
                        'irr_459_count': 0,
                        'irr_610_count': 0,
                        'irr_gt10_count': 0,
                    })
                lines.append((0, 0, {
                    'station_label': reading.station_label or f"{start_abs}-{end_abs}",
                    'irr_459_count': int(reading.irr_459_count or 0),
                    'irr_610_count': int(reading.irr_610_count or 0),
                    'irr_gt10_count': int(reading.irr_gt10_count or 0),
                }))
            res['line_ids'] = lines
        return res

    def action_apply(self):
        self.ensure_one()
        seg = self.segment_id
        if not seg:
            raise ValidationError(_('لا يوجد مقطع محدد.'))

        task = seg.task_id
        step = int(getattr(task, 'plr_reading_step', 50) or 50)
        start_m = int(seg.start_m or 0)
        start_index = (start_m // step) + 1
        Reading = self.env['project.task.plr.reading']
        for offset, wl in enumerate(self.line_ids.sorted('id'), start=0):
            idx = start_index + offset
            reading = Reading.search([('task_id', '=', task.id), ('reading_index', '=', idx)], limit=1)
            vals = {
                'irr_459_count': int(wl.irr_459_count or 0),
                'irr_610_count': int(wl.irr_610_count or 0),
                'irr_gt10_count': int(wl.irr_gt10_count or 0),
            }
            if reading:
                reading.write(vals)
            else:
                Reading.create({
                    'task_id': task.id,
                    'reading_index': idx,
                    'station_label': wl.station_label or '',
                    **vals,
                })


        end_m = int(seg.end_m or 0)
        end_index = int(ceil(end_m / float(step)))
        readings = Reading.search([
            ('task_id', '=', task.id),
            ('reading_index', '>=', (start_m // step) + 1),
            ('reading_index', '<=', end_index),
        ])
        seg.write({
            'irr_459_count': int(sum(readings.mapped('irr_459_count')) or 0),
            'irr_610_count': int(sum(readings.mapped('irr_610_count')) or 0),
            'irr_gt10_count': int(sum(readings.mapped('irr_gt10_count')) or 0),
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

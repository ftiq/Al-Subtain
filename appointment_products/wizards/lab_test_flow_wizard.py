# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class LabTestFlowWizard(models.TransientModel):
    _name = 'lab.test.flow.wizard'
    _description = 'معالج إنشاء خطة الفحص'

    template_id = fields.Many2one('lab.test.flow.template', string='قالب الخطة', required=True)
    sample_id = fields.Many2one('lab.sample', string='العينة', required=True)

    def action_create_flow(self):
        self.ensure_one()
        if not self.template_id.line_ids:
            raise UserError(_('القالب المختار لا يحتوي على مراحل!'))

        flow = self.env['lab.test.flow'].create({
            'name': f"خطة {self.template_id.name} / {self.sample_id.name}",
            'template_id': self.template_id.id,
            'sample_id': self.sample_id.id,
        })

    
        for line in self.template_id.line_ids:
            self.env['lab.test.flow.line'].create({
                'flow_id': flow.id,
                'sequence': line.sequence,
                'test_template_id': line.test_template_id.id,
                'sample_qty': line.sample_qty,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lab.test.flow',
            'res_id': flow.id,
            'view_mode': 'form',
            'target': 'current',
        } 
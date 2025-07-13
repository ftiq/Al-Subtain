# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectTaskSignatureWizard(models.TransientModel):
    _name = 'project.task.signature.wizard'
    _description = 'Task Signature Wizard'

    task_id = fields.Many2one('project.task', string='Task', required=True)
    signature = fields.Binary(string='Signature', attachment=True, required=True)

    def action_save_signature(self):
        for wizard in self:
            if wizard.signature:
                wizard.task_id.fsm_signature = wizard.signature
        return {'type': 'ir.actions.act_window_close'} 
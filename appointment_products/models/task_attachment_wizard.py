# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class TaskAttachmentWizard(models.TransientModel):
    _name = 'task.attachment.wizard'
    _description = 'معالج مرفقات المهام'

    task_id = fields.Many2one(
        'project.task', 
        string='المهمة', 
        required=True
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='المرفقات'
    )
    
    def action_attach_files(self):
        """إرفاق الملفات للمهمة"""
        for wizard in self:
            if wizard.attachment_ids:
                wizard.attachment_ids.write({
                    'res_model': 'project.task',
                    'res_id': wizard.task_id.id
                })
        return {'type': 'ir.actions.act_window_close'} 
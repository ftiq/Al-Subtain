# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockPickingTaskLink(models.Model):
    _inherit = 'stock.picking'

    task_id = fields.Many2one('project.task', string='Task', compute='_compute_task', store=False)

    def action_open_task_signature(self):
        """Open the Field Service task signature wizard/worksheet for the related task."""
        self.ensure_one()
        if not self.task_id:
            return False
        if hasattr(self.task_id, 'action_preview_worksheet'):
            return self.task_id.action_preview_worksheet()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.task_id.id,
        }

    def _compute_task(self):
        for picking in self:
            picking.task_id = self.env['project.task'].search([('stock_receipt_id', '=', picking.id)], limit=1)

    def action_open_task(self):
        self.ensure_one()
        if not self.task_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.task_id.id,
        } 
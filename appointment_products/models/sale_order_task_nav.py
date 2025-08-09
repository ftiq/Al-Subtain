# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleOrderTaskNav(models.Model):
    _inherit = 'sale.order'



    task_id = fields.Many2one(
        'project.task',
        string='Task',
        compute='_compute_task_id',
        store=True,
        index=True,
        help='Primary task related to this quotation / sales order.'
    )

    @api.depends('order_line')
    def _compute_task_id(self):
        """Assign the first task linked to the sale order either directly (via
        sale_order_id) or through its order lines.  We purposefully depend
        only on ``order_line`` to avoid referencing optional fields that might
        not exist (e.g. ``order_line.task_id`` when *sale_project* is not
        installed).
        """
        Task = self.env['project.task']
        for order in self:
            task = order.task_id  
            
            if not task:
                for line in order.order_line:
                    if 'fsm_task_id' in line._fields and line.fsm_task_id:
                        task = line.fsm_task_id
                        break

                    if 'task_id' in line._fields and line.task_id:
                        task = line.task_id
                        break


            if not task:
                task = Task.search([('sale_order_id', '=', order.id)], limit=1)

            if not task:
                task = Task.search([('sale_line_id.order_id', '=', order.id)], limit=1)

            order.task_id = task

    def _get_related_task(self):
        self.ensure_one()
        task = self.task_id
        if task:
            return task
        task = self.env['project.task'].search([('sale_order_id', '=', self.id)], limit=1)
        if not task:
            task = self.env['project.task'].search([('sale_line_id.order_id', '=', self.id)], limit=1)
        return task

    def action_open_task(self):
        self.ensure_one()
        task = self._get_related_task()
        if not task:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Task'),
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': task.id,
        } 
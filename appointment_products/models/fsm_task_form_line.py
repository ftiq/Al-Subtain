# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FsmTaskFormLine(models.Model):
    _name = 'fsm.task.form.line'
    _description = 'FSM Task Form Products'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, 
                               domain=[('tracking', '=', 'serial')])
    quantity = fields.Float(string='Quantity', default=1.0)
    move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, ondelete='set null', copy=False)


    def open_move(self):
        """Open the detailed operation form for the related stock.move."""
        self.ensure_one()
        if not self.move_id:
            return False
        return self.move_id.action_show_details()

    def unlink(self):
        for line in self:
            move = line.move_id
            if move and move.state not in ('done', 'cancel'):
                move._action_cancel()
                move.unlink()
        return super().unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    form_line_ids = fields.One2many(
        'fsm.task.form.line',
        'task_id',
        string='النماذج',
        default=lambda self: self._default_form_lines()
    )

    @api.model
    def _default_form_lines(self):
        return [] 
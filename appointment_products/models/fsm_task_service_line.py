# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FsmTaskServiceLine(models.Model):
    _name = 'fsm.task.service.line'
    _description = 'FSM Task Service Products'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, domain=[('is_service_fsm', '=', True)])
    quantity = fields.Float(string='Quantity', default=0.0)
    price_unit = fields.Float(string='Unit Price', related='product_id.list_price', readonly=True, store=True)
    currency_id = fields.Many2one(related='product_id.currency_id', string='Currency', readonly=True, store=True)
    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', currency_field='currency_id', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    # -------------------------------------------------
    # Synchronization with Sale Order (Field Service)
    # -------------------------------------------------

    def _sync_sale_order_line(self):
        """Sync the quantity of this service line with the corresponding
        Sale Order Line that is linked to the task through Field-Service logic.

        Uses the standard `product.set_fsm_quantity` helper that already
        exists in `industry_fsm_sale` to ensure quantities are reflected in
        the task's Sale Order and to automatically create that Sale Order if
        it does not yet exist (via `_fsm_ensure_sale_order`).
        """
        for line in self:
            if not line.task_id:
                continue
            # We reuse the existing mechanism used by the Product Catalog
            # (`set_fsm_quantity`) so that we keep all native side-effects
            # (sale order creation, warranty handling, SN wizard, etc.).
            if line.quantity is None or line.quantity < 0:
                continue

            # If quantity is 0 and task has no sale order yet, no need to create one.
            if line.quantity == 0 and not line.task_id.sale_order_id:
                continue

            line.product_id.with_context(fsm_task_id=line.task_id.id).set_fsm_quantity(line.quantity)

    # -------------------------------------------------
    # ORM overrides
    # -------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._sync_sale_order_line()
        return lines

    def write(self, vals):
        res = super().write(vals)
        # Only sync when quantity or product changed or if task changed.
        if any(key in vals for key in ['quantity', 'product_id', 'task_id']):
            self._sync_sale_order_line()
        return res


class ProjectTask(models.Model):
    _inherit = 'project.task'

    service_line_ids = fields.One2many(
        'fsm.task.service.line',
        'task_id',
        string='Service Products',
        default=lambda self: self._default_service_lines()
    )

    @api.model
    def _default_service_lines(self):
        # Previously we pre-populated all service products with quantity 0 on
        # each new task. That created clutter on every FSM task. Now we return
        # an empty list so lines are added only when needed by the user.
        return [] 
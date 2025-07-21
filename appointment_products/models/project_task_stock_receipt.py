# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTaskStockReceipt(models.Model):
    _inherit = 'project.task'

    stock_receipt_id = fields.Many2one('stock.picking', string='Stock Receipt', copy=False, readonly=True)
    

    planned_concrete_m3 = fields.Float(
        related='stock_receipt_id.planned_concrete_m3', 
        store=False, readonly=False, 
        string='Planned Concrete (m³)'
    )
    concrete_sample_type_id = fields.Many2one(
        related='stock_receipt_id.concrete_sample_type_id',
        store=False, readonly=False,
        string='Concrete Sample Type'
    )
    enable_reserve_samples = fields.Boolean(
        related='stock_receipt_id.enable_reserve_samples',
        store=False, readonly=False,
        string='Enable Reserve Samples'
    )
    concrete_sample_subtype_id = fields.Many2one(
        related='stock_receipt_id.concrete_sample_subtype_id',
        store=False, readonly=False,
        string='Concrete Sample Subtype'
    )
    estimated_samples = fields.Integer(
        related='stock_receipt_id.estimated_samples',
        store=False, readonly=True,
        string='Estimated Samples'
    )
    estimated_cubes = fields.Integer(
        related='stock_receipt_id.estimated_cubes',
        store=False, readonly=True,
        string='Estimated Cubes'
    )
    enable_7_days_samples = fields.Boolean(
        related='stock_receipt_id.enable_7_days_samples',
        store=False, readonly=False,
        string='Enable 7 Days Samples'
    )
    sampling_notes = fields.Text(
        related='stock_receipt_id.sampling_notes',
        store=False, readonly=False,
        string='Sampling Notes'
    )
    move_lines_with_codes_count = fields.Integer(
        related='stock_receipt_id.move_lines_with_codes_count',
        store=False, readonly=True,
        string='Move Lines Count'
    )
    move_line_ids = fields.One2many(
        related='stock_receipt_id.move_line_ids',
        store=False, readonly=False,
        string='Move Lines'
    )
    has_concrete_product = fields.Boolean(
        string='Has Concrete Product',
        compute='_compute_has_concrete_product',
        store=False,
        help='Determines if task has any concrete product'
    )

    @api.depends('form_line_ids.sample_type_id')
    def _compute_has_concrete_product(self):
        """Check if task has any concrete type product."""
        for task in self:
            task.has_concrete_product = any(
                line.sample_type_id and 'CONCRETE' in (line.sample_type_id.code or '') 
                for line in task.form_line_ids
            )

    def _create_stock_receipt(self):
        """Create an incoming picking for the serial-tracked products listed on the form lines.
        The partner ("Receipt From") is set to the current user's partner.  This method is
        automatically called the first time the task is saved with form lines.
        """
        self.ensure_one()
        if not self.form_line_ids:
            return False
        

        if self.stock_receipt_id:
            return self.stock_receipt_id

        PickingType = self.env['stock.picking.type']
        picking_type = PickingType.search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not picking_type:
            raise UserError(_('No incoming operation type found for the current company.'))

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'partner_id': self.env.user.partner_id.id,
            'origin': self.name or _('Task %s') % self.id,
            'user_id': self.env.user.id,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        Move = self.env['stock.move']
        for line in self.form_line_ids:
            vals = {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity or 1.0,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'company_id': self.env.company.id,
            }
            move = Move.create(vals)
            line.move_id = move

        picking.action_confirm()
        self.stock_receipt_id = picking
        return picking

    def _ensure_moves_for_form_lines(self):
        """For tasks that already have a picking, create stock.move for any
        form_line that does not yet have one (with anti-duplication protection)."""
        for task in self.filtered(lambda t: t.stock_receipt_id):
            picking = task.stock_receipt_id
            Move = self.env['stock.move']
            new_lines = task.form_line_ids.filtered(lambda l: not l.move_id)
            
            for line in new_lines:

                existing_move = Move.search([
                    ('picking_id', '=', picking.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', 'not in', ['done', 'cancel'])
                ], limit=1)
                
                if existing_move:

                    line.move_id = existing_move

                    if existing_move.product_uom_qty != (line.quantity or 1.0):
                        existing_move.write({'product_uom_qty': line.quantity or 1.0})
                else:

                    move_vals = {
                        'name': line.product_id.display_name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity or 1.0,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'picking_id': picking.id,
                        'company_id': task.env.company.id,
                    }
                    move = Move.create(move_vals)
                    line.move_id = move

            if new_lines:
                picking.action_confirm()

    def _ensure_service_sync(self):
        """Call _sync_sale_order_line on each service line to ensure SO lines
        are created/updated. Avoid duplication: that helper method handles
        quantity logic itself."""
        ServiceLine = self.env['fsm.task.service.line']
        for task in self:
            for line in task.service_line_ids:
                if line.quantity is not None:
                    ServiceLine.browse(line.id)._sync_sale_order_line()

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if task.form_line_ids and not task.stock_receipt_id:
                task._create_stock_receipt()
            else:
                task._ensure_moves_for_form_lines()
            task._ensure_service_sync()
        return tasks

    def write(self, vals):
        res = super().write(vals)

        for task in self:
            if task.form_line_ids:
                if not task.stock_receipt_id:
                    task._create_stock_receipt()
                else:
                    task._ensure_moves_for_form_lines()
                task._ensure_service_sync()
            else:
                task._ensure_service_sync()
        return res

    def action_open_concrete_sampling(self):
        """Open concrete sampling interface for the related stock picking."""
        self.ensure_one()
        if not self.stock_receipt_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Concrete Sampling'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_receipt_id.id,
            'context': {
                'default_picking_type_id': self.stock_receipt_id.picking_type_id.id,
                'concrete_sample_domain': [('code', 'ilike', 'CONCRETE')],
            },
        }
        
    def action_recalculate_samples(self):
        """Recalculate samples for concrete sampling."""
        self.ensure_one()
        if self.stock_receipt_id:

            self.stock_receipt_id.action_recalculate_samples()

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return False
        
    def action_generate_samples(self):
        """Generate samples for concrete sampling."""
        self.ensure_one()
        if self.stock_receipt_id:

            self.stock_receipt_id.action_generate_samples()

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return False 
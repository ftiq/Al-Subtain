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
    seven_days_for_all_groups = fields.Boolean(
        related='stock_receipt_id.seven_days_for_all_groups',
        store=False, readonly=False,
        string='7 Days for All Groups'
    )
    reserve_for_all_groups = fields.Boolean(
        related='stock_receipt_id.reserve_for_all_groups',
        store=False, readonly=False,
        string='Reserve for All Groups'
    )
    is_signed = fields.Boolean(
        related='stock_receipt_id.is_signed',
        store=False, readonly=True,
        string='Is Signed'
    )
    sampling_notes = fields.Text(
        related='stock_receipt_id.sampling_notes',
        store=False, readonly=False,
        string='Sampling Notes'
    )
    auto_sample_generation = fields.Boolean(
        string='تفعيل الإنشاء الأوتوماتيكي للعينات',
        default=False,
        help='عند التفعيل: يتم إنشاء العينات تلقائياً حسب الكمية والنوع\nعند الإلغاء: يمكن إدخال العينات يدوياً'
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
        """Recalculate samples for concrete sampling - only if auto generation is enabled."""
        self.ensure_one()
        
        if not self.auto_sample_generation:
            raise UserError(_('الإنشاء الأوتوماتيكي للعينات غير مفعل. يرجى تفعيله أولاً أو إضافة العينات يدوياً.'))
        
        if self.stock_receipt_id:
            self.stock_receipt_id.action_recalculate_samples()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return False
    
    def action_add_manual_sample(self):
        """إضافة عينة واحدة يدوياً"""
        self.ensure_one()
        
        if self.auto_sample_generation:
            raise UserError(_('الإنشاء الأوتوماتيكي مفعل. يرجى إلغاء تفعيله لإضافة العينات يدوياً.'))
        
        if not self.stock_receipt_id:

            picking_vals = {
                'name': f'Samples - {self.name}',
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'origin': self.name,
            }
            self.stock_receipt_id = self.env['stock.picking'].create(picking_vals)
        
        existing_groups = self.move_line_ids.mapped('group_no')
        next_group = max(existing_groups) + 1 if existing_groups else 1
        
        if not self.stock_receipt_id.move_ids:

            product = self.env['product.product'].search([('name', 'ilike', 'خرسانة')], limit=1)
            if not product:
                product = self.env['product.product'].browse(1) 
            

            product_uom = product.uom_id if product.uom_id else self.env.ref('uom.product_uom_unit')
            
            move_vals = {
                'name': 'Manual Sample',
                'picking_id': self.stock_receipt_id.id,
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product_uom.id,
                'location_id': self.stock_receipt_id.location_id.id,
                'location_dest_id': self.stock_receipt_id.location_dest_id.id,
            }
            move = self.env['stock.move'].create(move_vals)
        else:
            move = self.stock_receipt_id.move_ids[0]

            if not move.product_uom:
                move.product_uom = move.product_id.uom_id if move.product_id.uom_id else self.env.ref('uom.product_uom_unit')

        cube_count = 3 
        line_vals = {
            'move_id': move.id,
            'picking_id': self.stock_receipt_id.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'qty_done': float(cube_count), 
            'group_no': next_group,
            'field_code': '',
            'field_serial': '',
            'age_days': '28',
            'sample_quantity': 3,
            'cube_count': cube_count,
        }
        self.env['stock.move.line'].create(line_vals)
        
        self._update_move_demand_quantity()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _update_move_demand_quantity(self):
        """تحديث الكمية المطلوبة في الحركة لتتطابق مع الكميات المنجزة"""
        self.ensure_one()
        if self.stock_receipt_id and self.stock_receipt_id.move_ids:
            for move in self.stock_receipt_id.move_ids:
                total_qty_done = sum(move.move_line_ids.mapped('qty_done'))
                if total_qty_done > 0 and move.product_uom_qty != total_qty_done:
                    move.write({'product_uom_qty': total_qty_done})

    def action_generate_codes(self):
        """دالة معطلة - الرموز الحقلية يدخلها العميل بنفسه"""
        self.ensure_one()
        raise UserError(_('توليد الرموز الحقلية معطل. يرجى إدخال الرموز يدوياً في الحقول المخصصة.'))
    
    def action_clear_samples(self):
        """حذف جميع العينات الموجودة"""
        self.ensure_one()
        
        if self.move_line_ids:
            self.move_line_ids.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
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
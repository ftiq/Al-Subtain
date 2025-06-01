from odoo import models, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    SAMPLE_PRODUCT_ID = 735  # Product ID for "العينات المستلمة"

    def action_confirm(self):
        res = super().action_confirm()
        # Remove the standard delivery pickings for sample product
        for picking in self.picking_ids:
            for move in picking.move_lines:
                if move.product_id.id == self.SAMPLE_PRODUCT_ID:
                    picking.unlink()
                    break

        picking_type = self.env.ref('stock.picking_type_in')  # Receipt
        location_dest = self.env.ref('stock.stock_location_stock')
        location_src = self.env.ref('stock.stock_location_customers')

        sample_lines = self.order_line.filtered(lambda l: l.product_id.id == self.SAMPLE_PRODUCT_ID)
        if sample_lines:
            picking = self.env['stock.picking'].create({
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': location_src.id,
                'location_dest_id': location_dest.id,
                'origin': self.name,
            })
            for line in sample_lines:
                move = self.env['stock.move'].create({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'location_id': location_src.id,
                    'location_dest_id': location_dest.id,
                    'picking_id': picking.id,
                })
                move._action_confirm()
                move._action_assign()

        return res

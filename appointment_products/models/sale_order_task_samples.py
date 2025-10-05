# -*- coding: utf-8 -*-
from odoo import models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _appointment_products_get_samples_per_unit(self, sample_product_tmpl):
        """Return samples_per_unit for the given *sample* product template.
        1. If there is a specific parameter for that product (appointment_products.samples_per_unit_<id>) use it.
        2. Otherwise fall back to the generic parameter appointment_products.samples_per_unit.
        If nothing is set, default to 50000.
        """
        icp = self.env['ir.config_parameter'].sudo()
        specific_key = f'appointment_products.samples_per_unit_{sample_product_tmpl.id}'
        specific_val = icp.get_param(specific_key)
        if specific_val and str(specific_val).isdigit():
            return int(specific_val)

        generic_val = icp.get_param('appointment_products.samples_per_unit')
        if generic_val and str(generic_val).isdigit():
            return int(generic_val)
        return 50000

    def action_confirm(self):
        """After confirming the quotation, update `total_samples_count` on every
        FSM task that comes from a product having `related_sample_product_id`.
        The value is: quantity * samples_per_unit (from settings).
        """
        self = self.with_context(skip_lab_sample_creation_on_sale_confirm=True)
        res = super().action_confirm()

        for order in self:
            for line in order.order_line:
                task = line.task_id
                if not task:
                    continue

                related_sample = line.product_id.product_tmpl_id.related_sample_product_id
                if not related_sample:
                    continue

                samples_per_unit = self._appointment_products_get_samples_per_unit(related_sample)

                total_samples = int(line.product_uom_qty * samples_per_unit)

                task.with_context(bypass_samples_update=True).sudo().write({'total_samples_count': total_samples})


                sample_product_variant = self.env['product.product'].search(
                    [('product_tmpl_id', '=', related_sample.id)], limit=1)
                if not sample_product_variant:
                    continue

                expected_qty = max(1, int(-(-total_samples // samples_per_unit)))

                existing_line = task.form_line_ids.filtered(lambda l: l.product_id.id == sample_product_variant.id)

                if existing_line:
                    existing_line.with_context(bypass_quantity_check=True).sudo().write({'quantity': expected_qty})
                    existing_line._update_stock_move_quantity()
                else:
                    task.form_line_ids = [(0, 0, {
                        'product_id': sample_product_variant.id,
                        'quantity': expected_qty,
                    })]

        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, vals):
        """Override write to update task samples and prices when quantity changes (unless bypassed)"""
        if 'product_uom_qty' in vals and not self.env.context.get('bypass_task_samples_update'):
            old_values = {}
            for line in self:
                old_values[line.id] = line.product_uom_qty
        
        result = super().write(vals)
        
        if 'product_uom_qty' in vals and not self.env.context.get('bypass_task_samples_update'):
            for line in self:
                if line.product_uom_qty != old_values.get(line.id, 0):
                    line._update_task_samples_from_line_qty()
                    
                    if line.order_id.state in ('draft', 'sent'):
                        try:
                            if line.task_id:
                                line.task_id._trigger_sale_line_recalculation(line)
                            else:
                                line.invalidate_recordset(['price_unit', 'price_subtotal', 'price_total'])
                                line._compute_price_unit()
                                line._compute_amount()
                                line.order_id._amount_all()
                        except Exception:
                            pass
        
        return result

    def _update_task_samples_from_line_qty(self):
        """Update task total_samples_count when sale order line quantity changes"""
        self.ensure_one()
        
        if not self.task_id:
            return
            
        related_sample = self.product_id.product_tmpl_id.related_sample_product_id
        if not related_sample:
            return
        
        samples_per_unit = self.order_id._appointment_products_get_samples_per_unit(related_sample)
        total_samples = int(self.product_uom_qty * samples_per_unit)
        
        if self.task_id.total_samples_count != total_samples:
            self.task_id.with_context(bypass_samples_update=True).sudo().write({
                'total_samples_count': total_samples
            })
            
            sample_product_variant = self.env['product.product'].search(
                [('product_tmpl_id', '=', related_sample.id)], limit=1)
                
            if sample_product_variant:
                expected_qty = max(1, int(-(-total_samples // samples_per_unit)))
                existing_line = self.task_id.form_line_ids.filtered(
                    lambda l: l.product_id.id == sample_product_variant.id)
                
                if existing_line:
                    existing_line.with_context(bypass_quantity_check=True).sudo().write({
                        'quantity': expected_qty
                    })
                    existing_line._update_stock_move_quantity()


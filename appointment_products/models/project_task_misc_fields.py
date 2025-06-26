# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import math


class ProjectTaskMiscFields(models.Model):
    _inherit = 'project.task'

    move_ids_display = fields.Char(string='Moves Summary', readonly=True, copy=False)

    total_samples_count = fields.Integer(
        string='العدد الكلي للعينات',
        default=0,
        help='العدد الإجمالي للعينات المطلوبة في هذه المهمة'
    )
    

    book_number = fields.Char(
        string='رقم الكتاب',
        help='رقم الكتاب المرجعي للمهمة'
    )
    
    book_date = fields.Date(
        string='تاريخ الكتاب',
        help='تاريخ الكتاب الوارد'
    )
    
    modeling_date = fields.Date(
        string='تاريخ النمذجة',
        help='التاريخ المنفذ للنمذجة'
    )


    book_notes = fields.Html(
        string='الملاحظات',
        help='ملاحظات إضافية تخص الكتاب أو النمذجة'
    )

    @api.onchange('total_samples_count')
    def _onchange_total_samples_count(self):
        """حفظ تلقائي عند تغيير العدد الكلي للعينات وإنشاء سجل بمنتج العينات"""
        if self.total_samples_count > 0:

            samples_per_unit = int(self.env['ir.config_parameter'].sudo().get_param(
                'appointment_products.samples_per_unit', 50000
            ))
            

            calculated_quantity = math.ceil(self.total_samples_count / samples_per_unit)
            

            sample_product_template = self.env['product.template'].search([
                ('is_sample_product', '=', True)
            ], limit=1)
            
            if sample_product_template:

                sample_product = self.env['product.product'].search([
                    ('product_tmpl_id', '=', sample_product_template.id)
                ], limit=1)
                
                if sample_product:

                    existing_line = self.form_line_ids.filtered(
                        lambda line: line.product_id.id == sample_product.id
                    )
                    
                    if existing_line:


                        existing_line[0].with_context(bypass_quantity_check=True).write({
                            'quantity': calculated_quantity
                        })

                        existing_line[0]._update_stock_move_quantity()
                    else:

                        new_line_vals = {
                            'product_id': sample_product.id,
                            'quantity': calculated_quantity,
                        }

                        self.form_line_ids = [(0, 0, new_line_vals)]
            

            if self.id:
                try:
                    self.sudo().write({'total_samples_count': self.total_samples_count})
                except Exception:
                    pass
        else:

            sample_lines = self.form_line_ids.filtered(
                lambda line: line.product_id.product_tmpl_id.is_sample_product
            )
            if sample_lines:
                sample_lines.unlink()



    def action_open_receipt(self):
        """Open the stock receipt linked to the task (stock_receipt_id)."""
        self.ensure_one()
        if not self.stock_receipt_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_receipt_id.id,
        }

    def action_open_sale_order(self):
        """Open the sale order linked to the task, if any."""
        self.ensure_one()
        if not self.sale_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        } 
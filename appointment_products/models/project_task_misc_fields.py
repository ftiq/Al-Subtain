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

    appointment_datetime = fields.Datetime(string='موعد الحجز', related='sale_order_id.appointment_datetime', store=True)


    stock_done = fields.Boolean(string='انتهت المهمة المخزنية', default=False, tracking=True)
    stock_done_date = fields.Datetime(string='تاريخ إنهاء المخزون', tracking=True)

    def write(self, vals):
        """Override write to handle total_samples_count changes properly"""

        if 'total_samples_count' in vals and not self.env.context.get('bypass_samples_update'):
            old_values = {}
            for task in self:
                old_values[task.id] = task.total_samples_count
        
        result = super().write(vals)
        

        if 'total_samples_count' in vals and not self.env.context.get('bypass_samples_update'):
            for task in self:
                if task.total_samples_count != old_values.get(task.id, 0):
                    task.with_context(bypass_samples_update=True)._update_samples_related_data()
        
        return result

    def _update_samples_related_data(self):
        """Update form lines and sale order line when total_samples_count changes"""
        self.ensure_one()
        
        if self.total_samples_count > 0:

            samples_per_unit = self._get_samples_per_unit_for_task()
            calculated_quantity = math.ceil(self.total_samples_count / samples_per_unit)
            

            self._update_form_lines_for_samples(calculated_quantity)
            

            self._update_sale_order_line_for_samples()
        else:

            sample_lines = self.form_line_ids.filtered(
                lambda line: line.product_id.product_tmpl_id.is_sample_product
            )
            if sample_lines:
                sample_lines.unlink()

    def _get_samples_per_unit_for_task(self):
        """Get samples per unit for this task based on settings"""

        if self.sale_order_id:
            for line in self.sale_order_id.order_line:
                if line.task_id == self:
                    related_sample = line.product_id.product_tmpl_id.related_sample_product_id
                    if related_sample:
                        return self.sale_order_id._appointment_products_get_samples_per_unit(related_sample)
        

        return int(self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.samples_per_unit', 50000
        ))

    def _update_form_lines_for_samples(self, calculated_quantity):
        """Update form lines with calculated quantity for the correct sample product"""

        related_sample_product = None
        if self.sale_order_id:
            for line in self.sale_order_id.order_line:
                if line.task_id == self:
                    related_sample = line.product_id.product_tmpl_id.related_sample_product_id
                    if related_sample:

                        related_sample_product = self.env['product.product'].search([
                            ('product_tmpl_id', '=', related_sample.id)
                        ], limit=1)
                        break
        

        if not related_sample_product:
            sample_product_template = self.env['product.template'].search([
                ('is_sample_product', '=', True)
            ], limit=1)
            
            if sample_product_template:
                related_sample_product = self.env['product.product'].search([
                    ('product_tmpl_id', '=', sample_product_template.id)
                ], limit=1)
        
        if related_sample_product:

            wrong_sample_lines = self.form_line_ids.filtered(
                lambda line: line.product_id.product_tmpl_id.is_sample_product and 
                           line.product_id.id != related_sample_product.id
            )
            if wrong_sample_lines:
                wrong_sample_lines.unlink()
            

            existing_line = self.form_line_ids.filtered(
                lambda line: line.product_id.id == related_sample_product.id
            )
            
            if existing_line:
                existing_line[0].with_context(bypass_quantity_check=True).write({
                    'quantity': calculated_quantity
                })
                existing_line[0]._update_stock_move_quantity()
            else:
                new_line_vals = {
                    'product_id': related_sample_product.id,
                    'quantity': calculated_quantity,
                }
                self.form_line_ids = [(0, 0, new_line_vals)]

    def _trigger_sale_line_recalculation(self, sale_line):
        """Trigger proper recalculation of sale order line like UI would do"""
        try:

            sale_line.invalidate_cache()
            

            with sale_line.env.do_in_onchange():

                sale_line.with_context(bypass_task_samples_update=True)._compute_price_unit()
                sale_line.with_context(bypass_task_samples_update=True)._compute_amount()
                sale_line.with_context(bypass_task_samples_update=True)._compute_tax_id()
                

                if hasattr(sale_line, '_compute_name'):
                    sale_line.with_context(bypass_task_samples_update=True)._compute_name()
            

            sale_line.order_id._amount_all()
            
        except Exception as e:

            sale_line.with_context(bypass_task_samples_update=True)._compute_amount()
            sale_line.order_id._amount_all()

    def _update_sale_order_line_for_samples(self):
        """Update sale order line quantity and price based on total_samples_count"""
        if not self.sale_order_id:
            return
        

        task_line = self.sale_order_id.order_line.filtered(lambda l: l.task_id == self)
        if not task_line:
            return
        
        task_line = task_line[0]
        related_sample = task_line.product_id.product_tmpl_id.related_sample_product_id
        if not related_sample:
            return
        

        samples_per_unit = self.sale_order_id._appointment_products_get_samples_per_unit(related_sample)
        if samples_per_unit > 0:
            required_quantity = math.ceil(self.total_samples_count / samples_per_unit)
            

            if task_line.product_uom_qty != required_quantity:

                old_quantity = task_line.product_uom_qty
                old_subtotal = task_line.price_subtotal
                

                task_line.with_context(bypass_task_samples_update=True).write({
                    'product_uom_qty': required_quantity
                })
                

                if self.sale_order_id.state in ('draft', 'sent'):

                    self._trigger_sale_line_recalculation(task_line)
                


            icp = self.env['ir.config_parameter'].sudo()
            apply_disc = icp.get_param('appointment_products.apply_discount_incomplete_samples', 'False') == 'True'
            if apply_disc:
                expected_samples = required_quantity * samples_per_unit
                actual_samples = self.total_samples_count
                if expected_samples and actual_samples < expected_samples:
                    discount_percent = round((expected_samples - actual_samples) / expected_samples * 100, 2)
                else:
                    discount_percent = 0.0
                if abs(task_line.discount - discount_percent) > 0.01:
                    task_line.with_context(bypass_task_samples_update=True).write({'discount': discount_percent})
                    if self.sale_order_id.state in ('draft', 'sent'):
                        self._trigger_sale_line_recalculation(task_line)
            else:
                if task_line.discount:
                    task_line.with_context(bypass_task_samples_update=True).write({'discount': 0})
                    if self.sale_order_id.state in ('draft', 'sent'):
                        self._trigger_sale_line_recalculation(task_line)


    @api.onchange('total_samples_count')
    def _onchange_total_samples_count(self):
        """Onchange for total samples count - no warning needed"""
        pass

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

    def action_mark_stock_done(self):
        """يستدعيه مستخدم المخزون عند إنهاء جزء المخزون للمهمة.
        • يحدد الحقل stock_done ويُسجّل التاريخ.
        • يرسل إشعاراً ونشاطاً لمجموعة المختبر.
        """
        ActivityType = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        lab_group = self.env.ref('appointment_products.group_lab_inspector', raise_if_not_found=False)

        for task in self:
            if task.stock_done:
                continue

            task.write({
                'stock_done': True,
                'stock_done_date': fields.Datetime.now(),
            })


            task.message_post(body=_('تم إنهاء المهمة المخزنية. بانتظار الفحص المختبري.'))


            if ActivityType and lab_group:
                for user in lab_group.users:
                    task.activity_schedule(
                        ActivityType.id,
                        user_id=user.id,
                        summary=_('بدء الفحص المختبري'),
                        note=_('يرجى البدء بإجراءات الفحص بعد إنهاء المخزون.')
                    )
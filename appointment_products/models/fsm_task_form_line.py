# -*- coding: utf-8 -*-
import ast
import logging
import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class FsmTaskFormLine(models.Model):
    _name = 'fsm.task.form.line'
    _description = 'FSM Task Form Products'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        ondelete='cascade',
        index=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('product_tmpl_id.is_sample_product', '=', True)],
        index=True
    )


    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع العينة',
        related='product_id.product_tmpl_id.sample_type_id',
        store=True,
        readonly=True
    )


    sample_subtype_id = fields.Many2one(
        'lab.sample.subtype',
        string='النوع',
        domain="[('sample_type_id', '=', sample_type_id)]",
        help='النوع الفرعي للعينة المرتبط بنوع العينة المحدد للمنتج'
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_subtype_domain(self):
        """تحديث نطاق الأنواع الفرعية عند تغيير المنتج"""
        if self.product_id and self.product_id.product_tmpl_id.sample_type_id:
            sample_type = self.product_id.product_tmpl_id.sample_type_id.id
            return {
                'domain': {'sample_subtype_id': [('sample_type_id', '=', sample_type)]},
                'value': {'sample_subtype_id': False}
            }
        return {
            'domain': {'sample_subtype_id': []},
            'value': {'sample_subtype_id': False}
        }
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        help='الكمية المطلوبة من المنتج'
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        readonly=True,
        ondelete='set null',
        copy=False,
        index=True
    )

    @api.model
    def _get_approval_managers(self):
        """جلب قائمة مديري الموافقة من الإعدادات"""
        try:
            approval_manager_ids = self.env['ir.config_parameter'].sudo().get_param(
                'appointment_products.approval_manager_ids', '[]'
            )

            if not approval_manager_ids or approval_manager_ids == 'False':
                return []

            try:
                result = ast.literal_eval(approval_manager_ids)
                if isinstance(result, (list, tuple)):
                    return [int(x) for x in result if str(x).isdigit()]
                elif isinstance(result, (int, str)) and str(result).isdigit():
                    return [int(result)]
                else:
                    return []
            except (ValueError, SyntaxError, TypeError):
                try:
                    if ',' in approval_manager_ids:
                        return [int(x.strip()) for x in approval_manager_ids.split(',') if x.strip().isdigit()]
                    elif approval_manager_ids.strip().isdigit():
                        return [int(approval_manager_ids.strip())]
                    else:
                        return []
                except Exception as e:
                    _logger.warning("خطأ في تحليل معرفات مديري الموافقة: %s", str(e))
                    return []

        except Exception as e:
            _logger.error("خطأ في جلب مديري الموافقة: %s", str(e))
            return []

    @api.model
    def _is_approval_manager(self):
        """التحقق من أن المستخدم الحالي مدير موافقة"""
        approval_manager_ids = self._get_approval_managers()
        if not isinstance(approval_manager_ids, (list, tuple)):
            return False
        return self.env.user.id in approval_manager_ids

    @api.model
    def _calculate_default_quantity(self, total_samples):
        """حساب الكمية الافتراضية بناءً على عدد العينات"""
        try:
            if total_samples <= 0:
                return 1.0

            samples_per_unit = int(self.env['ir.config_parameter'].sudo().get_param(
                'appointment_products.samples_per_unit', 50000
            ))

            if samples_per_unit <= 0:
                _logger.warning("قيمة samples_per_unit غير صحيحة: %s", samples_per_unit)
                samples_per_unit = 50000

            result = math.ceil(total_samples / samples_per_unit)
            return max(result, 1.0)  

        except Exception as e:
            _logger.error("خطأ في حساب الكمية الافتراضية: %s", str(e))
            return 1.0

    @api.onchange('quantity')
    def _onchange_quantity(self):
        """إظهار تحذير عند تغيير الكمية"""
        if not self.task_id or not self.task_id.total_samples_count:
            return

        expected_quantity = self._calculate_default_quantity(self.task_id.total_samples_count)

        if self.quantity == expected_quantity:
            return

        if self._is_approval_manager():
            return {
                'warning': {
                    'title': _('تحذير - تغيير الكمية'),
                    'message': _(
                        'تم تغيير الكمية من القيمة الافتراضية المحسوبة.\n'
                        'الكمية الافتراضية: %s\n'
                        'الكمية المدخلة: %s\n'
                        'عدد العينات: %s\n\n'
                        'يمكنك المتابعة لأن لديك صلاحيات الموافقة.'
                    ) % (expected_quantity, self.quantity, self.task_id.total_samples_count)
                }
            }

        self.quantity = expected_quantity
        return {
            'warning': {
                'title': _('ليس لديك الصلاحية!'),
                'message': _(
                    'ليس لديك الصلاحية لتغيير الكمية!\n'
                    'تم إرجاع الكمية للقيمة الافتراضية: %s\n'
                    'عدد العينات: %s\n\n'
                    'يرجى التواصل مع مدير الموافقة لإجراء هذا التغيير.'
                ) % (expected_quantity, self.task_id.total_samples_count)
            }
        }

    @api.constrains('quantity')
    def _check_quantity_permission(self):
        """التحقق من صلاحية تغيير الكمية"""
        if self.env.context.get('bypass_quantity_check'):
            return

        for line in self:
            if not line.task_id or not line.task_id.total_samples_count:
                continue

            expected_quantity = line._calculate_default_quantity(line.task_id.total_samples_count)

            if line.quantity == expected_quantity:
                continue

            if line._is_approval_manager():
                line.task_id.message_post(
                    body=_('تحذير: تم تغيير كمية منتج العينات من %s إلى %s بواسطة %s (مدير موافقة)') % (
                        expected_quantity, line.quantity, self.env.user.name
                    ),
                    message_type='comment'
                )
                continue

            raise ValidationError(_(
                'ليس لديك الصلاحية لتغيير الكمية!\n'
                'الكمية الافتراضية المحسوبة: %s\n'
                'الكمية المدخلة: %s\n'
                'عدد العينات: %s\n\n'
                'يرجى التواصل مع مدير الموافقة لإجراء هذا التغيير.'
            ) % (expected_quantity, line.quantity, line.task_id.total_samples_count))

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء خطوط جديدة مع التحقق من الصلاحيات"""
        lines = super().create(vals_list)
        lines._check_quantity_permission()
        for line in lines:
            if line.task_id and line.task_id.stock_receipt_id and not line.move_id:
                existing_move = self.env['stock.move'].search([
                    ('picking_id', '=', line.task_id.stock_receipt_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('origin', 'like', str(line.task_id.id)),
                    ('state', 'not in', ['done', 'cancel'])
                ], limit=1)

                if not existing_move:
                    line.task_id._ensure_moves_for_form_lines()
        return lines

    def write(self, vals):
        """تحديث الخطوط مع التحقق من الصلاحيات وتحديث حركات المخزون"""
        result = super().write(vals)
        if 'quantity' in vals:
            self._check_quantity_permission()
            self._update_stock_move_quantity()
        return result

    def _update_stock_move_quantity(self):
        """تحديث كمية حركة المخزون المرتبطة بالخط (مع حماية من التكرار)"""
        for line in self:
            if not line.move_id:
                if line.task_id and line.task_id.stock_receipt_id:
                    existing_move = self.env['stock.move'].search([
                        ('picking_id', '=', line.task_id.stock_receipt_id.id),
                        ('product_id', '=', line.product_id.id),
                        ('state', 'not in', ['done', 'cancel'])
                    ], limit=1)

                    if existing_move:
                        line.move_id = existing_move
                    else:
                        line.task_id._ensure_moves_for_form_lines()
                        return

            if line.move_id and line.move_id.state not in ('done', 'cancel'):
                if line.quantity <= 0:
                    line.move_id._action_cancel()
                    continue

                if line.move_id.product_uom_qty != line.quantity:
                    line.move_id.write({
                        'product_uom_qty': line.quantity
                    })


                    if line.move_id.state in ('confirmed', 'assigned', 'partially_available'):
                        line.move_id._do_unreserve()
                        try:
                            line.move_id._action_assign()
                        except:
                            pass

    def open_move(self):
        """Open the detailed operation form for the related stock.move with smart sample distribution."""
        self.ensure_one()
        if not self.move_id:
            return False


        self._distribute_samples_intelligently()

        return self.move_id.action_show_details()

    def _distribute_samples_intelligently(self):
        """توزيع العينات على سطور الحركة"""
        if not self.task_id or not self.task_id.total_samples_count or not self.move_id:
            return


        samples_per_unit = self._get_samples_per_unit_for_product()
        if not samples_per_unit:
            return

        total_samples = self.task_id.total_samples_count


        full_lines = int(total_samples // samples_per_unit)
        remaining_samples = total_samples % samples_per_unit


        existing_lines = self.move_id.move_line_ids


        required_lines = full_lines + (1 if remaining_samples > 0 else 0)
        if len(existing_lines) > required_lines:
            existing_lines[required_lines:].unlink()


        for i in range(required_lines):
            if i < len(existing_lines):
                line = existing_lines[i]
            else:

                line = self.env['stock.move.line'].create({
                    'move_id': self.move_id.id,
                    'product_id': self.move_id.product_id.id,
                    'location_id': self.move_id.location_id.id,
                    'location_dest_id': self.move_id.location_dest_id.id,
                    'picking_id': self.move_id.picking_id.id,
                    'quantity': 1.0,
                })


            if i < full_lines:
                sample_qty = samples_per_unit
            else:
                sample_qty = remaining_samples


            line.with_context(skip_field_serial_update=True).write({
                'sample_quantity': sample_qty,
                'quantity': 1.0,
            })


            self._add_codes_to_line(line, i + 1)

    def _get_samples_per_unit_for_product(self):
        """الحصول على قيمة العينة الواحدة للمنتج"""
        if not self.product_id:
            return 0


        param_key = f'appointment_products.samples_per_unit_{self.product_id.product_tmpl_id.id}'
        saved_value = self.env['ir.config_parameter'].sudo().get_param(param_key)

        if saved_value:
            try:
                return int(saved_value)
            except (ValueError, TypeError):
                pass


        return int(self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.samples_per_unit', 50000
        ))

    def _add_codes_to_line(self, line, sequence_number):
        """إضافة الرموز للسطر إذا لم تكن موجودة"""
        auto_lab_code = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.auto_generate_lab_code', 'False') == 'True'
        auto_field_code = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.auto_field_code_on_creation', 'False') == 'True'

        updates = {}


        if auto_lab_code and not line.field_code and line.is_picking_signed:
            updates['field_code'] = line._generate_lab_code()


        if auto_field_code and not line.field_serial:
            field_serial = line._generate_field_serial()
            updates['field_serial'] = field_serial

        if updates:
            line.with_context(skip_field_serial_update=True).write(updates)

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
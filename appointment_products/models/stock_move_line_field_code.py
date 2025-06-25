# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLineFieldCode(models.Model):
    _inherit = 'stock.move.line'

    field_code = fields.Char(
        string='الرمز المختبري', 
        copy=False,
        help='يمكن كتابة الرمز فقط بعد التوقيع على الطلبية'
    )
    
    is_picking_signed = fields.Boolean(
        string='تم التوقيع على الطلبية',
        related='picking_id.is_signed',
        store=True
    )

    # -----------------------
    # القيود حسب الإعدادات
    # -----------------------
    @api.constrains('field_code', 'company_id')
    def _check_unique_lab_code(self):
        """يمنع التكرار إذا كان الإعداد لا يسمح بذلك."""
        allow_duplicates = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.allow_lab_code_duplicates', 'False') == 'True'
        if allow_duplicates:
            return  # لا حاجة للتحقق
        for rec in self:
            if rec.field_code:
                domain = [
                    ('field_code', '=', rec.field_code),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain):
                    raise ValidationError(_('لا يمكن تكرار الرمز المختبري داخل نفس الشركة.'))

    # -----------------------
    # الترقيم التلقائي
    # -----------------------

    def _generate_lab_code(self):
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'appointment_products.lab_code')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Lab Code',
                'code': 'appointment_products.lab_code',
                'implementation': 'no_gap',
                'prefix': 'LC',
                'padding': 5,
                'company_id': self.env.company.id,
            })
        return seq.next_by_id()

    @api.onchange('field_code')
    def _onchange_field_code(self):
        """التحقق من التوقيع قبل السماح بكتابة الرمز"""
        if self.field_code and not self.is_picking_signed:
            self.field_code = False
            return {
                'warning': {
                    'title': _('تنبيه'),
                    'message': _('يجب التوقيع على الطلبية أولاً قبل إدخال الرمز المختبري')
                }
            }
    
    @api.model_create_multi
    def create(self, vals_list):
        """منع إنشاء الرمز المختبري بدون توقيع"""
        for vals in vals_list:
            if vals.get('field_code'):
                picking = self.env['stock.picking'].browse(vals.get('picking_id'))
                if picking and not picking.is_signed:
                    vals['field_code'] = False
            else:

                auto = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_generate_lab_code', 'False') == 'True'
                if auto and vals.get('picking_id'):
                    picking = self.env['stock.picking'].browse(vals['picking_id'])
                    if picking and picking.is_signed:
                        vals['field_code'] = self._generate_lab_code()
        return super().create(vals_list)
    
    def write(self, vals):
        """منع تعديل الرمز المختبري بدون توقيع"""
        if 'field_code' in vals:
            for record in self:
                if vals['field_code'] and not record.is_picking_signed:
                    vals['field_code'] = False

        auto = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_generate_lab_code', 'False') == 'True'

        res = super().write(vals)


        if auto:
            for rec in self:
                if not rec.field_code and rec.is_picking_signed:
                    rec.field_code = rec._generate_lab_code()

        return res 
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

    def _generate_field_serial(self):
        """إنشاء رقم تسلسلي للرمز الحقلي"""
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'appointment_products.field_serial')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Field Serial',
                'code': 'appointment_products.field_serial',
                'implementation': 'no_gap',
                'prefix': 'FC',
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
                immediate = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_field_code_on_creation', 'False') == 'True'

                if vals.get('picking_id') and immediate:
                    vals['lot_name'] = vals.get('lot_name') or self._generate_field_serial()
                elif vals.get('picking_id') and (auto and self.env['stock.picking'].browse(vals['picking_id']).is_signed):
                    vals['field_code'] = self._generate_lab_code()
        return super().create(vals_list)
    
    def write(self, vals):
        """منع تعديل الرمز المختبري بدون توقيع"""
        if 'field_code' in vals:
            prevent = self.env['ir.config_parameter'].sudo().get_param('appointment_products.prevent_edit_lab_code', 'False') == 'True'
            for record in self:
                if vals['field_code'] and not record.is_picking_signed:
                    vals['field_code'] = False

                if prevent and record.field_code and vals['field_code'] != record.field_code:
                    raise ValidationError(_('لا يمكن تعديل الرمز المختبري بعد إنشائه.'))

        auto = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_generate_lab_code', 'False') == 'True'
        immediate = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_field_code_on_creation', 'False') == 'True'

        res = super().write(vals)

        if immediate:
            for rec in self:
                if not rec.lot_name and not rec.lot_id:
                    rec.lot_name = rec._generate_field_serial()

        if auto and not immediate:
            for rec in self:
                if not rec.field_code and rec.is_picking_signed:
                    rec.field_code = rec._generate_lab_code()

        return res 
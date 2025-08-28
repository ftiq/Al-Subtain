# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    signature = fields.Binary(
        string='التوقيع',
        attachment=True
    )
    
    signer_name = fields.Char(
        string='اسم الموقع',
        default=lambda self: self.env.user.name,
        readonly=True
    )
    
    is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_is_signed',
        store=True
    )
    
    @api.depends('signature')
    def _compute_is_signed(self):
        """حساب ما إذا كان التوقيع موجود"""
        for record in self:
            record.is_signed = bool(record.signature)

            if record.signature and not record.signer_name:
                record.signer_name = record.env.user.name
    
    def action_clear_signature(self):
        """مسح التوقيع"""
        for pick in self:
            if pick.state == 'done':

                raise ValidationError(_('لا يمكن مسح التوقيع بعد تصديق حركة المخزون.'))

        self.write({
            'signature': False,
            'signer_name': self.env.user.name  
        })
        return True 

    def write(self, vals):
        """منع تغيير التوقيع بعد تصديق الحركة
        توليد الرمز المختبري عند إضافة توقيع جديد"""
        if 'signature' in vals:
            for pick in self:
                if pick.state == 'done':
                    raise ValidationError(_('لا يمكن تعديل التوقيع بعد تصديق حركة المخزون.'))

        res = super().write(vals)

        if vals.get('signature'):
            auto = self.env['ir.config_parameter'].sudo().get_param('appointment_products.auto_generate_lab_code', 'False') == 'True'
            if auto:
                for pick in self:
                    if pick.signature:
                        move_lines_to_update = pick.move_line_ids.filtered(lambda l: not l.field_code)
                        for ml in move_lines_to_update:
                            ml.with_context(allow_signed_update=True).write({
                                'field_code': ml._generate_lab_code()
                            })
        return res 
# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # التوقيع الإلكتروني
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
        self.write({
            'signature': False,
            'signer_name': self.env.user.name  
        })
        return True 
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockMoveLineFieldCode(models.Model):
    _inherit = 'stock.move.line'

    field_code = fields.Char(string='الرمز الحقلي', default=lambda self: self._default_field_code(), copy=False)

    @api.model
    def _default_field_code(self):
        return self.env['ir.sequence'].next_by_code('stock.move.line.field_code')

    _sql_constraints = [
        ('unique_field_code', 'unique(field_code)', _('Field code must be unique.')),
    ] 
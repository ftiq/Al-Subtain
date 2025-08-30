# -*- coding: utf-8 -*-
from odoo import models, fields


class LabSpreadsheetSession(models.Model):
    _name = 'lab.spreadsheet.session'
    _description = 'Lab Spreadsheet Preview Session'
    _inherit = ['spreadsheet.mixin']

    name = fields.Char(string='Name', default='Lab Spreadsheet Preview')

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_open_spreadsheet_history',
            'params': {
                'spreadsheet_id': self.id,
                'res_model': self._name,
            }
        }



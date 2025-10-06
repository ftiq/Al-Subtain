# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FormsSummaryWizard(models.TransientModel):
    _name = 'forms.summary.wizard'
    _description = 'Forms Summary Wizard'

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='Branch/Company', default=lambda self: self.env.company, required=True)
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   domain="[('type', 'in', ('sale','cash','bank','general'))]")
    only_posted = fields.Boolean(default=True, string='Posted Entries Only')

    def action_print_pdf(self):
        self.ensure_one()
        action = self.env.ref('appointment_financial_report.forms_summary_report_action').report_action(self)
        # Keep the wizard open/editable after the report is generated
        if isinstance(action, dict):
            action['close_on_report_download'] = False
        return action

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class FormsSummaryWizard(models.TransientModel):
    _name = 'forms.summary.wizard'
    _description = 'Forms Summary Wizard'

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    def _default_date_to(self):
        today = fields.Date.context_today(self)
        # Last day of current month
        return today.replace(day=1) + relativedelta(months=1, days=-1)

    def _default_journals(self):
        # Default to journal with id=1 as requested
        j = self.env['account.journal'].browse(1)
        return j.exists()

    date_from = fields.Date(required=True, default=_default_date_from)
    date_to = fields.Date(required=True, default=_default_date_to)
    company_id = fields.Many2one('res.company', string='Branch/Company', default=lambda self: self.env.company, required=True)
    journal_ids = fields.Many2many('account.journal', string='Journals',
                                   domain="[('type', 'in', ('sale','cash','bank','general'))]",
                                   default=_default_journals)
    only_posted = fields.Boolean(default=True, string='Posted Entries Only')

    def action_print_pdf(self):
        self.ensure_one()
        action = self.env.ref('appointment_financial_report.forms_summary_report_action').report_action(self)
        # Keep the wizard open/editable after the report is generated
        if isinstance(action, dict):
            action['close_on_report_download'] = False
        return action

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_('The start date must be before or equal to the end date.'))

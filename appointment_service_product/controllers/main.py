from odoo import http
from odoo.addons.website_calendar.controllers.main import WebsiteCalendarController

class ProductCalendarController(WebsiteCalendarController):

    def _prepare_calendar_appointment_values(self, **kwargs):
        values = super()._prepare_calendar_appointment_values(**kwargs)
        values['products'] = http.request.env['product.product'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        return values

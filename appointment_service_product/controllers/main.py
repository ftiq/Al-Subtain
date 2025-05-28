from odoo import http
from odoo.addons.website_calendar.controllers.main import WebsiteCalendarController

class CustomWebsiteCalendarController(WebsiteCalendarController):

    @http.route()
    def calendar_appointment(self, **kwargs):
        response = super().calendar_appointment(**kwargs)
        if response.qcontext:
            response.qcontext['products'] = http.request.env['product.product'].search([
                ('type', '=', 'service'),
                ('sale_ok', '=', True)
            ])
        return response

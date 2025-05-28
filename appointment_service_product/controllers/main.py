from odoo import http
from odoo.addons.website_appointment.controllers.main import WebsiteAppointment

class CustomWebsiteAppointment(WebsiteAppointment):
    
    @http.route()
    def appointment(self, **kwargs):
        response = super().appointment(**kwargs)
        if response.qcontext:
            response.qcontext['products'] = http.request.env['product.product'].search([
                ('type', '=', 'service'),
                ('sale_ok', '=', True)
            ])
        return response

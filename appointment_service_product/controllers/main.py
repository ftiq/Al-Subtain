from odoo import http
from odoo.http import request

class AppointmentController(http.Controller):
    
    @http.route('/website/calendar', type='http', auth="public", website=True)
    def calendar_appointment(self, **post):
        services = request.env['product.product'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        return request.render("website_calendar.index", {
            'services': services,
        })

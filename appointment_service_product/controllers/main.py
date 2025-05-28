# controllers/main.py
from odoo import http
from odoo.http import request

class WebsiteAppointmentExtended(http.Controller):

    @http.route(['/appointment/<model("calendar.appointment.type"):appointment_type>/info'], type='http', auth='public', website=True)
    def appointment_info(self, appointment_type, **kwargs):
        products = request.env['product.product'].sudo().search([])
        return request.render("appointment.appointment_info", {
            'appointment_type': appointment_type,
            'products': products,
        })

    @http.route(['/appointment/submit'], type='http', auth='public', website=True, csrf=False)
    def appointment_submit(self, **post):
        product_id = int(post.get('x_service_product_id', 0))
        # Store or use this product_id in calendar.event creation
        # This logic depends on your specific flow
        return request.redirect('/appointment/confirmation')

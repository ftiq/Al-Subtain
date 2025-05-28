from odoo import http
from odoo.http import request

class AppointmentController(http.Controller):

    @http.route(['/appointment/<model("appointment.type"):appointment_type>/info'], type='http', auth="public", website=True)
    def appointment_info(self, appointment_type, **kwargs):
        products = request.env['product.product'].sudo().search([('sale_ok', '=', True)])
        values = {
            'appointment_type': appointment_type,
            'products': products,
        }
        return request.render("appointment.appointment_info", values)

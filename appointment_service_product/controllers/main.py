from odoo import http
from odoo.http import request

class AppointmentController(http.Controller):
    
    @http.route('/appointment', type='http', auth="public", website=True)
    def appointment_form(self, **post):
        services = request.env['product.product'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True)
        ])
        return request.render("appointment_service_product.appointment_page", {
            'services': services,
        })
    
    @http.route('/appointment/submit', type='http', auth="public", website=True, csrf=True)
    def appointment_submit(self, **post):
        event = request.env['calendar.event'].create({
            'name': post.get('name', 'New Appointment'),
            'start': post.get('start_datetime'),
            'stop': post.get('end_datetime'),
            'product_id': int(post.get('service_id')) if post.get('service_id') else False,
        })
        return request.redirect('/appointment/confirmation')

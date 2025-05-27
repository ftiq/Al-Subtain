
from odoo import http
from odoo.http import request
import base64

class AppointmentBookingController(http.Controller):

    @http.route(['/appointment/service_booking'], type='http', auth='public', website=True, csrf=True)
    def render_custom_appointment_form(self, **kwargs):
        services = request.env['product.product'].sudo().search([('sale_ok', '=', True), ('type', '=', 'service')])
        return request.render("appointment_service_booking.custom_appointment_form", {
            'services': services
        })

    @http.route(['/appointment/service_booking/submit'], type='http', auth='public', website=True, csrf=True, methods=["POST"])
    def submit_custom_appointment(self, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = int(post.get('service_product_id', 0))
        product = request.env['product.product'].sudo().browse(product_id)

        partner = request.env.user.partner_id or request.env['res.partner'].sudo().search([('id', '=', 1)], limit=1)

        booking = request.env['appointment.booking'].sudo().create({
            'partner_id': partner.id,
            'name': post.get('name', 'Appointment'),
            'x_service_id': product.id if product else False,
        })

        if uploaded_file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'appointment.booking',
                'res_id': booking.id,
                'type': 'binary',
            })
            booking.message_post(
                body="Customer uploaded a file.",
                attachment_ids=[attachment.id]
            )

        return request.redirect('/website/appointment/thank-you')

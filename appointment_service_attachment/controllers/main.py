
from odoo import http
from odoo.http import request
import base64

class AppointmentExtendedController(http.Controller):

    @http.route(['/appointment/custom_form'], type='http', auth='public', website=True, csrf=True)
    def custom_appointment_form(self, **kwargs):
        services = request.env['product.product'].sudo().search([('sale_ok', '=', True), ('type', '=', 'service')])
        return request.render("appointment_service_attachment.custom_appointment_form", {
            'services': services
        })

    @http.route(['/appointment/custom_submit'], type='http', auth='public', website=True, csrf=True, methods=["POST"])
    def custom_appointment_submit(self, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = int(post.get('service_product_id', 0))
        product = request.env['product.product'].sudo().browse(product_id)

        partner = request.env.user.partner_id

        description = f"Service Requested: {product.display_name if product else 'None'}\n"

        appointment = request.env['calendar.event'].sudo().create({
            'name': post.get('name', 'Appointment'),
            'partner_ids': [(4, partner.id)],
            'description': description,
        })

        if uploaded_file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'calendar.event',
                'res_id': appointment.id,
                'type': 'binary',
            })
            appointment.message_post(
                body="Customer uploaded a file.",
                attachment_ids=[attachment.id]
            )

        return request.redirect('/website/appointment/thank-you')

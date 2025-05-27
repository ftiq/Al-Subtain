
from odoo import http
from odoo.http import request
import base64

class WebsiteAppointmentExtended(http.Controller):

    @http.route('/website/appointment', type='http', auth='public', website=True)
    def render_appointment_form(self, **kwargs):
        services = request.env['product.product'].sudo().search([('sale_ok', '=', True), ('type', '=', 'service')])
        return request.render('website_appointment_service_v2.website_appointment_custom_form', {
            'services': services
        })

    @http.route('/website/appointment/submit', type='http', auth='public', website=True, csrf=True)
    def appointment_submit(self, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = int(post.get('service_product_id', 0))
        product = request.env['product.product'].sudo().browse(product_id)
        partner = request.env.user.partner_id

        appointment = request.env['calendar.event'].sudo().create({
            'name': post.get('name', 'Appointment'),
            'partner_ids': [(4, partner.id)],
        })

        attachment_id = None
        if uploaded_file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'calendar.event',
                'res_id': appointment.id,
                'type': 'binary',
            })
            attachment_id = attachment.id

            # Post to chatter
            appointment.message_post(
                body="Attachment uploaded during appointment booking.",
                attachment_ids=[attachment.id]
            )

        # Create Sales Order
        if product.exists():
            request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'order_line': [(0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 1,
                })]
            })

        return request.redirect('/website/appointment/thank-you')

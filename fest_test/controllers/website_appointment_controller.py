from odoo import http, fields
from odoo.http import request
import base64

class WebsiteAppointmentExtended(http.Controller):

    @http.route('/website/appointment', type='http', auth='public', website=True)
    def render_appointment_form(self, **kwargs):
        services = request.env['product.product'].sudo().search([('sale_ok', '=', True), ('type', '=', 'service')])
        return request.render('website_appointment_service.website_appointment_custom_form', {
            'services': services
        })

    @http.route('/website/appointment/submit', type='http', auth='public', website=True, csrf=True)
    def appointment_submit(self, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = int(post.get('service_product_id'))
        product = request.env['product.product'].sudo().browse(product_id)

        partner = request.env['res.partner'].sudo().create({
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
        })

        appointment = request.env['calendar.event'].sudo().create({
            'name': f"Appointment for {partner.name}",
            'partner_ids': [(4, partner.id)],
            'start': fields.Datetime.now(),
        })

        if uploaded_file:
            request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'calendar.event',
                'res_id': appointment.id,
                'type': 'binary',
            })

        request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
            })]
        })

        return request.redirect('/website/appointment/thank-you')
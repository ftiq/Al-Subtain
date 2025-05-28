from odoo import http, fields
from odoo.http import request
import base64

class AppointmentCustomController(http.Controller):

    @http.route(['/appointment/<model("appointment.type"):appointment_type>/submit'], type='http', auth='public', website=True, csrf=True)
    def appointment_submit(self, appointment_type, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = post.get('service_product_id')
        product = None
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))

        partner = request.env['res.partner'].sudo().create({
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
        })

        appointment = request.env['calendar.event'].sudo().create({
            'name': f"Appointment for {partner.name}",
            'partner_ids': [(4, partner.id)],
            'start': fields.Datetime.now(),
            'x_product_id': product.id if product else False,
        })

        if uploaded_file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'calendar.event',
                'res_id': appointment.id,
                'type': 'binary',
            })
            appointment.write({'x_attachment_id': attachment.id})

        return request.redirect('/website/appointment/thank-you')

from odoo import http, fields
from odoo.http import request
import base64

class AppointmentCustomController(http.Controller):

    @http.route(['/appointment/<model("appointment.type"):appointment_type>/submit'], type='http', auth='public', website=True, csrf=True)
    def appointment_submit(self, appointment_type, **post):
        partner = request.env['res.partner'].sudo().create({
            'name': post.get('name'),
            'email': post.get('email'),
            'phone': post.get('phone'),
        })

        attachment_id = None
        uploaded_file = post.get('attachment_file')
        if uploaded_file and appointment_type.allow_attachment:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': uploaded_file.filename,
                'datas': base64.b64encode(uploaded_file.read()),
                'res_model': 'calendar.event',
                'type': 'binary',
            })
            attachment_id = attachment.id

        event = request.env['calendar.event'].sudo().create({
            'name': f"Appointment for {partner.name}",
            'partner_ids': [(4, partner.id)],
            'start': fields.Datetime.now(),
            'x_attachment_id': attachment_id,
        })

        if appointment_type.product_id:
            request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'order_line': [(0, 0, {
                    'product_id': appointment_type.product_id.id,
                    'product_uom_qty': 1,
                })],
                'x_appointment_id': event.id
            })

        return request.redirect('/website/appointment/thank-you')

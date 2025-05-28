from odoo.addons.appointment.controllers.main import AppointmentWebsite
from odoo import http, fields
from odoo.http import request
import base64

class AppointmentWebsiteExtended(AppointmentWebsite):

    @http.route(['/appointment/<model("appointment.type"):appointment_type>/submit'], type='http', auth="public", website=True, csrf=True)
    def appointment_submit(self, appointment_type, **post):
        uploaded_file = request.httprequest.files.get('attachment_file')
        product_id = post.get('service_product_id')
        product = None
        if product_id:
            product = request.env['product.product'].sudo().browse(int(product_id))

        # Continue with the original logic to create the event
        response = super().appointment_submit(appointment_type, **post)

        # Attempt to find the last created appointment
        appointment = request.env['calendar.event'].sudo().search([], order='id desc', limit=1)

        # Save product_id and attachment to the event
        if appointment:
            vals = {}
            if product:
                vals['x_product_id'] = product.id
            if uploaded_file:
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': uploaded_file.filename,
                    'datas': base64.b64encode(uploaded_file.read()),
                    'res_model': 'calendar.event',
                    'res_id': appointment.id,
                    'type': 'binary',
                })
                vals['x_attachment_id'] = attachment.id

            if vals:
                appointment.write(vals)

        return response

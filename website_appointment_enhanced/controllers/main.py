import base64
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController

class WebsiteAppointmentEnhanced(AppointmentController):

    @http.route()
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs):
        service_id = int(kwargs.get('service_id') or 0)
        uploaded_file = request.httprequest.files.get('attachment')

        # معالجة staff_user_id إذا كان ID أو بريد إلكتروني
        try:
            staff_user_id = int(staff_user_id)
        except ValueError:
            staff_user = request.env['res.users'].sudo().search([('login', '=', staff_user_id)], limit=1)
            staff_user_id = staff_user.id if staff_user else None

        response = super().appointment_form_submit(
            appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs
        )

        appointment = request.env['calendar.event'].sudo().search([
            ('name', '=', name),
            ('start', '=', datetime_str),
        ], order='id desc', limit=1)

        if appointment:
            partner = appointment.partner_ids[0] if appointment.partner_ids else None
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id if partner else None,
                'origin': f"Appointment {appointment.id}"
            })

            if service_id:
                product = request.env['product.product'].sudo().browse(service_id)
                request.env['sale.order.line'].sudo().create({
                    'order_id': order.id,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.lst_price,
                    'name': product.name,
                })

            if uploaded_file:
                request.env['ir.attachment'].sudo().create({
                    'name': uploaded_file.filename,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'type': 'binary',
                    'datas': base64.b64encode(uploaded_file.read()),
                    'mimetype': uploaded_file.content_type,
                })

        return response

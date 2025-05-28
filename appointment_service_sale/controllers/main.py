import base64
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController

class AppointmentExtendedController(AppointmentController):
    @http.route()
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs):
        response = super(AppointmentExtendedController, self).appointment_form_submit(
            appointment_type_id, datetime_str, duration_str, staff_user_id,
            name, phone, email, **kwargs
        )

        appointment = request.env['appointment.appointment'].sudo().search([
            ('name', '=', name),
            ('phone', '=', phone),
            ('appointment_type_id', '=', int(appointment_type_id)),
        ], order="id desc", limit=1)

        if appointment:
            partner = appointment.partner_id or request.env['res.partner'].sudo().search([('phone', '=', phone)], limit=1)
            sale_order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id if partner else None,
                'origin': f"Appointment #{appointment.id}"
            })

            if appointment.service_id:
                request.env['sale.order.line'].sudo().create({
                    'order_id': sale_order.id,
                    'product_id': appointment.service_id.id,
                    'product_uom_qty': 1,
                    'product_uom': appointment.service_id.uom_id.id,
                    'price_unit': appointment.service_id.lst_price or 0.0,
                    'name': appointment.service_id.display_name,
                })

            if 'attachment' in request.httprequest.files:
                file_storage = request.httprequest.files['attachment']
                if file_storage:
                    file_content = file_storage.read()
                    attachment_vals = {
                        'name': file_storage.filename,
                        'res_model': 'sale.order',
                        'res_id': sale_order.id,
                        'type': 'binary',
                        'datas': base64.b64encode(file_content),
                        'mimetype': file_storage.content_type,
                    }
                    request.env['ir.attachment'].sudo().create(attachment_vals)

            appointment.sudo().write({'sale_order_id': sale_order.id})
        return response

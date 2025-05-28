import base64
import logging
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController

_logger = logging.getLogger(__name__)

class WebsiteAppointmentEnhanced(AppointmentController):

    @http.route()
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs):
        service_id = kwargs.get('service_id')
        uploaded_file = request.httprequest.files.get('attachment')

        try:
            staff_user_id = int(staff_user_id)
        except Exception:
            staff_user_id = request.env.user.id

        response = super().appointment_form_submit(
            appointment_type_id, datetime_str, duration_str, staff_user_id,
            name, phone, email, **kwargs
        )

        appointment = request.env['calendar.event'].sudo().search([
            ('start', '=', datetime_str),
            ('partner_ids.name', '=', name),
        ], order='id desc', limit=1)

        if not appointment:
            _logger.warning("No appointment found after submission.")
            return response

        partner = appointment.partner_ids[0] if appointment.partner_ids else None

        order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id if partner else None,
            'origin': f"Appointment {appointment.id}",
        })

        if service_id:
            try:
                service_id = int(service_id)
                product = request.env['product.product'].sudo().browse(service_id)
                if product.exists():
                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'product_uom': product.uom_id.id,
                        'price_unit': product.lst_price,
                        'name': product.name,
                    })
            except Exception as e:
                _logger.warning(f"Product error: {e}")

        if uploaded_file:
            try:
                request.env['ir.attachment'].sudo().create({
                    'name': uploaded_file.filename,
                    'res_model': 'sale.order',
                    'res_id': order.id,
                    'type': 'binary',
                    'datas': base64.b64encode(uploaded_file.read()),
                    'mimetype': uploaded_file.content_type,
                })
            except Exception as e:
                _logger.warning(f"Attachment error: {e}")

        return response

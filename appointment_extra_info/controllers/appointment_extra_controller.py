from odoo import http, fields
from odoo.http import request
import base64

class AppointmentExtraController(http.Controller):

    @http.route('/appointment/extra-info/<int:event_id>', type='http', auth='public', website=True)
    def extra_info_form(self, event_id, **kwargs):
        event = request.env['calendar.event'].sudo().browse(event_id)
        appointment_type = event.appointment_type_id
        return request.render("appointment_extra_info.appointment_extra_info_form", {
            "event": event,
            "appointment_type": appointment_type,
        })

    @http.route('/appointment/extra-info/save', type='http', auth='public', website=True, csrf=True)
    def save_extra_info(self, **post):
        event_id = int(post.get("event_id"))
        event = request.env['calendar.event'].sudo().browse(event_id)

        file = request.httprequest.files.get('attachment_file')
        attachment_id = None

        if file:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': file.filename,
                'datas': base64.b64encode(file.read()),
                'res_model': 'calendar.event',
                'res_id': event.id,
                'type': 'binary',
            })
            event.write({'x_attachment_id': attachment.id})

        if event.appointment_type_id.product_id:
            request.env['sale.order'].sudo().create({
                'partner_id': event.partner_ids[0].id if event.partner_ids else None,
                'order_line': [(0, 0, {
                    'product_id': event.appointment_type_id.product_id.id,
                    'product_uom_qty': 1,
                })],
                'x_appointment_id': event.id,
            })

        return request.redirect('/website/appointment/thank-you')
        from odoo.addons.appointment.controllers.main import AppointmentWebsite

        class AppointmentWebsiteCustom(AppointmentWebsite):

            def _redirect_to_next(self, appointment, event):
                # إعادة التوجيه إلى صفحة الخدمة والمرفق بدل thank-you
                return '/appointment/extra-info/{}'.format(event.id)

import base64
from odoo import http
from odoo.http import request
from odoo.addons.appointment.controllers.appointment import AppointmentController

class WebsiteAppointmentEnhanced(AppointmentController):

    @http.route()
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs):
        service_id = int(kwargs.get('service_id') or 0)
        uploaded_file = request.httprequest.files.get('attachment')

        # نحاول تحويل staff_user_id إلى int وإذا فشل نبحث عن المستخدم بالبريد
        try:
            staff_user_id = int(staff_user_id)
        except ValueError:
            user = request.env['res.users'].sudo().search([('login', '=', staff_user_id)], limit=1)
            staff_user_id = user.id if user else request.env.user.id

        # استدعاء دالة الـ Super
        response = super().appointment_form_submit(
            appointment_type_id, datetime_str, duration_str, staff_user_id, name, phone, email, **kwargs
        )

        # البحث عن الموعد الذي تم إنشاؤه
        appointment = request.env['calendar.event'].sudo().search([
            ('name', '=', name),
            ('start', '=', datetime_str),
        ], order='id desc', limit=1)

        if appointment:
            partner = appointment.partner_ids[0] if appointment.partner_ids else None

            # إنشاء طلب بيع
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id if partner else None,
                'origin': f"Appointment {appointment.id}"
            })

            # إضافة السطر للطلب
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

            # إضافة المرفق
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

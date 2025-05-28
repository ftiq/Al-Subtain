import base64
from odoo import http
from odoo.http import request

class AppointmentController(http.Controller):
    _inherit = 'appointment.appointment_controller'

    @http.route('/appointment/submit', type='http', auth="public", website=True)
    def appointment_form_submit(self, appointment_type_id, **kwargs):
        result = super(AppointmentController, self).appointment_form_submit(appointment_type_id, **kwargs)
        
        appointment_type = request.env['appointment.type'].browse(int(appointment_type_id))
        appointment = request.env['calendar.event'].browse(result.get('appointment_id'))
        
        # Handle attachment upload
        attachment = kwargs.get('attachment')
        if attachment and appointment_type.allow_attachment:
            request.env['ir.attachment'].create({
                'name': attachment.filename,
                'datas': base64.b64encode(attachment.read()),
                'res_model': 'calendar.event',
                'res_id': appointment.id,
            })
        
        # Create sales order if product is set
        if appointment_type.product_id:
            so = request.env['sale.order'].create({
                'partner_id': appointment.partner_id.id,
                'appointment_id': appointment.id,
                'order_line': [(0, 0, {
                    'product_id': appointment_type.product_id.id,
                    'product_uom_qty': 1,
                    'price_unit': appointment_type.product_id.list_price,
                })]
            })
            appointment.sale_order_id = so.id
        
        return result

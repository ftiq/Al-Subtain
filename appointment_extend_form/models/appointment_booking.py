
from odoo import models, fields

class AppointmentBooking(models.Model):
    _inherit = 'appointment.booking'

    x_service_id = fields.Many2one('product.product', string="Selected Service")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'appointment_booking_attachment_rel',
        'booking_id',
        'attachment_id',
        string='Attachments',
        domain=[('res_model', '=', 'appointment.booking')],
        auto_join=True
    )

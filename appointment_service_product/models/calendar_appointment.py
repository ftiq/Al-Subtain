# models/calendar_appointment.py
from odoo import models, fields

class CalendarAppointmentType(models.Model):
    _inherit = 'calendar.appointment.type'

    x_service_product_id = fields.Many2one('product.product', string='Default Service Product')

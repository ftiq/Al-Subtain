from odoo import models, fields

class CalendarAppointmentProduct(models.Model):
    _name = 'calendar.appointment.product'
    _description = 'Appointment Product Option'

    name = fields.Char(string="Service/Product Name", required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    appointment_type_id = fields.Many2one('calendar.appointment.type', string='Appointment Type')

class CalendarAppointment(models.Model):
    _inherit = 'calendar.appointment'

    product_ids = fields.Many2many(
        'calendar.appointment.product',
        'calendar_appointment_product_rel',
        'appointment_id', 'product_id',
        string='Selected Products'
    )

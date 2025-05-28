from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_appointment_id = fields.Many2one('calendar.event', string="Related Appointment")

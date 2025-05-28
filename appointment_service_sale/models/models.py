from odoo import models, fields

class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    service_id = fields.Many2one(
        'product.product', string="Service",
        domain=[('type', '=', 'service')]
    )
    sale_order_id = fields.Many2one(
        'sale.order', string="Generated Sale Order"
    )

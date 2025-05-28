from odoo import models, fields

class Appointment(models.Model):
    _inherit = 'appointment.appointment'

    product_id = fields.Many2one(
        'product.product', 
        string="Service",
        domain=[('type', '=', 'service')],
        tracking=True
    )

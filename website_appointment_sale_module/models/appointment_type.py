from odoo import models, fields

class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    product_id = fields.Many2one('product.product', string="Service Product")
    allow_attachment = fields.Boolean(string="Allow Attachment")

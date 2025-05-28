from odoo import models, fields

class AppointmentType(models.Model):
    _inherit = 'appointment.type'
    
    product_id = fields.Many2one('product.product', string='Service Product',
        help="The product that will be used when creating the sales order")
    allow_attachment = fields.Boolean('Allow Attachment Upload',
        help="Enable this to allow customers to upload attachments with their appointment")

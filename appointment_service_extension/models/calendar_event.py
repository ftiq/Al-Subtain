from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    service_product_id = fields.Many2one(
        'product.product',
        string='Service Requested',
        help='Service selected by the client for this appointment.'
    )

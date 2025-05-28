
from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    service_id = fields.Many2one('product.product', string='Service Product')

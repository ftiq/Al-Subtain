
from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    x_service_id = fields.Many2one('product.product', string="Selected Service")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'calendar_event_attachment_rel',
        'event_id',
        'attachment_id',
        string='Attachments',
        domain=[('res_model', '=', 'calendar.event')]
    )

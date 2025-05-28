from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    x_attachment_id = fields.Many2one('ir.attachment', string="Uploaded Attachment")

from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'
    
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    attachment_ids = fields.One2many('ir.attachment', 'res_id', 
                                   domain=[('res_model', '=', 'calendar.event')],
                                   string='Attachments')

from odoo import models, fields

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'
    
    product_id = fields.Many2one('product.product', string='الخدمة المختارة')

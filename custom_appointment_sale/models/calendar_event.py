from odoo import models, fields, api

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    x_service_product_id = fields.Many2one('product.product', string="Service", domain=[('detailed_type','=','service')])
    x_attachment = fields.Binary(string="Attachment")
    x_attachment_filename = fields.Char(string="Attachment Filename")

    def create_sale_order_from_event(self):
        for event in self:
            if event.partner_ids and event.x_service_product_id:
                order = self.env['sale.order'].create({
                    'partner_id': event.partner_ids[0].id,
                    'order_line': [(0, 0, {
                        'product_id': event.x_service_product_id.id,
                        'product_uom_qty': 1,
                        'name': event.name,
                    })],
                })
                if event.x_attachment:
                    self.env['ir.attachment'].create({
                        'name': event.x_attachment_filename or 'Attachment',
                        'type': 'binary',
                        'datas': event.x_attachment,
                        'res_model': 'sale.order',
                        'res_id': order.id,
                    })

from odoo import models, fields

class AppointmentType(models.Model):
    _inherit = 'appointment.type'

    allow_attachment = fields.Boolean(string="Allow Attachments")

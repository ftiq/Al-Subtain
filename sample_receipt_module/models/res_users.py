from odoo import models, fields, _
from odoo.exceptions import UserError

class ResUsers(models.Model):
    _inherit = 'res.users'

    api_token = fields.Char("API Token", readonly=True)

    def write(self, vals):
        if 'api_token' in vals:
            for user in self:
                if user.api_token and vals['api_token'] != user.api_token:
                    raise UserError(_("You cannot change the API Token once it is set."))
        return super().write(vals)

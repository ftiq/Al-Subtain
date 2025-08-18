# -*- coding: utf-8 -*-
from odoo import models


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    def _get_check_action_name(self):
        name = super()._get_check_action_name()
        if self.move_line_id and self.move_line_id.field_code:

            name += ' - %s' % self.move_line_id.field_code
        return name 
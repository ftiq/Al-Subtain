# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_service_fsm = fields.Boolean(string='الخدمة', help='حدد إذا كان هذا المنتج يمثل خدمة ميدانية.') 
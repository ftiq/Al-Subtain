# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'


    header_image = fields.Binary(
        string='صورة الترويسة',
        help='الصورة التي ستظهر في أعلى التقارير والمستندات'
    )
    

    footer_image = fields.Binary(
        string='صورة التذييل',
        help='الصورة التي ستظهر في أسفل التقارير والمستندات'
    ) 
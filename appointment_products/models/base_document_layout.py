# -*- coding: utf-8 -*-
from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'


    header_image = fields.Binary(
        string='صورة الترويسة',
        help='الصورة التي ستظهر في أعلى التقارير والمستندات',
        related='company_id.header_image',
        readonly=False
    )
    

    footer_image = fields.Binary(
        string='صورة التذييل', 
        help='الصورة التي ستظهر في أسفل التقارير والمستندات',
        related='company_id.footer_image',
        readonly=False
    ) 
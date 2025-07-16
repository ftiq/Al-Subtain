# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import reports

from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    """Pre-initialization hook for the module."""
    pass


def post_init_hook(env):
    """Post-initialization: إنشاء الفئات الافتراضية للوثائق بعد تثبيت الوحدة."""


    categories = [
        {'name': 'كتب إلكترونية', 'code': 'EBOOK', 'description': 'فئة الكتب الإلكترونية'},
        {'name': 'مخاطبات واردة', 'code': 'INCOMING', 'description': 'المخاطبات الواردة من الجهات الخارجية'},
        {'name': 'مخاطبات صادرة', 'code': 'OUTGOING', 'description': 'المخاطبات الصادرة للجهات الخارجية'},
        {'name': 'مخاطبات داخلية', 'code': 'INTERNAL', 'description': 'المخاطبات الداخلية بين الأقسام'},
    ]

    for cat_data in categories:
        existing = env['document.category'].search([('code', '=', cat_data['code'])], limit=1)
        if not existing:
            env['document.category'].create(cat_data)


def uninstall_hook(cr, registry):
    """Uninstall hook for the module."""
    pass 
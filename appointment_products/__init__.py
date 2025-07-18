# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizards
from odoo import fields
import logging
from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)

def patch_odoo18_compatibility():
    """إصلاح مشاكل التوافق مع Odoo 18"""
    try:
        if not hasattr(fields.Char, 'ondelete'):
            fields.Char.ondelete = property(lambda self: {})
            _logger.info("تم إصلاح مشكلة ondelete للحقول Char")
        
        original_selection_init = fields.Selection.__init__
        
        def patched_selection_init(self, *args, **kwargs):
            original_selection_init(self, *args, **kwargs)
            
            if not hasattr(self, 'value'):
                self.value = None
        
        fields.Selection.__init__ = patched_selection_init
        _logger.info("تم إصلاح مشكلة Selection.value")
        
    except Exception as e:
        _logger.warning(f"تحذير في إصلاح التوافق: {e}")


def deactivate_non_masonry(env):
    """تعطيل الأنواع الفرعية غير الطابوق عند التثبيت"""
    try:
        subtypes = env['lab.sample.subtype'].search([])
        for st in subtypes:
            if st.sample_type_id.code != 'MASONRY':
                st.active = False
        _logger.info("تم تعطيل الأنواع الفرعية غير الطابوق بنجاح")
    except Exception as e:
        _logger.error(f"خطأ أثناء تعطيل الأنواع الفرعية: {e}")


patch_odoo18_compatibility()

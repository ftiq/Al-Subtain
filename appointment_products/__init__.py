# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizards
from odoo import fields
import logging

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


patch_odoo18_compatibility()

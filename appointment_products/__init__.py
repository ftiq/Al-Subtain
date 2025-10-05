# -*- coding: utf-8 -*-
from . import models
from . import controllers
from . import wizards
from odoo import fields
import logging
from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)

def patch_odoo18_compatibility():
    """Fix compatibility issues with Odoo 18"""
    try:
        if not hasattr(fields.Char, 'ondelete'):
            fields.Char.ondelete = property(lambda self: {})
            _logger.info("Fixed ondelete issue for Char fields")
        
        original_selection_init = fields.Selection.__init__
        
        def patched_selection_init(self, *args, **kwargs):
            original_selection_init(self, *args, **kwargs)
            
            if not hasattr(self, 'value'):
                self.value = None
        
        fields.Selection.__init__ = patched_selection_init
        _logger.info("Fixed Selection.value issue")
        
    except Exception as e:
        _logger.warning(f"Warning in fixing compatibility: {e}")


def deactivate_non_masonry(env):
    """Disable non-masonry subtypes when installing"""
    try:
        subtypes = env['lab.sample.subtype'].search([])
        for st in subtypes:
            code = (st.sample_type_id.code or '').upper()

            if code not in ('MASONRY', 'CONCRETE_CORE'):
                st.active = False
        _logger.info("Disabled non-masonry subtypes successfully")
    except Exception as e:
        _logger.error(f"Error disabling subtypes: {e}")


# -*- coding: utf-8 -*-
"""
Migration script to update unique constraints for concrete samples
Removes old constraint and allows multiple result sets for concrete samples
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    إزالة القيد القديم للسماح بعدة result_sets لعينات الخرسانة
    """
    _logger.info("Starting migration: removing old unique constraint for concrete samples")
    

    try:
        cr.execute("""
            ALTER TABLE lab_result_set 
            DROP CONSTRAINT IF EXISTS lab_result_set_sample_template_unique;
        """)
        _logger.info("Successfully removed old unique constraint lab_result_set_sample_template_unique")
    except Exception as e:
        _logger.warning("Could not remove old constraint: %s", e)
    

    try:
        cr.execute("""
            CREATE INDEX IF NOT EXISTS lab_result_set_concrete_sample_idx 
            ON lab_result_set (is_concrete_sample) 
            WHERE is_concrete_sample IS TRUE;
        """)
        _logger.info("Created index for concrete samples")
    except Exception as e:
        _logger.warning("Could not create concrete sample index: %s", e)
    
    _logger.info("Migration completed: concrete samples can now have multiple result sets")

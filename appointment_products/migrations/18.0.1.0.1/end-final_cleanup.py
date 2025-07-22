# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    End-migration script للتنظيف النهائي بعد تحديث جميع الوحدات
    """
    _logger.info(f'بدء end-migration للتنظيف النهائي - النسخة {version}')
    
    try:

        cr.execute("""
            DELETE FROM ir_model_data 
            WHERE module = 'appointment_products' 
            AND model IN ('ir.model.fields', 'ir.ui.view', 'ir.model.access')
            AND res_id NOT IN (
                SELECT CASE 
                    WHEN model = 'ir.model.fields' THEN (SELECT id FROM ir_model_fields WHERE id = res_id)
                    WHEN model = 'ir.ui.view' THEN (SELECT id FROM ir_ui_view WHERE id = res_id)
                    WHEN model = 'ir.model.access' THEN (SELECT id FROM ir_model_access WHERE id = res_id)
                    ELSE res_id
                END
            )
        """)
        

        tables_to_refresh = ['project_task', 'stock_picking', 'project_project']
        for table in tables_to_refresh:
            try:

                cr.execute(f"""
                    SELECT setval('{table}_id_seq', 
                        COALESCE((SELECT MAX(id) FROM {table}), 1), 
                        CASE WHEN (SELECT MAX(id) FROM {table}) IS NULL THEN false ELSE true END
                    )
                """)
                _logger.info(f'تم تحديث sequence للجدول {table}')
            except Exception as e:
                _logger.warning(f'لم يتم العثور على sequence للجدول {table}: {e}')
        

        cr.execute("SELECT clear_cache_all()")
        

        cr.execute("VACUUM ANALYZE")
        
        _logger.info('تم الانتهاء من end-migration بنجاح')
        
    except Exception as e:
        _logger.error(f'خطأ أثناء تنفيذ end-migration: {str(e)}')
        raise

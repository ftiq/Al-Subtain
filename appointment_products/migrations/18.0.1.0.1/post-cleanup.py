# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Post-migration script للتنظيف النهائي بعد تحديث الوحدة
    """
    _logger.info(f'بدء post-migration للتنظيف النهائي - النسخة {version}')
    
    try:

        deleted_views = [

        ]
        
        for view_name in deleted_views:
            cr.execute("""
                DELETE FROM ir_ui_view 
                WHERE name=%s AND (arch LIKE %s OR xml_id LIKE %s)
            """, (view_name, f'%{view_name}%', f'%{view_name}%'))
            _logger.info(f'تم حذف الواجهة {view_name}')
        

        cr.execute("""
            DELETE FROM ir_model_access 
            WHERE name LIKE %s
        """, ('access_%_deleted_%',))
        

        cr.execute("""
            DELETE FROM ir_rule 
            WHERE name LIKE %s
        """, ('%_deleted_%',))
        

        cr.execute("""
            DELETE FROM ir_act_window 
            WHERE res_model IN (
                SELECT name FROM ir_model WHERE name LIKE '%deleted%'
            )
        """)
        

        cr.execute("""
            DELETE FROM ir_ui_menu 
            WHERE name LIKE %s OR xml_id LIKE %s
        """, ('%deleted%', '%deleted%'))
        
        _logger.info('تم الانتهاء من post-migration بنجاح')
        
    except Exception as e:
        _logger.error(f'خطأ أثناء تنفيذ post-migration: {str(e)}')
        raise

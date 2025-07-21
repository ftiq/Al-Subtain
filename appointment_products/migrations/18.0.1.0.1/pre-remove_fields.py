# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    """
    Migration script لحذف الحقول المحذوفة من الكود بأمان
    يتم تنفيذه قبل تحديث الوحدة
    """
    _logger.info(f'بدء migration لإزالة الحقول المحذوفة - النسخة {version}')
    

    fields_to_remove = [

    ]
    

    tables_to_remove = [

    ]
    
    try:

        for table_name, field_name in fields_to_remove:

            cr.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=%s AND column_name=%s
            """, (table_name, field_name))
            
            if cr.fetchone():
                _logger.info(f'حذف الحقل {field_name} من الجدول {table_name}')
                cr.execute(f'ALTER TABLE {table_name} DROP COLUMN IF EXISTS {field_name}')
            else:
                _logger.info(f'الحقل {field_name} غير موجود في الجدول {table_name}')
        

        for table_name in tables_to_remove:

            cr.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name=%s
            """, (table_name,))
            
            if cr.fetchone():
                _logger.info(f'حذف الجدول {table_name}')
                cr.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
            else:
                _logger.info(f'الجدول {table_name} غير موجود')
        

        for table_name, field_name in fields_to_remove:
            cr.execute("""
                DELETE FROM ir_model_fields 
                WHERE name=%s AND model=%s
            """, (field_name, table_name.replace('_', '.')))
            _logger.info(f'تم حذف تعريف الحقل {field_name} من ir_model_fields')
        

        for table_name, field_name in fields_to_remove:
            cr.execute("""
                DELETE FROM ir_model_data 
                WHERE name LIKE %s AND module=%s
            """, (f'field_{table_name}__{field_name}', 'appointment_products'))
        
        _logger.info('تم الانتهاء من migration بنجاح')
        
    except Exception as e:
        _logger.error(f'خطأ أثناء تنفيذ migration: {str(e)}')
        raise

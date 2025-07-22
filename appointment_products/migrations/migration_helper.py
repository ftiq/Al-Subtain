# -*- coding: utf-8 -*-
"""

"""
import logging

_logger = logging.getLogger(__name__)

class MigrationHelper:

    
    @staticmethod
    def safe_drop_column(cr, table_name, column_name):

        try:

            cr.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name=%s AND column_name=%s
            """, (table_name, column_name))
            
            if cr.fetchone():
                cr.execute(f'ALTER TABLE {table_name} DROP COLUMN {column_name}')
                _logger.info(f'تم حذف العمود {column_name} من الجدول {table_name}')
                return True
            else:
                _logger.info(f'العمود {column_name} غير موجود في الجدول {table_name}')
                return False
        except Exception as e:
            _logger.error(f'خطأ في حذف العمود {column_name}: {str(e)}')
            return False
    
    @staticmethod
    def safe_drop_table(cr, table_name):
        """حذف آمن للجداول"""
        try:

            cr.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name=%s
            """, (table_name,))
            
            if cr.fetchone():
                cr.execute(f'DROP TABLE {table_name} CASCADE')
                _logger.info(f'تم حذف الجدول {table_name}')
                return True
            else:
                _logger.info(f'الجدول {table_name} غير موجود')
                return False
        except Exception as e:
            _logger.error(f'خطأ في حذف الجدول {table_name}: {str(e)}')
            return False
    
    @staticmethod
    def cleanup_model_data(cr, module_name, model_name, field_name=None):

        try:
            if field_name:

                cr.execute("""
                    DELETE FROM ir_model_data 
                    WHERE module=%s AND model='ir.model.fields'
                    AND name LIKE %s
                """, (module_name, f'field_{model_name.replace(".", "_")}__{field_name}'))
            else:

                cr.execute("""
                    DELETE FROM ir_model_data 
                    WHERE module=%s AND model=%s
                """, (module_name, model_name))
            
            _logger.info(f'تم تنظيف بيانات النموذج {model_name}')
        except Exception as e:
            _logger.error(f'خطأ في تنظيف بيانات النموذج: {str(e)}')
    
    @staticmethod
    def backup_data_before_migration(cr, table_name, backup_table_name=None):
        """إنشاء نسخة احتياطية من البيانات"""
        if not backup_table_name:
            backup_table_name = f"{table_name}_backup_{int(time.time())}"
        
        try:
            cr.execute(f'CREATE TABLE {backup_table_name} AS SELECT * FROM {table_name}')
            _logger.info(f'تم إنشاء نسخة احتياطية: {backup_table_name}')
            return backup_table_name
        except Exception as e:
            _logger.error(f'خطأ في إنشاء النسخة الاحتياطية: {str(e)}')
            return None
    
    @staticmethod
    def get_removed_fields_list():
        """قائمة بالحقول المحذوفة - يتم تحديثها حسب الحاجة"""
        return [

        ]
    
    @staticmethod
    def get_removed_tables_list():
        """قائمة بالجداول المحذوفة - يتم تحديثها حسب الحاجة"""
        return [

        ]

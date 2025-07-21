# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Migration script to clean up removed fields
    إزالة الحقول المحذوفة من قاعدة البيانات
    """
    if version is None:
        return
    

    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='stock_picking' 
        AND column_name='related_task_id';
    """)
    
    if cr.fetchone():
        cr.execute("ALTER TABLE stock_picking DROP COLUMN IF EXISTS related_task_id;")
        

    cr.execute("""
        DELETE FROM ir_model_fields 
        WHERE model = 'stock.picking' 
        AND name = 'related_task_id';
    """)

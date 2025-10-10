# -*- coding: utf-8 -*-

from . import models
from . import wizards



from odoo import api, SUPERUSER_ID


def pre_init_hook(cr):
    """Pre-initialization hook for the module."""
    pass


def post_init_hook(env):
    """Post-initialization hook for the module."""
    
    try:
        env.ref('mail.action_discuss')
    except ValueError:
        mail_action = env['ir.actions.act_window'].create({
            'name': 'Discuss',
            'res_model': 'mail.channel',
            'view_mode': 'kanban,list,form',
            'domain': [],
            'context': {},
            'help': '<p class="o_view_nocontent_smiling_face">Start a conversation</p><p>Channels allow you to organize discussions around topics.</p>'
        })
        
        env['ir.model.data'].create({
            'name': 'action_discuss',
            'module': 'mail',
            'model': 'ir.actions.act_window',
            'res_id': mail_action.id,
            'noupdate': True
        })
    
    try:
        env.cr.execute("""
            SELECT m.id, m.name, m.action 
            FROM ir_ui_menu m 
            WHERE m.action LIKE 'ir.actions.client,%%' 
            AND NOT EXISTS (
                SELECT 1 FROM ir_act_client c 
                WHERE CONCAT('ir.actions.client,', c.id) = m.action
            )
        """)
        
        orphaned_menus = env.cr.fetchall()
        
        if orphaned_menus:
            print(f"MGT Documents: Found {len(orphaned_menus)} orphaned client action references")
            

            menu_ids = [menu[0] for menu in orphaned_menus]
            orphaned_menu_records = env['ir.ui.menu'].browse(menu_ids)
            
            for menu in orphaned_menu_records:
                print(f"MGT Documents: Clearing orphaned action reference for menu: {menu.name}")
                menu.action = False
            
            env.cr.commit()
            print("MGT Documents: All orphaned client action references have been cleared")
        
    except Exception as e:
        print(f"MGT Documents: Error fixing orphaned actions: {e}")
    

    categories = [
        {'name': 'مخاطبات واردة', 'code': 'INCOMING', 'description': 'المخاطبات الواردة من الجهات الخارجية'},
        {'name': 'مخاطبات صادرة', 'code': 'OUTGOING', 'description': 'المخاطبات الصادرة للجهات الخارجية'},
        {'name': 'مخاطبات داخلية', 'code': 'INTERNAL', 'description': 'المخاطبات الداخلية بين الأقسام'},
    ]

    for cat_data in categories:
        existing = env['document.category'].search([('code', '=', cat_data['code'])], limit=1)
        if not existing:
            env['document.category'].create(cat_data)
    
    print("MGT Documents: Post-initialization completed")


def uninstall_hook(env):
    """Uninstall hook for the module."""

    pass
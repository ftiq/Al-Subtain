{
    'name': 'إدارة الوثائق والمخاطبات',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'نظام إدارة وأرشفة المخاطبات والوثائق الإدارية',
    'description': """
        نظام شامل لإدارة وأرشفة الوثائق
        ================================================
        
        الميزات الأساسية:

        - إدارة المخاطبات الإدارية (واردة وصادرة)
        - نظام الأرشفة التلقائية
        - البحث المتقدم والاسترجاع
        - نظام الصلاحيات المرن
        - دعم التوقيع الرقمي
        - سير عمل الموافقات الإدارية


    """,
    'author': "المهندس / صالح الحجاني",
    'website': "https://www.facebook.com/salh.alhjany/?rdid=plWVCqF0AkDERe3g",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'web',
        'web_editor',
        'portal',
        'certificate',
        'approvals',
        'documents',
        'html_editor',
    ],
    'data': [

        'data/sequences.xml',
        'data/approval_categories.xml',
        'data/copy_messages.xml',
        'data/notification_templates.xml',
        'data/email_templates.xml',
        
        

        'data/ir_sequence.xml',
        'data/document_categories.xml',
        'data/mail_templates.xml',
        'data/document_type_defaults.xml',
        

        'security/mgt_documents_groups.xml',
        'security/ir.model.access.csv',
        'security/copy_access_rules.xml',
        

        'views/mgt_documents_actions.xml',      
        'views/mgt_documents_menus.xml',
        'views/document_copy_wizard_views.xml', 
        'views/document_document_views.xml',
        'views/document_category_views.xml',
        'views/document_history_views.xml',
        'views/copy_message_views.xml',
        'views/digital_signature_views.xml',
        'views/digital_signature_wizard_views.xml',
        'views/document_approval_wizard_views.xml',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mgt_documents/static/src/scss/mgt_documents_scoped.scss',
            'mgt_documents/static/src/scss/document_html_editor.scss',
            'mgt_documents/static/src/scss/ckeditor5_widget.scss',
            'mgt_documents/static/src/scss/rich_text_widget.scss',
            'mgt_documents/static/src/scss/mgt_documents_scoped.scss',
            'mgt_documents/static/src/css/document_kanban.css',
            'mgt_documents/static/src/css/document_dashboard.css',
            'mgt_documents/static/src/js/document_dashboard.js',
            'mgt_documents/static/src/xml/dashboard_template.xml',

        ],
        'web.assets_frontend': [
            'mgt_documents/static/src/scss/mgt_documents_portal.scss',
        ],
    },
    'demo': [

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
} 

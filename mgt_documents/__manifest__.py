{
    'name': 'إدارة الوثائق والمخاطبات',
    'version': '18.0.1.0.0',
    'category': 'Document Management',
    'summary': 'نظام إدارة وأرشفة الكتب الإلكترونية والمخاطبات الإدارية',
    'description': """
        نظام شامل لإدارة وأرشفة الوثائق
        ================================================
        
        الميزات الأساسية:
        - إدارة الكتب الإلكترونية
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
        'portal',
        'certificate',
        'approvals',
    ],
    'data': [
        # Security
        'security/mgt_documents_groups.xml',
        'security/ir.model.access.csv',
        # 'security/mgt_documents_security.xml',  # مؤقتاً معلق
        

        'data/ir_sequence.xml',
        'data/document_categories.xml',
        'data/mail_templates.xml',
        

        'views/document_document_views.xml',
        'views/document_category_views.xml',
        'views/approval_request_views.xml',
        'views/digital_signature_views.xml',
        'views/document_history_views.xml',
        'views/document_report_views.xml',
        'views/mgt_documents_actions.xml',
        'views/mgt_documents_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mgt_documents/static/src/scss/mgt_documents.scss',
            'mgt_documents/static/src/js/document_kanban.js',
            'mgt_documents/static/src/js/document_dashboard.js',
            'mgt_documents/static/src/xml/document_templates.xml',
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
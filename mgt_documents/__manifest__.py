{
    'name': 'إدارة الوثائق والمخاطبات',
    'version': '18.0.1.0.1',
    'category': 'Document Management',
    'summary': 'نظام إدارة وأرشفة المخاطبات والوثائق الإدارية',
    'description': """
        نظام شامل لإدارة وأرشفة الوثائق
    """,
    'author': "engineer / saleh alhjany",
    'website': "https://www.facebook.com/salh.alhjany/?rdid=plWVCqF0AkDERe3g",
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'web',
    ],
    'data': [

        'security/mgt_documents_groups.xml',
        'security/ir.model.access.csv', 
        'security/document_access_rules.xml',
        'security/approval_access_rules.xml',
        
        
        'data/mail_compatibility.xml',
        'data/sequences.xml',
        'data/ir_sequence.xml',
        'data/ir_cron_jobs.xml',
        'data/ir_model_data.xml',
        'data/approval_categories.xml',
        'data/document_categories.xml', 
        'data/document_type_defaults.xml',
        'data/email_templates.xml',
        'data/mail_templates.xml',
        'data/mgt_demo_org.xml',
                
        'views/mgt_documents_actions.xml',
        'views/mgt_documents_menus.xml',
        'views/document_router_views.xml',
        'views/document_version_views.xml',
        'views/dashboard_views.xml',
        

        'views/admin_task_views.xml',
        'views/workflow_step_views.xml',
        'views/workflow_process_views.xml',
        'views/document_workflow_instance_views.xml',
        'views/document_document_views.xml',
        'views/document_category_views.xml',
        'views/document_history_views.xml',
        'views/res_config_settings_views.xml',
        'views/approval_task_assignment_wizard_views.xml',
        'views/approval_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mgt_documents/static/src/scss/mgt_documents_scoped.scss',
            'mgt_documents/static/src/css/document_kanban.css',
            'mgt_documents/static/src/css/mgt_documents_kanban.css',
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

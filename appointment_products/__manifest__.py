# -*- coding: utf-8 -*-
{
    'name': "المواعيد والخدمات الميدانية المتقدمة",
    'summary': "نظام شامل لإدارة مهام الخدمة الميدانية والمختبرات مع ربط المنتجات بالمواعيد",
    'description': """
        نظام شامل لإدارة مهام الخدمة الميدانية والمختبرات مع ربط المنتجات بالمواعيد:
        
        الميزات الرئيسية:
        ================
        * إدارة المواعيد والخدمات الميدانية
        * ربط المنتجات بالمواعيد
        * نظام فحوصات مختبرية ديناميكي
        * قوالب فحص قابلة للتكوين
        * معايير فحص مرنة
        * إدارة العينات والنتائج
        * مراحل فحص متعددة
        * تكامل مع نظام الجودة
        * تتبع دقيق للنتائج

    """,
    'author': "المهندس / صالح الحجاني",
    'website': "https://www.facebook.com/salh.alhjany/?rdid=plWVCqF0AkDERe3g",
    'category': 'Services/Appointments',
    'version': '1.0',
    'depends': [
        'appointment', 
        'product', 
        'website_appointment', 
        'website_sale', 
        'website_sale_stock', 
        'web', 
        'sale_management', 
        'phone_validation', 
        'industry_fsm', 
        'industry_fsm_sale', 
        'industry_fsm_report', 
        'stock', 
        'quality',
        'quality_control', 
        'sale_project'
    ],
    'data': [

        'security/lab_groups.xml',
        'security/ir.model.access.csv',
        'security/task_attachment_rules.xml',
        'data/fsm_task_sequence.xml',
        'data/stock_picking_lab_actions.xml',
        'data/brick_test_templates.xml',
        'views/appointment_product_views.xml',
        'views/appointment_products_templates.xml',
        'views/project_task_signature_views.xml',
        'views/sale_order_question_views.xml',
        'views/portal_task_extra_views.xml',
        'views/project_task_question_views.xml',
        'views/product_template_service_views.xml',
        'views/project_task_service_views.xml',
        'views/project_task_form_views.xml',
        'views/project_task_stock_done_views.xml',
        'views/report_task_extra_views.xml',
        'views/appointment_config_settings_views.xml',
        'views/stock_move_line_views.xml',
        'views/project_task_buttons.xml',
        'views/stock_picking_buttons.xml',
        'views/stock_picking_lab_notify_views.xml',
        'views/sale_order_buttons.xml',
        'views/stock_picking_report_custom.xml',
        'views/stock_picking_signature_views.xml',
        'views/stock_move_line_signature_views.xml',
        'views/project_task_extra_signatures_views.xml',
        'views/product_labels_simple_enhancement.xml',
        'views/sample_product_config_views.xml',
        'views/sale_order_views_inherit_project_name.xml',
        'views/project_task_attachments_views.xml',
        'views/task_attachment_wizard_views.xml',
        'views/lab_test_template_views.xml',
        'views/lab_sample_views.xml',
        'views/lab_result_set_views.xml',
        'views/lab_menus.xml',
        'views/quality_lab_integration_views.xml',
        'views/lab_result_dynamic_input_views.xml',
        'views/lab_test_flow_views.xml',
        'reports/lab_result_set_report.xml',
        'data/lab_sample_sequence.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/jquery/jquery.js',
            'appointment_products/static/src/js/appointment_products.js',
            'appointment_products/static/src/js/appointment_cart.js',
        ],
        'web.assets_backend': [
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/src/scss/pre_variables.scss',
            'appointment_products/static/src/css/lab_chatter_fix.css',
            'appointment_products/static/src/css/dynamic_results_table.css',
            'appointment_products/static/src/scss/lab_sample_kanban.scss',
            'appointment_products/static/src/js/lab_sample_kanban.js',
        ],
    },
    'icon': 'appointment_products/static/description/lab_icon.svg',
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'demo': [

    ],
}

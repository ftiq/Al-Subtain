{
    'name': 'Appointment Sales and Attachments',
    'version': '18.0.1.0.0',
    'summary': 'Add product and attachment fields to appointments with automatic sales orders',
    'description': """
        This module extends appointment functionality to:
        - Add product selection to appointment types
        - Allow file uploads during booking
        - Automatically create sales orders
        - Track attachments with appointments
        - Link appointments to sales orders
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'category': 'Services/Appointment',
    'depends': [
        'appointment', 
        'sale_management',
        'calendar',
        'portal'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
        'views/sale_order_views.xml',
        'static/src/xml/appointment_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'appointment_sale_attachment/static/src/js/appointment_form.js',
        ],
        'web.assets_backend': [
            'appointment_sale_attachment/static/src/js/sale_order_kanban.js',
        ],
    },
    'demo': [
        'demo/appointment_type_demo.xml',
        'demo/product_demo.xml',
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
    'images': ['static/description/icon.png'],
    'post_init_hook': '_post_init_hook',
}

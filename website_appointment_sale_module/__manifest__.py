{
    'name': 'Website Appointment with Service and Attachment',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Add service and attachment to appointment and auto-create sale order',
    'depends': ['appointment', 'sale_management', 'website'],
    'data': [
        'views/appointment_type_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_appointment_sale_module/static/src/xml/website_appointment_templates.xml',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': False
}
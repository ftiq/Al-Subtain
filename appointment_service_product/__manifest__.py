# -*- coding: utf-8 -*-
{
    'name': "Appointment Service Product Selection",
    'summary': """
        Add product/service selection to website appointments""",
    'description': """
        This module extends website appointments to allow customers
        to select a specific product/service when booking appointments.
    """,
    'author': "Your Name",
    'website': "http://www.yourcompany.com",
    'category': 'Services/Appointment',
    'version': '18.0.1.0.0',
    'depends': [
        'website_appointment',  # Main appointment module
        'website',              # Website functionality
        'product',             # Product management
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/appointment_views.xml',
        'views/appointment_templates.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_frontend': [
            'appointment_service_product/static/src/js/website_appointment.js',
        ],
    },
}

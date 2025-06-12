{
    'name': 'Appointment Product Integration',
    'version': '1.0',
    'summary': 'Select products/services during appointment booking',
    'author': 'Your Name',
    'depends': ['website_appointment', 'product'],
    'data': [
        'views/appointment_product_views.xml',
        'views/website_appointment_templates.xml',
    ],
    'installable': True,
    'application': False,
}

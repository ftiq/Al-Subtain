{
    'name': 'Custom Appointment Products',
    'version': '1.0',
    'summary': 'Add product selection to website appointments',
    'description': 'Allows customers to select products/services when booking appointments',
    'author': 'Your Name',
    'depends': ['website_appointment', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/appointment_views.xml',
        'views/appointment_templates.xml',
    ],
    'installable': True,
    'application': False,
}

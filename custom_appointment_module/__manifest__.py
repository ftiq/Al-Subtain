{
    'name': 'Appointment Sales and Attachments',
    'version': '18.0.1.0.0',
    'summary': 'Add product and attachment fields to appointments',
    'description': 'Extends appointments with products and attachments',
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'category': 'Services/Appointment',
    'depends': ['appointment', 'sale_management', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
        'static/src/xml/appointment_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

{
    'name': 'Custom Appointment Sales',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Create Sale Order from Appointment Form',
    'description': 'Generate Sale Order from Appointment and Save Attachment',
    'depends': ['appointment', 'sale'],
    'data': [
        'views/appointment_templates.xml',
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Include any custom CSS/JS here if needed
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

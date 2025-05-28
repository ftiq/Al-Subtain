{
    'name': 'Appointment Sales and Attachments',
    'version': '1.0',
    'summary': 'Add product and attachment to appointments',
    'description': """
        This module extends appointment functionality to:
        - Add product to appointment types
        - Allow file uploads during booking
        - Create sales orders automatically
    """,
    'author': 'Your Name',
    'website': 'https://yourwebsite.com',
    'category': 'Services/Appointment',
    'depends': ['appointment', 'sale'],
    'data': [
        'views/appointment_type_views.xml',
        'views/calendar_event_views.xml',
        'static/src/xml/appointment_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

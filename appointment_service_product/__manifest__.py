{
    'name': 'Calendar Event Product Selection',
    'version': '18.0.1.0.0',
    'summary': 'Add product/service selection to calendar events',
    'description': 'Allows selecting products/services when booking calendar appointments',
    'author': 'Your Name',
    'depends': ['calendar', 'website_calendar', 'product'],
    'data': [
        'views/calendar_event_views.xml',
        'views/website_calendar_templates.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

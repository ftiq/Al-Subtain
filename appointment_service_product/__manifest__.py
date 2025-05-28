{
    'name': 'Appointment Product Selection',
    'version': '1.0',
    'depends': [
        'calendar',    # Base calendar functionality
        'website',     # Website features
        'product',     # Product management
    ],
    'data': [
        'views/calendar_event_views.xml',
        'views/website_templates.xml',
    ],
    'installable': True,
    'application': False,
}

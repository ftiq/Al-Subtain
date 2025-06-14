{
    'name': 'Internal Mail System',
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'views/internal_mail_views.xml',
        'views/internal_mail_menus.xml',
        'data/sequence_data.xml',
        'data/email_template_data.xml',
    ],
    'installable': True,
    'application': True,
}

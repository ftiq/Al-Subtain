{
    'name': 'Project Correspondence',
    'version': '1.0',
    'summary': 'أرشفة ومراسلات الكتب الداخلية والخارجية والفنية والواردة',
    'description': """Module to manage correspondence:
- Outgoing internal, external, technical.
- Incoming documents.
- Workflow with states, archiving, logging, notifications.""",
    'author': 'Your Company',
    'category': 'Tools',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'data/sequence_data.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/correspondence_views.xml',
        'views/dashboard_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'project_correspondence/static/src/js/dashboard.js',
            'project_correspondence/views/dashboard_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
{
    'name': 'HR Timeoff Monthly Accrual',
    'version': '18.0.1.3.0',
    'category': 'Human Resources',
    'summary': 'Monthly and annual time-credit allocations with carry-over, expirations, alerts, and settings view',
    'author': 'Business Technology',
    'depends': ['hr_holidays', 'mail'],
    'data': [
        'data/hr_leave_type_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/hr_leave_type_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
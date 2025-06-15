{
    'name': 'HR Timeoff Monthly Accrual',
    'version': '18.0.1.1.0',
    'category': 'Human Resources',
    'summary': 'Monthly and annual time-credit allocations with carry-over, expirations, and alerts',
    'author': 'Business Technology',
    'depends': ['hr_leave', 'mail'],
    'data': [
        'data/hr_leave_type_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
# -*- coding: utf-8 -*-
{
    'name': 'HR Overtime Request',
    'summary': 'Employee overtime request with approval and conversion to leave or payroll input',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'author': "Salah Alhjany",
    'website': "https://wa.me/967711778764",
    'license': 'LGPL-3',
    'depends': ['hr', 'hr_holidays', 'hr_payroll', 'hr_attendance', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/payslip_input_type.xml',
        'data/leave_type.xml',
        'data/salary_rule_overtime.xml',
        'data/cron.xml',
        'data/demo_overtime.xml',
        'views/overtime_request_views.xml',
    ],
    'application': False,
    'installable': True,
}

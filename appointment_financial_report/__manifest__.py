# -*- coding: utf-8 -*-
{
    'name': 'Appointment Financial Voucher Report',
    'summary': 'Custom financial voucher report for field service/appointments',
    'version': '1.0.0',
    'category': 'Accounting',
    'author': "Salah Alhjany",
    'website': "https://wa.me/967711778764",
    'license': 'OEEL-1',
    'depends': [
        'account',
        'sale_management',
        'project',
        'appointment_products',
    ],
    'data': [
        'security/ir.model.access.csv',
        'reports/financial_voucher_report.xml',
        'views/forms_summary_wizard.xml',
        'reports/forms_summary_report.xml',
    ],
    'assets': {},
    'installable': True,
    'application': False,
}

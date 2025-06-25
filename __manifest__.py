# -*- coding: utf-8 -*-
{
    'name': 'تخطيط التقارير المخصص',
    'version': '18.0.1.1.0',
    'category': 'Reporting',
    'summary': 'تخطيط مخصص للترويسة والتذييل في جميع التقارير',
    'description': """
        هذا المديول يقوم بتخصيص الترويسة والتذييل لجميع التقارير في الأودو:
        - الترويسة: تحتوي على صورة الترويسة المخصصة بحجم 20 سم × 3 سم
        - التذييل: يحتوي على صورة التذييل المخصصة بنفس الحجم
        - يطبق على جميع التقارير في النظام
        - حقول منفصلة للترويسة والتذييل (غير مرتبطة بشعار الشركة الافتراضي)
    """,
    'author': 'المهندس/صالح الحجاني',
    'website': "https://www.facebook.com/salh.alhjany/?rdid=plWVCqF0AkDERe3g",
    'depends': ['web', 'base', 'appointment_products'],
    'data': [
        'views/res_company_views.xml',
        'views/report_templates.xml',
        'views/appointment_report_inherit.xml',
        'data/report_layout_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
} 
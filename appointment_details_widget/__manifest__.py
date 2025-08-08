{
    'name': 'Appointment Details Widget',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Adds appointment details widget button to sale orders list view',
    'author': "المهندس / صالح الحجاني",
    'website': "https://www.facebook.com/salh.alhjany/?rdid=plWVCqF0AkDERe3g",
    'license': 'LGPL-3',
    'depends': ['sale', 'appointment_products', 'project', 'sale_project'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'appointment_details_widget/static/src/css/appointment_widget.css',
            'appointment_details_widget/static/src/xml/appointment_widget.xml',
            'appointment_details_widget/static/src/js/appointment_details_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': True,
} 
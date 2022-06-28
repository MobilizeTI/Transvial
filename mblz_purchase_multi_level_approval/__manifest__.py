# -*- coding: utf-8 -*-
{
    'name': "MBLZ: Aprobación de RFQ múlti-nivel",

    'summary': """
        Aplicación de aprobación de múltiples niveles de órdenes de compra""",
    'description': """
    """,

    'website': "https://www.mobilize.cl",
    'category': 'Mobilize/Apps',
    'version': '0.1',
    'author': 'Mobilize (Cristóbal OCH)',
    'live_test_url': 'https://drive.google.com/file/d/1XMlU16X7VFOCTbpNYLi9hdhPDBqIfFcq/view?usp=sharing',
    # any module necessary for this one to work correctly
    'depends': ['purchase', 'mail', 'web_notify'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/document_approval.xml',
        'views/res_config_settings.xml',
        'views/purchase_order.xml',
        'views/res_users.xml',

        'wizard/wz_approve.xml',

        'data/mail_template.xml',

    ],
    # only loaded in demonstration mode
    'demo': [],
}

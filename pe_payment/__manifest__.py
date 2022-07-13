# -*- coding: utf-8 -*-
{
    'name': "Pagos (Perú)",

    'summary': """
       1.- Pagos masivos a multi proveedores
       
       """,

    'description': """
        Cambios al modulo de pagos 
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Perú/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'mblz_utils'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/payment_multi.xml',
        'wizard/load_invoices_wizard.xml',

        'data/functions.xml'

    ],
    'uninstall_hook': 'clear_seq_payment_multi_hook'

}

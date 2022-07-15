# -*- coding: utf-8 -*-
{
    'name': "Base (Perú)",

    'summary': """
        1.- Asignar series a los documentos
        2.- Asignar secuencias de sistema a facturas de cliente y proveedor
        """,

    'description': """
        Configuraciones generales para la localización peruana by Mobilize
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Perú/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'l10n_latam_invoice_document'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/invoice_series.xml',

        'views/account_journal.xml',
        'views/account_move.xml',

        # función para crear las secuencias relacionas al correlativo de sistema para facturas de cliente y proveedor
        'data/functions.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    'uninstall_hook': 'clear_seq_customer_supplier_invoice_hook'

}

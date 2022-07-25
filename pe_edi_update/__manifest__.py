# -*- coding: utf-8 -*-
{
    'name': "EDI for Perú (by MBLZ)",

    'summary': """
        1.- Asignar series a las facturas de cliente
        """,

    'description': """
        Configuraciones generales para la localización peruana by Mobilize
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Perú/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'l10n_pe_edi', 'l10n_latam_invoice_document', 'pe_base'],

    # always loaded
    'data': [
        'security/security_edi.xml',
        'security/ir.model.access.csv',

        'views/edi_invoice_series.xml',
        'views/account_journal.xml',
        'views/account_move.xml',

        'data/2.1/edi_common.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
    # 'uninstall_hook': 'clear_seq_customer_supplier_invoice_hook'

}

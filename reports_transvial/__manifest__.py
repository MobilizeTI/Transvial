# -*- coding: utf-8 -*-
{
    'name': "Reportes: Transvial",

    'summary': """
            1.- Reporte de asientos contables (Pagos)
        """,

    'description': """
        Reportes exclusivos para transvial
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Transvial/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['account', 'l10n_pe_mblz', 'pe_edi_detraction'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'reports/report_payment_receipt_document_transvial.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}

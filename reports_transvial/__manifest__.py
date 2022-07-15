# -*- coding: utf-8 -*-
{
    'name': "Reportes: Transvial",

    'summary': """
            1.- Reporte de asientos contables (facturas)
            2.- Reporte de asientos contables (Pagos)
        """,

    'description': """
        Reportes exclusivos para transvial (PE)
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Transvial/Apps',
    'version': '0.1',

    'depends': ['account',
                'pe_base',
                'l10n_pe_mblz',
                'pe_edi_detraction'
                ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'reports/report_payment_receipt_document_transvial.xml',

        # reporte de apuntes contables
        'reports/report_account_entries.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}

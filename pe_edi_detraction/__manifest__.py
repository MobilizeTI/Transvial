# -*- coding: utf-8 -*-
{
    'name': "mblz: Detracciones",

    'summary': """
        Cambios en el proceso de detracción PE""",

    'description': """
    """,

    'author': "Mobilize SPA",
    'website': "https://www.mobilize.cl",
    'category': 'Perú/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'l10n_pe_edi', 'l10n_latam_invoice_document', 'mblz_utils'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/table_option_detraction.xml',

        'views/option_table_detraction.xml',
        'views/product_template.xml',
        'views/res_config_settings.xml',
        'views/res_partner.xml',
        'views/account_move.xml',

        # 'wizard/account_payment_register_views.xml',

        'reports/report_invoice.xml',

        # reporte de apuntes contables
        'reports/report_account_entries.xml',

        # función para crear las secuencias relacionas al correlativo de sistema para facturas de proveedor
        'data/functions.xml'
    ],
    'uninstall_hook': 'clear_seq_supplier_invoice_hook'

}

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
    'depends': ['l10n_pe_edi'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/table_option_detraction.xml',

        'views/option_table_detraction.xml',
        'views/product_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}

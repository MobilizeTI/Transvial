# -*- coding: utf-8 -*-
{
    'name': "Base (Perú)",

    # 'summary': """
    #     (x) 2.- Asignar secuencias de sistema a facturas de cliente y proveedor
    #     """,

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
        'security/ir.model.access.csv',

        'menu/pe.xml',

        'base/sunat_electronic_book.xml',

        # tablas
        'tablas/tabla_ocho_codigo_libro_registro.xml',

        # libros electrónicos sunat
        'data/electronic_book.xml',
        'data/pe_code_book_table_08.csv'
    ],
    # only loaded in demonstration mode
    'demo': [],

}

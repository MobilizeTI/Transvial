# -*- coding: utf-8 -*-
{
    'name': 'Validador de RUC - Peru',
    'version': '0.0.1',
    'author': 'OPeru',
    'category': 'Perú/Apps',

    'summary': 'RUC validator - PERU',
    'license': 'LGPL-3',
    'contributors': [
        'Enrique Huayas <enrique@operu.pe>',
        'Leonidas Pezo <leonidas@operu.pe>',
        'Cristóbal Olano Chávez <cristobal@mobilize.cl>',
    ],
    'description': """
                    Validador RUC
                    -----------------------
                    Clientes y Proveedores:
                    -----------------------
                        * Nuevo campo "tipo de documento"
                        * Validacion RUC
                    Dependencias:
                    -------------
                    $ sudo pip3 install beautifulsoup4

    """,
    'depends': ['l10n_latam_base', 'l10n_pe'],
    'data': [
        "data/ir_config_parameter.xml",
        'views/res_partner_view.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
    ],
    'qweb': [

    ],
    'demo': [
        # 'demo/account_demo.xml',
    ],
    'test': [
        # 'test/account_test_users.yml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'support': 'soporte@operu.pe',
    'installable': True,
    'auto_install': False,
    # "sequence": 1,

    'post_init_hook': '_pe_ruc_validation_init',
}

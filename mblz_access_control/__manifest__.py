# -*- coding: utf-8 -*-

{
    "name": "MBLZ: Access Control",
    "version": "1.0",
    "author": "Mobilize",
    "license": 'LGPL-3',
    "category": "Mobilize/Tools",
    "description": "Control de acceso a los usuario utilizando perfiles",
    "summary": "Control de acceso a los usuario utilizando perfiles",
    "depends": ['base', 'web', 'hide_menu_user'],
    "data": [
        'security/security.xml',

        "views/res_users_view.xml",
        "data/res_users_data.xml",
        "views/res_groups_view.xml",
        'views/res_company_view.xml',

        'views/templates.xml',

    ],
    "demo": [],
    'qweb': [
        "static/src/xml/base.xml",
    ],
    "installable": True,
    "active": False,
    "uninstall_hook": "uninstall_hook",
}

# créditos SMILE

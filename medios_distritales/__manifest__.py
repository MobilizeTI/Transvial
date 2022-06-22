# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Medios Distritales',
    'version' : '1.1',
    'summary': '',
    'sequence': 10,
    'description': """
        
    """,
    'category': 'Account',
    'depends' : [
        'base',
        'account',
        'account_reports',
        'l10n_co_reports',
        ],
    'data': [
        'views/account_account_filter.xml',
        'views/assets.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

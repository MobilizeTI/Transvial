# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Tree Payment View MBLZ',
    'version': '1.1',
    'sequence': 10,
    'description': """

    """,
    'category': 'Account',
    'website': '',
    'images': [],
    'depends': ['base','account'],
    'data': [
        'views/account_payment_view.xml',
        'views/res_partner_bank_view.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

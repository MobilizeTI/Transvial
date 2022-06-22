# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Validate Qty in Picking',
    'sequence': 10,
    'description': """
        Valida las cantidades hechas contra las cantidades demandadas
        No permite validar un picking cuando la cantidad hecha es superior a las de demanda
    """,
    'website': "https://www.mobilize.cl",
    'category': 'Mobilize/Apps',
    'version': '1.1',
    'depends': ['stock'],
    'data': ['views/stock_picking_views.xml'],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

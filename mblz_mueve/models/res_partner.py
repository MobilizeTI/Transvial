# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import models, fields, api, _

ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')


class Partner(models.Model):
    _inherit = 'res.partner'

    type_client_tkt = fields.Selection(
        string='Tipo de tícket',
        selection=[('glider', 'Planeador'),
                   ('technical-its', 'Técnico ITS'),
                   ('supervisor-mtto', 'Supervisor MTTO'),
                   ('other', 'Otro'),
                   ],
        required=False,
        help='Solo los clientes que tengan algun valor asigado (Planeador, Técnico ITS o Supervisor MTTO) podrán ser asignados como clientes en los tickets nuevos')

    # Cambios para el header del reporte
    # @api.model
    # def _address_fields(self):
    #     """Returns the list of address fields that are synced from the parent."""
    #     return list(ADDRESS_FIELDS)

# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class SunatElectronicBook(models.Model):
    _name = 'sunat.electronic_book'
    _description = 'Libro Electrónicos (TABLA_8 SUNAT)'

    name = fields.Char(string='Nombre', required=True)
    description = fields.Char(string='Descripción', required=True)
    code_le = fields.Char(string='Código', required=True)
    state = fields.Selection([('enable', 'Disponible'),
                              ('disable', 'No disponible')], string='Estado')
    nro_order = fields.Char(string='Número Orden')

    def name_get(self):
        return [(record.id, record.description) for record in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('nro_order', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

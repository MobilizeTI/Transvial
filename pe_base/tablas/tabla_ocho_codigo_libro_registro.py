# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class PECodeBook(models.Model):
    _name = 'pe_code_book_table_08'
    _description = 'TABLA 8: CÓDIGO DEL LIBRO O REGISTRO'

    name = fields.Char(string='NOMBRE O DESCRIPCIÓN', required=True)
    code = fields.Char(string='CÓDIGO', required=True)

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'El nombre del libro debe ser unico'),
        ('unique_code', 'unique (code)', 'El código del libro debe ser unico'),
    ]

    def name_get(self):
        return [(record.id, f'[{record.code}]{record.name}') for record in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

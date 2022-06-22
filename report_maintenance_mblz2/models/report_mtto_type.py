# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ReportMttoType(models.Model):
    _name = 'report.mtto.type'
    _description = 'Tipos de reporte mtto'

    code = fields.Char(string='Code', required=True, copy=False)
    name = fields.Char(string='Name', required=True, copy=False)
    internal_group = fields.Selection([
        ('level1', 'Nivel 1'),
        ('level2', 'Nivel 2'),
        ('other', 'Otros')
    ], string="Internal Group",
        required=True)

    active = fields.Boolean(default=True)
    sequence = fields.Integer(required=True, default=10)
    note = fields.Text(string='Description')

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f'[{record.code}] {record.name} '))
        return result

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'The activity name must be unique!'),
        ('unique_code', 'unique (code)', 'The activity code must be unique!'),
    ]

# -*- coding: utf-8 -*-

from odoo import fields, api, models
from odoo.exceptions import ValidationError


class InvoiceSeries(models.Model):
    _name = 'invoice.series'
    _check_company_auto = True

    company_id = fields.Many2one('res.company',
                                 string='Compañía',
                                 required=True, default=lambda self: self.env.company, readonly=True)
    name = fields.Char('Descripción', size=4, required=True)
    # journal_id = fields.Many2one('account.journal', 'Diario asociado',
    #                              readonly=True, check_company=True, copy=False)

    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id)',
         '¡El nombre de la serie debe ser unico por compañía!'),
    ]

# -*- coding: utf-8 -*-

import re
from odoo import fields, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Número de serie',
                                       required=False)
    required_serie = fields.Boolean(string='Utilizan serie', related='journal_id.required_serie')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Serie',
                                       related='move_id.invoice_serie_id', store=True)

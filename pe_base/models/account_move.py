# -*- coding: utf-8 -*-

import re
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    name_seq_system = fields.Char(
        'Correlativo', copy=False, readonly=True, default=lambda x: _('/'),
        help='Correlativo del sistema para facturas de proveedor')

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Número de serie',
                                       required=False)
    required_serie = fields.Boolean(string='Utilizan serie', related='journal_id.required_serie')

    @api.model
    def create(self, values):
        move_new = super(AccountMove, self).create(values)
        if move_new.move_type == 'in_invoice' and move_new.name_seq_system == '/':
            move_new.name_seq_system = self.env['ir.sequence'].next_by_code('seq.supplier.invoice') or _('/')
        elif move_new.move_type == 'out_invoice' and move_new.name_seq_system == '/':
            move_new.name_seq_system = self.env['ir.sequence'].next_by_code('seq.customer.invoice') or _('/')
        return move_new


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Serie',
                                       related='move_id.invoice_serie_id', store=True)

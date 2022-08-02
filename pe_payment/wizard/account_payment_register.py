# -*- coding: utf-8 -*-
from lxml import etree

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # is_pay_detraction = fields.Boolean(string='Pago detracción', required=False)
    option_pay = fields.Selection(
        string='Opción de pago',
        selection=[('base', 'Comprobante'),
                   ('detraction', 'Detracción')],
        required=True, default='base')

    is_invisible = fields.Boolean(compute='_compute_is_invisible')

    @api.depends('line_ids')
    def _compute_is_invisible(self):
        for record in self:
            record.is_invisible = len(record.line_ids.filtered_domain([('is_detraction', '=', True)])) <= 0

    @api.onchange('option_pay')
    def onchange_option_pay(self):
        self._upd_line_ids()
        if self.option_pay == 'detraction':
            self.line_ids = [(6, 0, self.line_ids.filtered_domain([('is_detraction', '=', True)]).ids)]
        else:
            self.line_ids = [(6, 0, self.line_ids.filtered_domain([('is_detraction', '=', False)]).ids)]

    def _upd_line_ids(self):
        if self._context.get('active_model') == 'account.move':
            lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
        elif self._context.get('active_model') == 'account.move.line':
            lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
        else:
            raise UserError(_(
                "The register payment wizard should only be called on account.move or account.move.line records."
            ))

            # Keep lines having a residual amount to pay.
        available_lines = self.env['account.move.line']
        for line in lines:
            if line.move_id.state != 'posted':
                raise UserError(_("You can only register payment for posted journal entries."))

            if line.account_internal_type not in ('receivable', 'payable'):
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available_lines |= line

        # Check.
        if not available_lines:
            raise UserError(
                _("You can't register a payment because there is nothing left to pay on the selected journal items."))
        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if len(set(available_lines.mapped('account_internal_type'))) > 1:
            raise UserError(
                _("You can't register payments for journal items being either all inbound, either all outbound."))

        self.line_ids = [(6, 0, available_lines.ids)]

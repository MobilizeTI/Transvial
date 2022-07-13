# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import models, fields, api, _
from odoo.tools import groupby
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from odoo.exceptions import UserError, ValidationError


class LoadInvoicesWizard(models.TransientModel):
    _name = "load.invoice.wizard"
    _description = "Carga de comprobantes"

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company, readonly=True
    )
    partner_ids = fields.Many2many('res.partner', string='Clientes/Proveedores', readonly=True)
    invoices_ids = fields.Many2many('account.move.line', string='Comprobante(s)', required=True)

    payment_multi_id = fields.Many2one('account.payment', required=True)
    # aml_exclude_ids = fields.Many2many('account.move.line', 'rel_load_invoice_wizard_aml_exclude')
    domain_invoice_ids = fields.One2many('account.move.line', compute='_compute_domain_invoice_ids')

    @api.depends('partner_ids')
    def _compute_domain_invoice_ids(self):
        for rec in self:
            rec.domain_invoice_ids = [(6, 0, rec.get_domain_invoice_ids())]

    def get_domain_invoice_ids(self):
        domain = [
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('account_internal_type', 'in', ('receivable', 'payable')),
            ('partner_id', 'in', self.partner_ids.ids),
            ('company_id', '=', self.env.company.id)
        ]

        invoices = self.env['account.move.line'].sudo().search(domain)

        return self._clear_domain_invoices(lines=invoices)

    def _clear_domain_invoices(self, lines):
        # Mantener las líneas teniendo una cantidad residual a pagar.
        available_lines = self.env['account.move.line']
        for line in lines:
            if line.move_id.state != 'posted':
                raise UserError(_("Sólo se puede registrar el pago de los asientos contabilizados."))

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
                _("No puede registrar un pago porque no queda nada por pagar en los artículos del diario seleccionados."))
        if len(lines.company_id) > 1:
            raise UserError(
                _("No puede registrar un pago porque no queda nada por pagar en los artículos del diario seleccionados."))
        if len(set(available_lines.mapped('account_internal_type'))) > 1:
            raise UserError(
                _("No se pueden registrar pagos para partidas de diario que sean todas de entrada o todas de salida."))

        return available_lines.ids

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        self._compute_domain_invoice_ids()

    def action_load_invoices(self):
        pass

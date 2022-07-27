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
    partner_ids = fields.Many2many('res.partner', string='Proveedores', readonly=True)
    invoices_ids = fields.Many2many('account.move.line', string='Comprobante(s)', required=False)

    payment_multi_id = fields.Many2one('account.payment_multi', required=True)
    partner_type = fields.Selection([
        ('customer', 'Cliente'),
        ('supplier', 'Proveedor'),
    ], default='customer', tracking=True, required=True)
    domain_invoice_ids = fields.One2many('account.move.line', compute='_compute_domain_invoice_ids')

    select_all = fields.Boolean(string='select_all', required=True)
    is_pay_detraction = fields.Boolean(string='Pago detracción', required=False)

    @api.depends('partner_ids', 'partner_type')
    def _compute_domain_invoice_ids(self):
        for rec in self:
            rec.domain_invoice_ids = [(6, 0, rec.get_domain_invoice_ids())]

    def _date_maturity_domain(self):
        domain = []
        if self.payment_multi_id.range == 'date':
            domain.append(('date_maturity', '<=', self.payment_multi_id.date_def))
        elif self.payment_multi_id.range in ('month', 'dates'):
            self.payment_multi_id.onchange_range()
            domain += [('date_maturity', '>=', self.payment_multi_id.date_start),
                       ('date_maturity', '<=', self.payment_multi_id.date_end)]
        return domain

    def get_domain_invoice_ids(self):
        domain = [
            ('parent_state', '=', 'posted'),
            ('parent_payment_state', '=', 'not_paid'),
            ('reconciled', '=', False),
            ('currency_id', '=', self.payment_multi_id.currency_id.id),
            ('company_id', '=', self.env.company.id)
        ]
        if self.partner_ids:
            domain += [('partner_id', 'in', self.partner_ids.ids)]
        if self.is_pay_detraction:
            domain += [('is_detraction', '=', True)]

        domain += self._date_maturity_domain()
        # proveedor
        if self.partner_type == 'supplier':
            domain += [('account_internal_type', 'in', ('payable', 'other')),
                       ('journal_id.type', '=', 'purchase')]
        else:
            # cliente
            domain += [('account_internal_type', 'in', ('receivable', 'other')),
                       ('journal_id.type', '=', 'sale')]
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

    def _return_this(self, select_all=True):
        context = dict(self._context, create=True)
        context.update({'select_all': select_all})
        return {
            'name': 'Carga de comprobantes varios',
            "type": "ir.actions.act_window",
            "res_model": "load.invoice.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            'context': context
        }

    def action_add_all(self):
        self.ensure_one()
        # self.select_all = False
        self.invoices_ids = [(6, 0, self.domain_invoice_ids.ids)]
        return self._return_this(select_all=False)

    def action_clear_invoices_ids(self):
        self.ensure_one()
        self.invoices_ids = [(6, 0, [])]
        # self.select_all = True
        return self._return_this(select_all=True)

    def action_load_invoices(self):
        data_lines = []
        for item in self.invoices_ids:
            data_lines.append((0, 0,
                               {
                                   'payment_multi_id': self.payment_multi_id.id,
                                   'move_line_id': item.id,
                                   'partner_id': item.partner_id.id,
                                   'invoice_date': item.move_id.invoice_date,
                                   'invoice_origin': item.move_id.invoice_origin,
                                   'invoice_user_id': item.move_id.invoice_user_id.id or False,
                                   'expiration_date': item.move_id.invoice_date_due,
                                   'amount': item.move_id.amount_total,
                                   'amount_residual': item.move_id.amount_residual,
                                   'amount_payable': item.move_id.amount_residual,
                               }))
        if data_lines:
            self.payment_multi_id.sudo().write({
                'line_ids': data_lines
            })

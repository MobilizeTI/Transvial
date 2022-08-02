# -*- coding: utf-8 -*-
import re
import base64
from pprint import pprint

from lxml import etree
from num2words import num2words

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_repr, float_round
from odoo.exceptions import UserError, ValidationError


class AMDetraction(models.Model):
    _name = 'account.move.detraction'
    _description = 'Líneas de detracción'
    _check_company_auto = True

    move_id = fields.Many2one('account.move', string='Order reference', required=True,
                              ondelete='cascade', index=True, copy=False)
    move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Move line',
        required=True,
        readonly=True, ondelete='cascade'
    )
    product_id = fields.Many2one('product.product', string='Producto', ondelete='restrict')

    currency_id = fields.Many2one('res.currency', related='move_id.currency_id', string='Moneda')
    company_id = fields.Many2one('res.company', related='move_id.company_id', string='Compañía')

    amount = fields.Monetary(string='Monto')
    percentage = fields.Float(string='Porcentaje')
    # comment = fields.Text(string='Comentario')
    option_detraction_id = fields.Many2one(
        'table.option.detraction',
        string='Bien o servicio',
        help="Número de catálogo 54 SUNAT, utilizado funcionalmente para documentar en el documento impreso en las "
             "facturas que necesitan tener el texto SPOT adecuado")


class AccountMove(models.Model):
    _inherit = 'account.move'

    #  --------- campos exclusivos para (Detracciones de facturas de proveedor) -- Inicio
    supplier_account_detraction = fields.Char(string='Cuenta del proveedor', required=False,
                                              help="# Número del cuenta del proveedor para detracciones.")
    supplier_nro_constancia = fields.Char(string='Nro constancia', required=False)

    payer_detraction_id = fields.Many2one('res.partner',
                                          string='Pagador de detracción',
                                          required=False)
    #  -- Fin

    detraction_move_id = fields.Many2one('account.move', string="Asiento de detracción")

    detraction_lines = fields.One2many('account.move.detraction', 'move_id',
                                       string='Lineas de detracción', readonly=False, copy=False)

    is_affect_detraction = fields.Boolean(string='Afecto a detracción',
                                          compute='_compute_is_affect_detraction', store=True,
                                          help='Para facturas de proveedor')
    reload_is_affect_detraction = fields.Boolean(string='reload_is_affect_detraction',
                                                 compute='_compute_reload_is_affect_detraction')

    amount_detraction = fields.Monetary(
        string='Total detracción',
        readonly=True)

    currency_pe_id = fields.Many2one('res.currency', default=lambda i: i.env.ref('base.PEN'))
    currency_symbol = fields.Char(related='currency_id.symbol',
                                  help="Currency sign, to be used when printing amounts.")

    amount_detraction_pen = fields.Monetary(
        string='Total detracción (soles)',
        readonly=True)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        """Validación del tipo de cambio para la fecha"""
        if self.currency_id and self.currency_id.symbol != 'S/':
            date = self.date
            if self.invoice_date:
                date = self.invoice_date
            if not date:
                date = fields.Date.context_today(self)
            self.currency_id.validate_rate(date)

    # payment_detraction_id = fields.Many2one(
    #     comodel_name='account.payment',
    #     string='Pagó detracción',
    #     readonly=True,
    #     help='Pago relacionado a la detracción'
    # )

    @api.depends('detraction_lines')
    def _compute_reload_is_affect_detraction(self):
        for record in self:
            record._compute_is_affect_detraction()
            record._l10n_pe_edi_get_spot()  # recalcula la detracción
            record.reload_is_affect_detraction = True

    @api.depends('invoice_line_ids')
    def _compute_is_affect_detraction(self):
        for record in self:
            max_percent = max(record.invoice_line_ids.mapped('product_id.l10n_pe_withhold_percentage'), default=0)
            record.is_affect_detraction = max_percent and record.amount_total > 700

            if record.is_affect_detraction and record.l10n_pe_edi_operation_type != '1001' \
                    and record.move_type == 'out_invoice':
                record.l10n_pe_edi_operation_type = '1001'
            elif not record.is_affect_detraction and record.l10n_pe_edi_operation_type and \
                    record.l10n_pe_edi_operation_type == '1001':
                record.l10n_pe_edi_operation_type = '0101'
            if not record.is_affect_detraction:
                record.detraction_lines = [(6, 0, [])]

    def load_lines_detraction(self):
        # context = dict(self._context, create=True)
        # context.update({'upd_lines_detraction': False})
        detraction_lines = []
        for line in self.invoice_line_ids.filtered_domain([('product_id.is_affect_detraction', '=', True)]):
            is_affect_detraction = line.product_id and line.price_total > 700
            if is_affect_detraction and line.product_id.id not in self.detraction_lines.mapped('product_id.id'):
                detraction_lines.append((
                    0, 0, {
                        'move_id': line.move_id.id,
                        'move_line_id': line.id,
                        'product_id': line.product_id.id,
                        'option_detraction_id': line.product_id.option_detraction_id.id,
                        'amount': line.product_id.amount_min_detraction,
                        'percentage': line.product_id.percentage_detraction,
                    }
                ))
        if detraction_lines:
            # Búsqueda de número de cuenta para detracciones
            supplier_account_detraction = self.partner_id.bank_ids.filtered_domain([('is_detraction', '=', True)])
            if supplier_account_detraction:
                supplier_account_detraction = supplier_account_detraction[0]
            self.sudo().update(dict(
                detraction_lines=detraction_lines,
                payer_detraction_id=self.env.company.partner_id.id,
                supplier_account_detraction=supplier_account_detraction.acc_number or ''
            ))
        # else:
        #     self.sudo().update(dict(detraction_lines=detraction_lines))

    @api.model
    def l10n_pe_edi_amount_to_text(self):
        return {
            'amount_to_text': self._l10n_pe_edi_amount_to_text(),
        }

    def _l10n_pe_edi_get_spot(self):
        # max_percent = max(self.invoice_line_ids.mapped('product_id.l10n_pe_withhold_percentage'), default=0)
        max_percent = max(self.detraction_lines.mapped('percentage'), default=0)
        if self.move_type == 'out_invoice':
            if not max_percent or self.amount_total_signed < 700 or \
                    not self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004']:
                return {}
            line_detraction_list = self.detraction_lines.sorted(lambda l: l.percentage, reverse=True)[0]
            line = line_detraction_list.move_line_id
            national_bank = self.env.ref('l10n_pe_edi.peruvian_national_bank', raise_if_not_found=False)
            national_bank_account_number = False
            if national_bank:
                national_bank_account = self.company_id.bank_ids.filtered(lambda b: b.bank_id == national_bank)
                if national_bank_account:
                    # just take the first one (but not meant to have multiple)
                    national_bank_account_number = national_bank_account[0].acc_number

            spot_amount = float_round(self.amount_total * (max_percent / 100.0), precision_rounding=2)
            self.amount_detraction = spot_amount
            # self.amount_detraction_pen = self.currency_id._convert(
            #     spot_amount,
            #     self.currency_pe_id,
            #     self.currency_id,
            #     self.date or fields.Date.today(),
            # )

            amount = float_repr(float_round(self.amount_total_signed * (max_percent / 100.0), precision_rounding=2),
                                precision_digits=2)
            self.amount_detraction_pen = amount

            return {
                'ID': 'Detraccion',
                'PaymentMeansID': line.product_id.l10n_pe_withhold_code,
                'PayeeFinancialAccount': national_bank_account_number,
                'PaymentMeansCode': '999',
                'spot_amount': spot_amount,
                'Amount': amount,
                'PaymentPercent': max_percent,
                'spot_message': "Operacion sujeta al sistema de Pago de Obligaciones Tributarias-SPOT, Banco de la Nacion"
                                " %% %s Cod Serv. %s" % (
                                    line_detraction_list.percentage,
                                    line.product_id.l10n_pe_withhold_code) if self.amount_total_signed >= 700.0 else False
            }
        elif self.move_type == 'in_invoice':
            # cálculo de la detracción para facturas de proveedor
            self.amount_detraction = 0
            self.amount_detraction_pen = 0
            if not max_percent or self.amount_total < 700:
                # or not self.l10n_pe_edi_operation_type in ['1001', '1002', '1003', '1004']
                return {}
            spot_amount = float_round(self.amount_total * (max_percent / 100.0), precision_rounding=2)
            self.amount_detraction = spot_amount
            self.amount_detraction_pen = self.currency_id._convert(
                spot_amount,
                self.currency_pe_id,
                self.currency_id,
                self.date or fields.Date.today(),
            )

    def create_entry_detraction(self):
        """Crear apuntes contables de detracción"""
        detraction_journal_id = self._valid_account_detraction()
        line_data = {
            'name': _('Detracción'),
            'ref': self.name,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'currency_id': self.currency_id and self.currency_id.id or False,
            'is_detraction': True,
        }

        debit_data = dict(line_data)
        credit_data = dict(line_data)
        # src_account_id = False

        if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
            debit_account_id = self.partner_id.property_account_payable_id.id
            credit_account_id = detraction_journal_id.default_detraction_account.id
            src_account_id = debit_account_id
        # if self.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
        else:
            debit_account_id = detraction_journal_id.default_detraction_account.id
            credit_account_id = self.partner_id.property_account_receivable_id.id
            src_account_id = credit_account_id
        debit_data.update(
            account_id=debit_account_id,
            debit=self.amount_detraction_pen,
            credit=False,
        )
        credit_data.update(
            account_id=credit_account_id,
            debit=False,
            credit=self.amount_detraction_pen,
        )

        # if self.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
        #     src_account_id = self.partner_id.property_account_payable_id.id
        #     line_ids = [
        #         (0, 0, {
        #             'name': _('Detracción'),
        #             'account_id': src_account_id,
        #             'currency_id': self.currency_id.id,
        #             'debit': self.amount_detraction_pen,
        #             'credit': 0.0,
        #             # 'exclude_from_invoice_tab': True,
        #             'is_detraction': True,
        #         }),
        #         (0, 0, {
        #             'name': _('Detracción'),
        #             'account_id': detraction_journal_id.default_detraction_account.id,
        #             'currency_id': self.currency_id.id,
        #             'debit': 0.0,
        #             'credit': self.amount_detraction_pen,
        #             # 'exclude_from_invoice_tab': True,
        #             'is_detraction': True,
        #         })
        #     ]
        # else:
        #     src_account_id = self.partner_id.property_account_receivable_id.id
        #     line_ids = [
        #         (0, 0, {
        #             'name': _('Detracción'),
        #             'account_id': src_account_id,
        #             'currency_id': self.currency_id.id,
        #             'debit': 0.0,
        #             'credit': self.amount_detraction_pen,
        #             # 'exclude_from_invoice_tab': True,
        #             'is_detraction': True,
        #         }),
        #         (0, 0, {
        #             'name': _('Detracción'),
        #             'account_id': detraction_journal_id.default_detraction_account.id,
        #             'currency_id': self.currency_id.id,
        #             'debit': self.amount_detraction_pen,
        #             'credit': 0.0,
        #             # 'exclude_from_invoice_tab': True,
        #             'is_detraction': True,
        #         })
        #     ]

        move_detraction = {'ref': 'Detracción ' + 'de ' + str(self.name),
                           'line_ids': [(0, 0, debit_data), (0, 0, credit_data)],
                           'journal_id': detraction_journal_id.id,
                           'date': self.date,
                           'state': 'draft',
                           'move_type': 'entry'
                           }
        detraction_move_id = self.env['account.move'].sudo().create(move_detraction)
        if detraction_move_id:
            self.detraction_move_id = detraction_move_id
            self.detraction_move_id.post()
            to_reconcile = self.line_ids.filtered_domain([
                ('account_id', '=', src_account_id), ('reconciled', '=', False)])
            payment_lines = detraction_move_id.line_ids.filtered_domain([
                ('account_id', '=', src_account_id), ('reconciled', '=', False)])

            results = (payment_lines + to_reconcile).reconcile()

    # def _clear_entries_detraction(self):
    #     line_detraction_ids = self.line_ids.filtered_domain([('is_detraction', '=', True)])
    #     line_detraction_ids.unlink()

    def _valid_account_detraction(self):
        # if not self.company_id.detraction_account_id:
        #     raise ValidationError(
        #         _(f'No existe la cuenta de detracción configurada para la compañía {self.company_id.name}'))

        detraction_journal_id = self.env['account.journal'].search(
            [('is_detraction_journal', '=', True), ('company_id', '=', self.company_id.id)], limit=1)
        if not detraction_journal_id:
            raise UserError(_(
                'No hay un diario de detracción.'
                'Por favor defina un diario tipo varios con la cuenta de detracción asociada para la compañía %s.') % (
                                self.company_id.name))

        if detraction_journal_id and not detraction_journal_id.default_detraction_account:
            raise ValidationError(
                _(f'No existe la cuenta de detracción configurada para la compañía {self.company_id.name}'))
        return detraction_journal_id

    # def action_post(self):
    #     # se añade el apunte contable de la detracción (solo a facturas de proveedor)
    #     resp = super(AccountMove, self).action_post()
    #     if self.move_type in ('in_invoice', 'out_invoice'):
    #         if self.is_affect_detraction:
    #             self.create_entry_detraction()
    #         else:
    #             self._clear_entries_detraction()
    #     return resp

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        for move in self:
            if move.is_affect_detraction:
                move.create_entry_detraction()
        return res

    @api.model
    def create(self, values):
        move_new = super(AccountMove, self).create(values)
        for record in self:
            if record.move_type in ('in_invoice', 'out_invoice'):
                move_new.load_lines_detraction()
        return move_new

    # @api.onchange('invoice_line_ids')
    # def _onchange_invoice_line_ids(self):
    #     # Add code here
    #     rep = super(AccountMove, self)._onchange_invoice_line_ids()
    #     if not self.is_affect_detraction:
    #         self._clear_entries_detraction()
    #         self.detraction_lines = [(6, 0, [])]
    #     return rep

    def write(self, values):
        # Add code here
        rep_write = super(AccountMove, self).write(values)
        for record in self:
            if record.move_type in ('in_invoice', 'out_invoice') and record.is_affect_detraction:
                record.load_lines_detraction()
        return rep_write

    # @api.returns('self', lambda value: value.id)
    # def copy(self, default=None):
    #     default = dict(default or {})
    #     if self.is_affect_detraction:
    #         ids = self.line_ids.filtered_domain([('is_detraction', '=', False)]).ids
    #         default['line_ids'] = [(6, 0, ids)]
    #         default['invoice_line_ids'] = [(6, 0, self.invoice_line_ids.ids)]
    #     copy_new = super().copy(default)
    #     print(len(copy_new.invoice_line_ids))
    #     return copy_new


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_detraction = fields.Boolean(string='Es detracción', readonly=True, copy=False)

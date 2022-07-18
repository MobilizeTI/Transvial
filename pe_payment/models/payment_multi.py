# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PaymentMulti(models.Model):
    _name = 'account.payment_multi'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pagos multiples'
    _order = "date desc, name desc"
    _check_company_auto = True

    name = fields.Char(string='SEQ', required=True, copy=False,
                       readonly=True,
                       index=True, default=lambda self: _('/'))

    date = fields.Date(
        string='Fecha',
        required=True,
        index=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        copy=False,
        default=fields.Date.context_today
    )

    company_id = fields.Many2one(comodel_name='res.company', string='Compañía',
                                 store=True, readonly=True,
                                 compute='_compute_company_id')

    @api.depends('journal_id')
    def _compute_company_id(self):
        for move in self:
            move.company_id = move.journal_id.company_id or move.company_id or self.env.company

    payment_type = fields.Selection([
        ('outbound', 'Enviar dinero'),
        ('inbound', 'Recibir dinero'),
    ], string='Tipo de pago', default='inbound', required=True)

    partner_type = fields.Selection([
        ('customer', 'Cliente'),
        ('supplier', 'Proveedor'),
    ], default='customer', tracking=True, required=True)

    expiration_date = fields.Date(string='Fecha de vencimiento', copy=False)

    state = fields.Selection(selection=[
        ('draft', 'Borrador'),
        ('confirm', 'Confirmado'),
        ('payment', 'Pagado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    def _get_default_journal(self):
        return self.env['account.move']._search_default_journal(('bank', 'cash'))

    payment_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Asiento contable', required=False, readonly=True, ondelete='cascade',
        check_company=True,
        help='Asiento contable para un pago de tipo de generación masiva'
    )

    partner_ids = fields.Many2many(
        comodel_name='res.partner',
        string="Clientes/Proveedores",
        store=True, readonly=False, ondelete='restrict', required=True,
        domain="['|', ('parent_id','=', False), ('is_company','=', True)]",
        check_company=True)
    user_id = fields.Many2one('res.users', string='Comercial', default=lambda self: self.env.user, required=True)
    generation_type = fields.Selection(string='Generación',
                                       selection=[('individual', 'Individual'),
                                                  ('massive', 'Masiva')],
                                       required=True, default='individual')

    journal_id = fields.Many2one('account.journal',
                                 string='Diario',
                                 required=True,
                                 readonly=False,
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]",
                                 check_company=True,
                                 default=_get_default_journal)

    # def _default_currency_id(self):
    #     currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id
    #     return currency_id

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id

    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, help="Moneda para pagos multiples")

    # @api.depends('journal_id')
    # def _compute_currency_id(self):
    #     for pay in self:
    #         pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

    # Lineas
    line_ids = fields.One2many(
        comodel_name='account.payment_multi.line',
        inverse_name='payment_multi_id',
        string='Facturas',
        required=False)

    #  ----------------- Cambios de estados -----------------
    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def _create_move_massive(self):
        line_ids = []
        for record in self.line_ids:
            labels = set([
                record.move_line_id.move_id.name or record.move_line_id.move_id.ref or record.move_line_id.move_id.name])
            name = ' '.join(sorted(labels))
            if self.partner_type == 'supplier':
                line_ids += [
                    (0, 0, {
                        'name': name,
                        'partner_id': record.partner_id.id,
                        'account_id': record.partner_id.property_account_payable_id.id,
                        'currency_id': record.currency_id.id,
                        'debit': record.amount_payable,
                        'credit': 0.0,
                        'exclude_from_invoice_tab': True,
                    }),
                    (0, 0, {
                        'name': name,
                        'partner_id': record.partner_id.id,
                        'account_id': self.journal_id.payment_credit_account_id.id,
                        'currency_id': self.currency_id.id,
                        'debit': 0.0,
                        'credit': record.amount_payable,
                        'exclude_from_invoice_tab': True,
                    })
                ]
            else:
                line_ids += [
                    (0, 0, {
                        'name': name,
                        'partner_id': record.partner_id.id,
                        'account_id': record.partner_id.property_account_receivable_id.id,
                        'currency_id': record.currency_id.id,
                        'debit': 0.0,
                        'credit': record.amount_payable,
                        'exclude_from_invoice_tab': True,
                    }),
                    (0, 0, {
                        'name': name,
                        'partner_id': record.partner_id.id,
                        'account_id': self.journal_id.payment_debit_account_id.id,
                        'currency_id': self.currency_id.id,
                        'debit': record.amount_payable,
                        'credit': 0.0,
                        'exclude_from_invoice_tab': True,
                    })
                ]

        move_vals = {
            'ref': f'PAGO MASIVO {self.name}',
            'date': fields.Date.context_today(self),
            'journal_id': self.journal_id.id,
            'line_ids': line_ids,
            'move_type': 'entry',
            'company_id': self.company_id.id,
        }

        move_entry_new = self.env['account.move'].sudo().create(move_vals)
        move_entry_new.action_post()
        self.payment_move_id = move_entry_new.id

    def action_confirm(self):
        self.ensure_one()
        if self.generation_type == 'individual':
            for record in self.line_ids:
                labels = set([
                    record.move_line_id.move_id.name or record.move_line_id.move_id.ref or record.move_line_id.move_id.name])
                ref = ' '.join(sorted(labels))
                vals_payment = {
                    'date': fields.Date.context_today(self),
                    'partner_id': record.move_line_id.partner_id.id,
                    'amount': record.amount_payable,
                    'payment_type': self.payment_type,
                    'partner_type': self.partner_type,
                    'journal_id': self.journal_id.id,
                    'payment_multi_id': self.id,
                    'ref': ref,
                    'company_id': self.company_id.id
                }
                new_payment = self.env['account.payment'].sudo().create(vals_payment)
                new_payment.action_post()
                record.payment_id = new_payment.id
                _logger.info(f'>>> new payment: {new_payment.name}')
        else:
            self._create_move_massive()
        self.state = 'confirm'

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'

    #  ----------------- Cambios de estados -----------------

    def action_load_invoices(self):
        self.ensure_one()
        action = self.env.ref('pe_payment.action_load_invoice_wizard').read()[0]
        context = dict(self._context, create=True)
        context.update({
            'default_payment_multi_id': self.id,
            'default_partner_ids': self.partner_ids.ids
        })
        action['context'] = context
        return action

    def clear_invoices(self):
        self.ensure_one()
        self.line_ids = [(6, False, [])]

    payment_count = fields.Integer('Cantidad de pagos', compute='compute_payment_counts')

    def compute_payment_counts(self):
        for record in self:
            record.payment_count = len(record.payment_ids)

    def action_view_payment(self):
        self.ensure_one()
        if self.partner_type == 'supplier':
            action = self.env.ref('account.action_account_payments_payable').sudo().read()[0]
        else:
            action = self.env.ref('account.action_account_payments').sudo().read()[0]
        action['domain'] = [('id', '=', self.payment_ids.ids)]
        if self.payment_ids:
            if len(self.payment_ids) == 1:
                temp_id = self.payment_ids[:1]
                res = self.env.ref('account.view_account_payment_form', False)
                form_view = [(res and res.id or False, 'form')]
                action['views'] = form_view
                action['res_id'] = temp_id.id
        else:
            action['views'] = action['views'][1:]
        return action

    @api.model
    def create(self, values):
        new_payment_multi = super(PaymentMulti, self).create(values)
        if new_payment_multi.name == '/':
            new_payment_multi.name = self.env['ir.sequence'].next_by_code(
                f'seq.payment_multi.{"in" if new_payment_multi.partner_type == "supplier" else "out"}') or _('/')

        return new_payment_multi

    # Pagos relacionados
    payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='payment_multi_id',
        string='Pagos',
        required=False, help='Pagos realizados para cuando la generación es individual', copy=False)

    # @api.model
    # def default_get(self, fields):
    #     res = super().default_get(fields)
    #     journal_id = None
    #     if 'journal_id' not in res and res.get('journal_id'):
    #         journal_id = self.env['account.journal'].search([('id', '=', res['journal_id'])], limit=1)
    #     if journal_id:
    #         res['currency_id'] = journal_id.currency_id.id or journal_id.company_id.currency_id.id
    #     return res


class PaymentMultiLines(models.Model):
    _name = 'account.payment_multi.line'
    _description = 'Pagos multiples'
    _order = "sequence desc"
    _check_company_auto = True

    payment_multi_id = fields.Many2one(comodel_name='account.payment_multi',
                                       string='Pago multiple', index=True, ondelete='cascade', required=True)
    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda', related='payment_multi_id.currency_id')

    company_id = fields.Many2one(comodel_name='res.company', string='Compañía', related='payment_multi_id.company_id')
    sequence = fields.Integer(default=10)
    move_line_id = fields.Many2one('account.move.line', string='Comprobante', index=True,
                                   domain=[('account_internal_type', 'in', ('receivable', 'payable'))], readonly=True)
    partner_id = fields.Many2one('res.partner', string='Empresa', ondelete='restrict', readonly=True)
    invoice_date = fields.Date(string='Fecha factura/Recibo', readonly=True)
    invoice_origin = fields.Char(string='Origen', readonly=True)
    invoice_user_id = fields.Many2one('res.users', string='Comercial', readonly=True)
    expiration_date = fields.Date(string='Fecha vencimiento', readonly=True)

    amount = fields.Monetary(string='Importe adeudado', help="Importe a pagar en la moneda de diario", readonly=True)
    amount_residual = fields.Monetary(string='Cantidad a pagar', readonly=True)
    amount_payable = fields.Monetary(string='Importe', help="Importe a pagar en la moneda de diario")
    payment_id = fields.Many2one("account.payment", 'Pago', readonly=True)

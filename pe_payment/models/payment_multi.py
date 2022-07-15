# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


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

    move_ids = fields.Many2many(
        comodel_name='account.move',
        string='Asientos contables', required=True, readonly=True, ondelete='cascade',
        check_company=True)

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

    currency_id = fields.Many2one('res.currency', string='Moneda', store=True,
                                  compute='_compute_currency_id',
                                  help="The payment's currency.")

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id

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

    def action_confirm(self):
        self.ensure_one()
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

    @api.model
    def create(self, values):
        new_payment_multi = super(PaymentMulti, self).create(values)
        if new_payment_multi.name == '/':
            new_payment_multi.name = self.env['ir.sequence'].next_by_code('seq.payment_multi.in') or _('/')

        return new_payment_multi

    # Pagos relacionados
    payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='payment_multi_id',
        string='Pagos',
        required=False, help='Pagos realizados para cuando la generación es individual')


class PaymentMultiLines(models.Model):
    _name = 'account.payment_multi.line'
    _description = 'Pagos multiples'
    _order = "sequence desc"
    _check_company_auto = True

    payment_multi_id = fields.Many2one(comodel_name='account.payment_multi',
                                       string='Pago multiple', index=True, ondelete='cascade', required=True)

    company_id = fields.Many2one(comodel_name='res.company', string='Compañía', related='payment_multi_id.company_id')
    sequence = fields.Integer(default=10)
    move_line_id = fields.Many2one('account.move.line', string='Comprobante', index=True,
                                   domain=[('account_internal_type', 'in', ('receivable', 'payable'))])

    currency_id = fields.Many2one(comodel_name='res.currency', string='Moneda', related='payment_multi_id.currency_id')
    invoice_date = fields.Date(string='Fecha emisión')
    expiration_date = fields.Date(string='Fecha vencimiento')
    # amount = fields.Monetary(string='Total')
    balance = fields.Monetary(string='Saldo real')

    amount = fields.Monetary(string='Importe ', help="Importe a pagar en la moneda de diario")
    balance_payable = fields.Monetary(string='Saldo a pagar', help="Importe a pagar en la moneda de diario")

    # date_constance = fields.Date(string="Fecha constancia")
    # consistency_number = fields.Char(string="N° constancia")

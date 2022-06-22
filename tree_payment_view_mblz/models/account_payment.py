# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _
from datetime import timedelta
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    invoice_ids = fields.Many2many('account.move', compute='_compute_invoice_ids', string='Facturas',)
    monto_factura_sin_impuestos = fields.Float(string='Valor Bruto', compute='_compute_invoice_ids',)
    monto_factura_con_impuestos = fields.Float(string='Valor Neto', compute='_compute_invoice_ids',)
    monto_iva = fields.Float(string='Rete IVA', compute='_compute_invoice_ids',)
    monto_reteica = fields.Float(string='Rete ICA', compute='_compute_invoice_ids',)
    monto_retefte = fields.Float(string='Rete Fuente', compute='_compute_invoice_ids',)
    monto_valor_iva = fields.Float(string='Valor Iva', compute='_compute_invoice_ids',)
    banco = fields.Char(string='Banco', related='partner_bank_id.bank_id.name', store=True,)
    nro_cuenta = fields.Char(string='Nro Cuenta', related='partner_bank_id.acc_number',)
    partner_nit = fields.Char(string='NIT', related="partner_id.vat")
    tipo_cuenta = fields.Selection(string='Tipo Cuenta Bancaria', related="partner_bank_id.tipo_cuenta", store=True,)
    
    @api.depends('move_id')
    def _compute_invoice_ids(self):
        for rec in self:
            rec.invoice_ids = invoice_ids = [move[2].move_id.id for move in rec.move_id._get_reconciled_invoices_partials()]
            # raise UserError(('valor_iva: %s %s') %(rec.invoice_ids.name,invoice_ids))
            facturas = self.env['account.move'].search([('id', 'in', invoice_ids)])
            rec.monto_factura_con_impuestos = sum(facturas.mapped('amount_total'))
            rec.monto_factura_sin_impuestos = sum(facturas.mapped('amount_untaxed'))
            lineas = facturas.mapped('invoice_line_ids.tax_ids')
            valor_iva = facturas.mapped('invoice_line_ids.tax_ids').filtered(lambda tax: tax.l10n_co_edi_type.code == '01').mapped('id')
            reteiva = facturas.mapped('invoice_line_ids.tax_ids').filtered(lambda tax: tax.l10n_co_edi_type.code == '05').mapped('id')
            retefte = facturas.mapped('invoice_line_ids.tax_ids').filtered(lambda tax: tax.l10n_co_edi_type.code == '06').mapped('id')
            reteica = facturas.mapped('invoice_line_ids.tax_ids').filtered(lambda tax: tax.l10n_co_edi_type.code == '07').mapped('id')
            rec.monto_iva = abs(sum(facturas.mapped('line_ids').filtered(lambda x: x.tax_line_id.id in reteiva).mapped('balance'))) if reteiva else 0.0
            rec.monto_reteica = abs(sum(facturas.mapped('line_ids').filtered(lambda x: x.tax_line_id.id in reteica).mapped('balance'))) if reteica else 0.0
            rec.monto_retefte = abs(sum(facturas.mapped('line_ids').filtered(lambda x: x.tax_line_id.id in retefte).mapped('balance'))) if retefte else 0.0
            rec.monto_valor_iva = abs(sum(facturas.mapped('line_ids').filtered(lambda x: x.tax_line_id.id in valor_iva).mapped('balance'))) if valor_iva else 0.0
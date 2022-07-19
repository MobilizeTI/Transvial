# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AML(models.Model):
    _inherit = "account.move.line"

    parent_payment_state = fields.Selection(related='move_id.payment_state', store=True, readonly=True)

    # Se utiliza para poder identificar a que pago pasivo debo aplicar el débito o el crédito según corresponda
    id_invoice_payment = fields.Float(string='ID comprobante de pago', required=False)

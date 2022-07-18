# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_multi_id = fields.Many2one(comodel_name='account.payment_multi',
                                       string='Pago multiple', index=True, ondelete='cascade', copy=False)

# coding: utf-8

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_detraction_journal = fields.Boolean(default=False)
    default_detraction_account = fields.Many2one(
        'account.account',
        string="Cuenta de detracción",
        company_dependent=True,
        domain=lambda self: [('deprecated', '=', False)],
        help="Cuenta que será utilizada para registrar la deuda de detracciones.")

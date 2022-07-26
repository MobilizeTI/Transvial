from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    detraction_account_id = fields.Many2one(
        'account.account',
        string="Cuenta de detracción",
        company_dependent=True,
        domain=lambda self: [('deprecated', '=', False)],
        help="Cuenta que será utilizada para registrar la deuda de detracciones.")

    currency_rates_autoupdate = fields.Boolean(
        string="Tipos de cambio automáticos",
        default=True,
        company_dependent=True,
        help="Activar la actualización automática de los tipos de cambio")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    detraction_account_id = fields.Many2one(
        'account.account', string='Cuenta de detracción',
        related='company_id.detraction_account_id', readonly=False,
        domain=lambda self: [('deprecated', '=', False)],
        help="Cuenta que será utilizada para registrar la deuda de detracciones.")

    currency_rates_autoupdate = fields.Boolean(
        string="Automatic Currency Rates",
        related="company_id.currency_rates_autoupdate",
        readonly=False,
        help="Enable regular automatic currency rates updates",
    )

# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _
from datetime import timedelta
from odoo.exceptions import UserError

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    tipo_cuenta = fields.Selection([('corriente', 'Corriente'), ('ahorro', 'Ahorro')])
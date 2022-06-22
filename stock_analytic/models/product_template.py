# Copyright (C) 2019 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    analytic_account_id = fields.Many2one(string="Analytic Account", comodel_name="account.analytic.account")
    analytic_tag_ids = fields.Many2many("account.analytic.tag", string="Analytic Tags")
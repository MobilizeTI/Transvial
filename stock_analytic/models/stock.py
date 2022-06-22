# Copyright 2013 Julius Network Solutions
# Copyright 2015 Clear Corp
# Copyright 2016 OpenSynergy Indonesia
# Copyright 2017 ForgeFlow S.L.
# Copyright 2018 Hibou Corp.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    analytic_account_id = fields.Many2one(
        string="Cuenta Analítica",
        comodel_name="account.analytic.account",
        related="product_id.analytic_account_id",
    )
    analytic_tag_ids = fields.Many2many(
        "account.analytic.tag", 
        string="Etiquetas Analíticas", 
        compute="_compute_analytic_tag_ids")

    @api.depends("product_id")
    def _compute_analytic_tag_ids(self):
        for rec in self:
            # if rec.picking_code == 'outgoing':
            rec.analytic_tag_ids= rec.product_id.analytic_tag_ids


    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, description):
        self.ensure_one()
        res = super(StockMove, self)._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, description
        )
        for line in res:
            if self.picking_code == 'outgoing':
                if (line[2]["account_id"] != self.product_id.categ_id.property_stock_valuation_account_id.id):
                    # Añadir cuenta analítica en la línea de débito
                    if self.analytic_account_id:
                        line[2].update({"analytic_account_id": self.analytic_account_id.id})
                    # Añadir etiquetas analíticas en la línea de débito
                    if self.analytic_tag_ids:
                        line[2].update(
                            {"analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)]}
                        )
        return res

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        fields = super()._prepare_merge_moves_distinct_fields()
        fields.append("analytic_account_id")
        return fields

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    analytic_account_id = fields.Many2one(related="move_id.analytic_account_id")

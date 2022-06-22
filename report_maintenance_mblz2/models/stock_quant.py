# -*- coding: utf-8 -*-

import logging

from psycopg2 import Error, OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def action_view_quants_mtto(self, parameters=False):
        # print(parameters)
        domain = []
        if parameters:
            if parameters['opc'] == 'dates':
                date_start, date_end = parameters['dates']
                domain += [('in_date', '>=', date_start), ('in_date', '<=', date_end)]
            elif parameters['opc'] == 'date':
                domain += [('in_date', '=', parameters['date'])]
        self = self.with_context(search_default_internal_loc=1)
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            company_user = self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                self = self.with_context(default_location_id=warehouse.lot_stock_id.id)

        # If user have rights to write on quant, we set quants in inventory mode.
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
        return self._get_quants_action2(domain=domain, extend=True)

    @api.model
    def _get_quants_action2(self, domain=None, extend=False):
        """ Returns an action to open quant view.
        Depending of the context (user have right to be inventory mode or not),
        the list view will be editable or readonly.

        :param domain: List for the domain, empty by default.
        :param extend: If True, enables form, graph and pivot views. False by default.
        """
        self._quant_tasks()
        ctx = dict(self.env.context or {})
        ctx.pop('group_by', None)
        action = {
            'name': _('Stock disponible'),
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': domain or [],
            'help': """
                    <p class="o_view_nocontent_empty_folder">Sin existencias disponibles</p>
                    <p>Este análisis le ofrece una visión general del stock actual
                    de sus productos.</p> <p>
                    """
        }

        target_action = self.env.ref('report_maintenance_mblz2.mblz_dashboard_open_quants', False)
        if target_action:
            action['id'] = target_action.id

        # if self._is_inventory_mode():
        #     action['view_id'] = self.env.ref('report_maintenance_mblz2.mblz_view_stock_quant_tree_editable').id
        #     form_view = self.env.ref('report_maintenance_mblz2.mblz_view_stock_quant_form_editable').id
        # else:
        action['view_id'] = self.env.ref('report_maintenance_mblz2.mblz_view_stock_quant_tree').id
        form_view = self.env.ref('report_maintenance_mblz2.mblz_view_stock_quant_form').id
        action.update({
            'views': [
                (action['view_id'], 'list'),
                (form_view, 'form'),
            ],
        })
        if extend:
            action.update({
                'view_mode': 'tree,form,pivot,graph',
                'views': [
                    (action['view_id'], 'list'),
                    (form_view, 'form'),
                    (self.env.ref('report_maintenance_mblz2.mblz_view_stock_quant_pivot').id, 'pivot'),
                    (self.env.ref('report_maintenance_mblz2.mblz_stock_quant_view_graph').id, 'graph'),
                ],
            })
        return action

    product_name = fields.Char(string='Producto', related='product_id.name')
    product_code = fields.Char(string='Código', related='product_id.default_code')

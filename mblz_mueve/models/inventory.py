import base64
import difflib
import io
import json

from xlsxwriter import Workbook

from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools import float_compare, float_is_zero, float_repr

from odoo.tools.misc import OrderedSet

from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    value = fields.Monetary('Value', compute='_compute_value',
                            groups='stock.group_stock_manager,mblz_mueve.mueve_group_stock_analista_inventario')
    currency_id = fields.Many2one('res.currency', compute='_compute_value',
                                  groups='stock.group_stock_manager,mblz_mueve.mueve_group_stock_analista_inventario')

    inventory_quantity = fields.Float(
        'Inventoried Quantity', compute='_compute_inventory_quantity',
        inverse='_set_inventory_quantity',
        groups='stock.group_stock_manager,mblz_mueve.mueve_group_stock_analista_inventario')

    @api.model
    def action_view_quants(self):
        self = self.with_context(search_default_internal_loc=1)
        if not self.user_has_groups('stock.group_stock_multi_locations'):
            company_user = self.env.company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                self = self.with_context(default_location_id=warehouse.lot_stock_id.id)

        # If user have rights to write on quant, we set quants in inventory mode.
        if self.user_has_groups('stock.group_stock_manager') or self.user_has_groups(
                'mblz_mueve.mueve_group_stock_analista_inventario'):
            self = self.with_context(inventory_mode=True)
        return self._get_quants_action(extend=True)

    @api.model
    def _is_inventory_mode(self):
        """ Used to control whether a quant was written on or created during an
        "inventory session", meaning a mode where we need to create the stock.move
        record necessary to be consistent with the `inventory_quantity` field.
        """
        return self.env.context.get('inventory_mode') is True and (
                self.user_has_groups('stock.group_stock_manager') or self.user_has_groups(
            'mblz_mueve.mueve_group_stock_analista_inventario'))


class Product(models.Model):
    _inherit = "product.product"

    # Be aware that the exact same function exists in product.template
    def action_open_quants(self):
        domain = [('product_id', 'in', self.ids)]
        hide_location = not self.user_has_groups('stock.group_stock_multi_locations')
        hide_lot = all(product.tracking == 'none' for product in self)
        self = self.with_context(
            hide_location=hide_location, hide_lot=hide_lot,
            no_at_date=True, search_default_on_hand=True,
        )

        # If user have rights to write on quant, we define the view as editable.
        if self.user_has_groups('stock.group_stock_manager') or self.user_has_groups(
                'mblz_mueve.mueve_group_stock_analista_inventario'):
            self = self.with_context(inventory_mode=True)
            # Set default location id if multilocations is inactive
            if not self.user_has_groups('stock.group_stock_multi_locations'):
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    self = self.with_context(default_location_id=warehouse.lot_stock_id.id)
        # Set default product id if quants concern only one product
        if len(self) == 1:
            self = self.with_context(
                default_product_id=self.id,
                single_product=True
            )
        else:
            self = self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = self.env['stock.quant']._get_quants_action(domain)
        action["name"] = _('Update Quantity')
        return action


class Inventory(models.Model):
    _inherit = "stock.inventory"

    def action_validate(self):
        if not self.exists():
            return
        self.ensure_one()
        if not self.user_has_groups('stock.group_stock_manager') and not self.user_has_groups(
                'mblz_mueve.mueve_group_stock_analista_inventario'):
            raise UserError(_("Only a stock manager can validate an inventory adjustment."))
        if self.state != 'confirm':
            raise UserError(_(
                "You can't validate the inventory '%s', maybe this inventory "
                "has been already validated or isn't ready.", self.name))
        inventory_lines = self.line_ids.filtered(lambda l: l.product_id.tracking in ['lot',
                                                                                     'serial'] and not l.prod_lot_id and l.theoretical_qty != l.product_qty)
        lines = self.line_ids.filtered(lambda l: float_compare(l.product_qty, 1,
                                                               precision_rounding=l.product_uom_id.rounding) > 0 and l.product_id.tracking == 'serial' and l.prod_lot_id)
        if inventory_lines and not lines:
            wiz_lines = [(0, 0, {'product_id': product.id, 'tracking': product.tracking}) for product in
                         inventory_lines.mapped('product_id')]
            wiz = self.env['stock.track.confirmation'].create({'inventory_id': self.id, 'tracking_line_ids': wiz_lines})
            return {
                'name': _('Tracked Products in Inventory Adjustment'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'res_model': 'stock.track.confirmation',
                'target': 'new',
                'res_id': wiz.id,
            }
        self._action_done()
        self.line_ids._check_company()
        self._check_company()
        return True


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    def action_lot_open_quants(self):
        self = self.with_context(search_default_lot_id=self.id, create=False)
        if self.user_has_groups('stock.group_stock_manager') or self.user_has_groups(
                'mblz_mueve.mueve_group_stock_analista_inventario'):
            self = self.with_context(inventory_mode=True)
        return self.env['stock.quant']._get_quants_action()


class Warehouse(models.Model):
    _inherit = "stock.warehouse"

    def _update_name_and_code(self, new_name=False, new_code=False):
        if new_code:
            self.mapped('lot_stock_id').mapped('location_id').write({'name': new_code})
        if new_name:
            # TDE FIXME: replacing the route name ? not better to re-generate the route naming ?
            for warehouse in self:
                routes = warehouse.route_ids
                for route in routes:
                    route.write({'name': route.name.replace(warehouse.name, new_name, 1)})
                    for pull in route.rule_ids:
                        pull.write({'name': pull.name.replace(warehouse.name, new_name, 1)})
                if warehouse.mto_pull_id:
                    warehouse.mto_pull_id.write(
                        {'name': warehouse.mto_pull_id.name.replace(warehouse.name, new_name, 1)})
        for warehouse in self:
            sequence_data = warehouse._get_sequence_values()
            # `ir.sequence` write access is limited to system user
            if self.user_has_groups('stock.group_stock_manager') or self.user_has_groups(
                    'mblz_mueve.mueve_group_stock_analista_inventario'):
                warehouse = warehouse.sudo()
            warehouse.in_type_id.sequence_id.write(sequence_data['in_type_id'])
            warehouse.out_type_id.sequence_id.write(sequence_data['out_type_id'])
            warehouse.pack_type_id.sequence_id.write(sequence_data['pack_type_id'])
            warehouse.pick_type_id.sequence_id.write(sequence_data['pick_type_id'])
            warehouse.int_type_id.sequence_id.write(sequence_data['int_type_id'])


class ReplenishmentReport(models.AbstractModel):
    _inherit = 'report.stock.report_product_product_replenishment'

    def _compute_draft_quantity_count(self, product_template_ids, product_variant_ids, wh_location_ids):
        """ Overrides to computes the valuations of the stock. """
        res = super()._compute_draft_quantity_count(product_template_ids, product_variant_ids, wh_location_ids)
        if not self.user_has_groups('stock.group_stock_manager') or not self.user_has_groups(
                'mblz_mueve.mueve_group_stock_analista_inventario'):
            return res
        domain = self._product_domain(product_template_ids, product_variant_ids)
        company = self.env['stock.location'].browse(wh_location_ids).mapped('company_id')
        svl = self.env['stock.valuation.layer'].search(domain + [('company_id', '=', company.id)])
        currency = svl.currency_id or self.env.company.currency_id
        total_quantity = sum(svl.mapped('quantity'))
        # Because we can have negative quantities, `total_quantity` may be equal to zero even if the warehouse's `quantity` is positive.
        if svl and not float_is_zero(total_quantity, precision_rounding=svl.product_id.uom_id.rounding):
            def filter_on_locations(layer):
                return layer.stock_move_id.location_dest_id.id in wh_location_ids or layer.stock_move_id.location_id.id in wh_location_ids

            quantity = sum(svl.filtered(filter_on_locations).mapped('quantity'))
            value = sum(svl.mapped('value')) * (quantity / total_quantity)
        else:
            value = 0
        value = float_repr(value, precision_digits=currency.decimal_places)
        if currency.position == 'after':
            value = '%s %s' % (value, currency.symbol)
        else:
            value = '%s %s' % (currency.symbol, value)
        res['value'] = value
        return res

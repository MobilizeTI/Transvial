from odoo import models, fields
from odoo import api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_name = fields.Char(string='Producto', related='product_id.name')
    product_code = fields.Char(string='Código', related='product_id.default_code')
    pro_partner_id = fields.Many2one('res.partner', string='Proveedor', related='order_id.partner_id')
    # date_planned = fields.Datetime(string='Fecha de recepción', related='order_id.date_planned')
    # delivery_state = fields.Char(compute='compute_delivery_state', store=True, string='Estado de entrega')
    delivery_state = fields.Selection(
        string='Estado de entrega',
        selection=[('not delivered', 'No entregado'),
                   ('delivered', 'Entregado'),
                   ('over delivered', 'Entregado en exceso')], compute='compute_delivery_state', store=True)

    @api.depends('product_qty', 'qty_received')
    def compute_delivery_state(self):
        for purcase_order_line_id in self:
            if purcase_order_line_id.product_qty > purcase_order_line_id.qty_received:
                purcase_order_line_id.delivery_state = 'not delivered'
            if purcase_order_line_id.product_qty == purcase_order_line_id.qty_received:
                purcase_order_line_id.delivery_state = 'delivered'
            if purcase_order_line_id.product_qty < purcase_order_line_id.qty_received:
                purcase_order_line_id.delivery_state = 'over delivered'

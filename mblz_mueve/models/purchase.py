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


class PO(models.Model):
    _inherit = 'purchase.order'

    readonly_po = fields.Boolean(
        string='Solo lectura',
        compute='_compute_readonly_po')

    @api.depends('picking_ids')
    def _compute_readonly_po(self):
        for record in self:
            if record.picking_ids:
                record.readonly_po = all([state in ('done', 'cancel') for state in record.picking_ids.mapped('state')])
            else:
                record.readonly_po = False

    def write(self, values):
        # Add code here
        if self.readonly_po:
            raise ValidationError('¡No se puede modificar una orden compra después de haber hecho la recepción!')
        return super(PO, self).write(values)

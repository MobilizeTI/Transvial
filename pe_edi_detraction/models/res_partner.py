# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner.bank'

    is_detraction = fields.Boolean(
        string='Para detracción',
        required=False, help='Cuenta de banco para detracción de proveedor')
    

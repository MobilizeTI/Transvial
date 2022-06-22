# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PT(models.Model):
    _inherit = 'product.template'

    me_category_ids = fields.Many2many('maintenance.equipment.category',
                                       string='Tipologias')


class SQ(models.Model):
    _inherit = 'stock.quant'

    me_category_ids = fields.Many2many('maintenance.equipment.category',
                                       related='product_id.me_category_ids',
                                       string='Tipologias')

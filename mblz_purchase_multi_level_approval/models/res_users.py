# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import models, fields, api, _


class ResUsers(models.Model):
    _inherit = 'res.users'

    flag_approve_po = fields.Boolean(string='Permitir confirmar la compra', required=False)

    @api.model
    def default_get(self, field_list):
        res = super(ResUsers, self).default_get(field_list)
        if 'field_ids' in res:
            field_ids = res['field_ids'][0][2]
            ids = self.env['ir.model.fields'].search([
                ('model', 'in', ('res.users', 'res.partner')),
                ('name', '=', 'flag_approve_po'),
            ]).ids
            res.update({
                'field_ids': [(6, 0, field_ids + ids)]
            })
        return res

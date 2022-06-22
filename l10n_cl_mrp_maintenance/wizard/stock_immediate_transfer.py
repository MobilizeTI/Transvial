# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    def process(self):
        # Add code here
        resp = super(StockImmediateTransfer, self).process()
        print(f'pick_ids: {self.pick_ids}')
        return resp

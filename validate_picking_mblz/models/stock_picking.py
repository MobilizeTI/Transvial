# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class Picking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        for record in self:
            qty_done_two = 0
            lista = []
            for move in record.move_ids_without_package:
                qty_done = sum(record.move_line_nosuggest_ids.filtered(lambda l: l.move_id.id==move.id).mapped('qty_done'))
                qty_done_two = move.quantity_done if move.quantity_done else 0
                
                if qty_done > move.product_uom_qty:
                    lista.append(move.product_id.name)
                
                elif qty_done_two > move.product_uom_qty:
                    lista.append(move.product_id.name)
            
            if len(lista) > 0:
                raise UserError("Los productos en rojo superan la cantidad de demanda")

        # raise UserError(_(("No entro")))
        return super(Picking, self).button_validate()

# class StockMove(models.Model):
#     _inherit = "stock.move"
    
#     def write(self, vals):
        
#         res = super(StockMove, self).write(vals)
#         for rec in self:
#             if rec.quantity_done > rec.product_uom_qty:
#                 raise UserError("La cantidad hecha no puede ser superior a la cantidad de demanda")
#             if rec.quantity_done > rec.reserved_availability:
#                 raise UserError("La cantidad hecha no puede ser superior a la cantidad de demanda")

#         return res
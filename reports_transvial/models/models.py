# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class reports_transvial(models.Model):
#     _name = 'reports_transvial.reports_transvial'
#     _description = 'reports_transvial.reports_transvial'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

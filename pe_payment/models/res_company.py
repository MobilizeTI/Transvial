# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    def _create_seq_payment_multi(self):
        seq_supplier_invoice_vals = []
        for company in self:
            seq_supplier_invoice_vals.append({
                'name': 'Correlativo pagos masivos proveedores',
                'code': 'seq.payment_multi.in',
                'company_id': company.id,
                'prefix': 'MP/IN/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })

            seq_supplier_invoice_vals.append({
                'name': 'Correlativo pagos masivos clientes',
                'code': 'seq.payment_multi.out',
                'company_id': company.id,
                'prefix': 'MP/OUT/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1
            })
        if seq_supplier_invoice_vals:
            self.env['ir.sequence'].sudo().create(seq_supplier_invoice_vals)

    @api.model
    def create_payment_multi(self):
        company_ids = self.env['res.company'].search([])
        company_has_supplier_invoice_seq = self.env['ir.sequence'].sudo().search(
            [('code', 'in', ('seq.payment_multi.in', 'seq.payment_multi.out'))]).mapped('company_id')
        company_todo_sequence = company_ids - company_has_supplier_invoice_seq
        company_todo_sequence._create_seq_payment_multi()

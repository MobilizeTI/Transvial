from odoo import api, SUPERUSER_ID


def clear_seq_supplier_invoice_hook(cr, registry):
    """Si se desinstala se limpia las secuencias de sistema para facturas de proveedor"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.sequence'].sudo().search([('code', '=', 'seq.supplier.invoice')]).unlink()

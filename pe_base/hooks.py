from odoo import api, SUPERUSER_ID


def clear_seq_customer_supplier_invoice_hook(cr, registry):
    """Si se desinstala se limpia las secuencias de sistema para facturas de cliente y proveedor"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.sequence'].sudo().search([('code', 'in', ('seq.customer.invoice', 'seq.supplier.invoice'))]).unlink()

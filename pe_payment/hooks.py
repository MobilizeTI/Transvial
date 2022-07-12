from odoo import api, SUPERUSER_ID


def clear_seq_payment_multi_hook(cr, registry):
    """Si se desinstala se limpia las secuencias para pagos multiples"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.sequence'].sudo().search([('code', 'in', ('seq.payment_multi.in', 'seq.payment_multi.out'))]).unlink()

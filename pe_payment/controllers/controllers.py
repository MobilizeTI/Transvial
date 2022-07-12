# -*- coding: utf-8 -*-
# from odoo import http


# class PePayment(http.Controller):
#     @http.route('/pe_payment/pe_payment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pe_payment/pe_payment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pe_payment.listing', {
#             'root': '/pe_payment/pe_payment',
#             'objects': http.request.env['pe_payment.pe_payment'].search([]),
#         })

#     @http.route('/pe_payment/pe_payment/objects/<model("pe_payment.pe_payment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pe_payment.object', {
#             'object': obj
#         })

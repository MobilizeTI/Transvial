# -*- coding: utf-8 -*-
# from odoo import http


# class PeEdiDetraction(http.Controller):
#     @http.route('/pe_edi_detraction/pe_edi_detraction/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pe_edi_detraction/pe_edi_detraction/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pe_edi_detraction.listing', {
#             'root': '/pe_edi_detraction/pe_edi_detraction',
#             'objects': http.request.env['pe_edi_detraction.pe_edi_detraction'].search([]),
#         })

#     @http.route('/pe_edi_detraction/pe_edi_detraction/objects/<model("pe_edi_detraction.pe_edi_detraction"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pe_edi_detraction.object', {
#             'object': obj
#         })

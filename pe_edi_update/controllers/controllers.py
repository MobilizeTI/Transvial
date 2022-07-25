# -*- coding: utf-8 -*-
# from odoo import http


# class PeBase(http.Controller):
#     @http.route('/pe_base/pe_base/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pe_base/pe_base/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pe_base.listing', {
#             'root': '/pe_base/pe_base',
#             'objects': http.request.env['pe_base.pe_base'].search([]),
#         })

#     @http.route('/pe_base/pe_base/objects/<model("pe_base.pe_base"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pe_base.object', {
#             'object': obj
#         })

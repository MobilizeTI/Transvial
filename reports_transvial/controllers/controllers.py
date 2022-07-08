# -*- coding: utf-8 -*-
# from odoo import http


# class ReportsTransvial(http.Controller):
#     @http.route('/reports_transvial/reports_transvial/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/reports_transvial/reports_transvial/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('reports_transvial.listing', {
#             'root': '/reports_transvial/reports_transvial',
#             'objects': http.request.env['reports_transvial.reports_transvial'].search([]),
#         })

#     @http.route('/reports_transvial/reports_transvial/objects/<model("reports_transvial.reports_transvial"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('reports_transvial.object', {
#             'object': obj
#         })

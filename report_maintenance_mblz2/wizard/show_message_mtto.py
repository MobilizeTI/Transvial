# coding=utf-8
from odoo import fields, api, models, _


class ShowMessageMtto(models.TransientModel):
    _name = 'show.message.mtto'
    _description = "Asistente para mostrar KPI - cálculados pos generación del reporte"

    message = fields.Html(string='Message', required=True)

    # def action_view_rpt(self):
    #     ws = self.env['mtto.report.wz'].search([], order='create_date desc', limit=1)
    #     return ws.action_view_screen()

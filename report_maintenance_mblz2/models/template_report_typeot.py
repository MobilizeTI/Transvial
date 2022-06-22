# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError, ValidationError

from dateutil.relativedelta import relativedelta


class TemplateReportTypeOT(models.Model):
    _name = "template.report.typeot"
    _description = "Plantilla para reportes que dependan de tipos de OT's"

    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean('Active', default=True)
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user)
    mt_stage_ids = fields.Many2many(
        comodel_name='maintenance.stage',
        string="Etapas de OT's", required=False)

    type_ot_ids = fields.One2many('template.report.typeot.line',
                                  'report_temp_id', string='Tipos', required=False)

    all_stages = fields.Boolean(string='Todos los estados', required=False)
    all_types = fields.Boolean(string="Todos los tipos de Ot's", required=False)
    rpt_type_id = fields.Many2one('report.mtto.type', string='Reporte', required=True)
    code_rpt_type = fields.Char(string='Code', related='rpt_type_id.code')

class TemplateReportTypeOTLine(models.Model):
    _name = "template.report.typeot.line"
    _description = "Lineas de reportes"

    report_temp_id = fields.Many2one(
        'template.report.typeot',
        string='Temp', ondelete='cascade',
        required=True)

    sequence = fields.Integer(required=True, default=10)
    type_ot = fields.Many2one('maintenance.request.type', string='Tipo de OT', required=True)
    type_of_fault = fields.Selection(string=' Tipo de falla', related='type_ot.type_of_fault')

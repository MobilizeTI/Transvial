# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
from pprint import pprint

from odoo import fields, models, api, _, tools
import subprocess
import sys


def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


try:
    import numpy as np
except:
    install('numpy')

import numpy as np

import datetime as dt
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from datetime import timedelta
from odoo.exceptions import Warning


class ProductividadMantenimiento(models.Model):
    _name = 'productividad.mantenimiento'
    _description = '1-32 y 1-33'
    _auto = False

    maintenance_id = fields.Many2one('maintenance.request', string='Referencia OT', readonly=True)
    name_seq = fields.Char(string='Numero de OT', readonly=True)
    type_ot = fields.Many2one('maintenance.request.type', string='Tipo OT', readonly=True)
    activity_id = fields.Many2one('maintenance.request.task', string='Actividad', readonly=True)
    name = fields.Char(string='Nombre de la tarea', readonly=True)

    # activity_speciality_ids = fields.Many2one('maintenance.request.task', string='', readonly = True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=False)
    duration = fields.Float(string='Horas Programadas')
    unit_amount = fields.Float(string='Horas Efectivas', readonly=False)

    percentage_e_p = fields.Float(string='Hs E/P(%)')
    percentage_p_l = fields.Float(string='Hs P/L(%)')
    percentage_e_l = fields.Float(string='Hs E/L(%)')

    resource_calendar_id = fields.Float(string='Horas Laborales', readonly=True)

    analytic_line_ids = fields.Many2one('account.analytic.line', readonly=True, string='Cuenta analítica')
    prom_hrs_efectivas = fields.Float(compute='_promedio_horas_efectivas', string='Promedio de hrs efectivas')
    duracion = fields.Boolean(string='Duración', readonly=True)
    company_id = fields.Many2one('res.company', string='Unidad de Negocio', readonly=True)
    request_date = fields.Date(string='Fecha solicitud', readonly=True, )

    @api.depends('analytic_line_ids')
    def _promedio_horas_efectivas(self):
        for record in self:
            suma = 0
            num_task = 1
            if record.analytic_line_ids:
                for x in record.analytic_line_ids:
                    suma = sum(line.unit_amount for line in
                               record.analytic_line_ids.filtered(
                                   lambda x: x.task_request_id.id == record.activity_id.id))
                    num_task = len(record.analytic_line_ids)
            record.prom_hrs_efectivas = suma / num_task

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     res = super(ProductividadMantenimiento, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
    #                                                              orderby=orderby, lazy=lazy)
    #     for group in res:
    #         if group.get('__domain'):
    #             records = self.search(group['__domain'])
    #             group['resource_calendar_id'] = sum(records.mapped('resource_calendar_id')) / (
    #                 len(records) if records else 1)
    #     return res

    def get_query(self, dates=False, date=False):
        nro_dias_lab = 1
        if dates:
            date_start, date_end = dates
            nro_dias_lab = np.busday_count(date_start, date_end)

        sql = f"""
        SELECT row_number() OVER() as id,
            mr.id AS maintenance_id, 
            mr.name_seq, 
            mr.type_ot, 
            mrt.id AS activity_id, 
            mrt.name,
            aat.employee_id,
            mrt.planned_hours AS duration, 
            aat.unit_amount,
            (rc.hours_per_day*{nro_dias_lab}) AS resource_calendar_id, 
            aat.id AS analytic_line_ids,
            (aat.unit_amount / NULLIF(mrt.planned_hours, 0)) AS percentage_e_p,
            (mrt.planned_hours / NULLIF((rc.hours_per_day * 1), 0)) AS percentage_p_l,
            (aat.unit_amount / NULLIF((rc.hours_per_day * 1), 0)) AS percentage_e_l,
            (CASE WHEN mrt.employee_id = aat.employee_id THEN True ELSE False END) duracion,
            mr.company_id,
            mr.request_date 
        FROM maintenance_request AS mr
            INNER JOIN maintenance_request_task AS mrt ON mrt.request_id=mr.id
            INNER JOIN hr_employee AS he ON he.id=mrt.employee_id
            INNER JOIN resource_calendar AS rc ON rc.id=he.resource_calendar_id
            INNER JOIN account_analytic_line AS aat ON aat.task_request_id=mrt.id
            -- WHERE mrt.id = 39281 
            """
        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "WHERE mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "WHERE mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        query = f"create or replace view productividad_mantenimiento as ({sql})"
        # pprint(query)
        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'productividad_mantenimiento')
        query = self.get_query()
        self._cr.execute(query)

    def get_act_window(self, data):
        if data['opc'] == 'dates':
            query = self.get_query(dates=data['dates'])
        elif data['opc'] == 'date':
            query = self.get_query(date=data['date'])
        else:
            query = self.get_query()
        self.env.cr.execute(query)
        if self.search_count([]) == 0:
            raise Warning('!No existe datos, para el filtro ingresado!')
        view_tree = self.env.ref('report_maintenance_mblz2.productividad_mantenimiento_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.productividad_mantenimiento_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.productividad_mantenimiento_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.productividad_mantenimiento_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'productividad.mantenimiento',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_graph.id, 'graph'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
                "search_default_preventivos": "preventive",
                "search_default_group_employee": True,

            }
        }

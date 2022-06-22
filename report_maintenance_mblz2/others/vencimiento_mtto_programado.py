# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _, tools
from datetime import timedelta
from odoo.exceptions import Warning


class FechasDeVencimientoDeMtto(models.Model):
    _name = 'fechas.de.vencimiento.de.mtto'
    _description = '1-12- Reporte - Fechas de vencimiento de Mtto preventivo y programado'
    _auto = False

    maintenance_id = fields.Many2one('maintenance.request', string='Referencia OT', readonly=True, )
    name_seq = fields.Char(string='Numero de OT', readonly=True, )
    model_id = fields.Many2one('fleet.vehicle.model', string='Modelo', readonly=True, )
    maintenance_type = fields.Char(string='Tipo mantenimiento', readonly=True, )
    category_id = fields.Many2one('maintenance.equipment.category', string='Tipología', readonly=True, )
    odometer_actual = fields.Float(string='Kilometraje', readonly=True, )
    stage_id = fields.Many2one('maintenance.stage', string='Estado', readonly=True, )
    schedule_date = fields.Date(string='Fecha Prevista', readonly=True, )

    request_date = fields.Date(string='Fecha solicitud', readonly=True, )
    company_id = fields.Many2one('res.company', string='Unidad de negocio', readonly=True)

    estado = fields.Char(string='Estado', readonly=True, )
    next_odometer = fields.Float(string='Km Próximo a Vencer', readonly=True, )
    preventivos = fields.Char(string='Preventivos', readonly=True, )
    correctivos = fields.Char(string='Correctivos', readonly=True, )
    maintenance_type_view = fields.Char(string='Tipo mantenimiento', readonly=True, )

    def get_query(self, dates=False, date=False):
        sql = """
            SELECT row_number() OVER() as id, 
                mr.id AS maintenance_id, 
                mr.name_seq, 
                mr.stage_id,
                mr.type_ot, 
                mrt.maintenance_type, 
                TO_DATE(TO_CHAR(mr.schedule_date, 'yyyy-mm-dd'), 'yyyy-mm-dd') AS schedule_date, 
                mr.request_date, 
                mr.company_id, 
                me.id AS equipment_id, me.category_id, 
                fv.model_id, T1.next_odometer, 
                (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<=mr.request_date ORDER BY fvo.date DESC LIMIT 1) AS odometer_actual, 
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='preventive') AS preventivos, 
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='corrective') AS correctivos, 
                (CASE mrt.maintenance_type 
                    WHEN 'preventive' THEN 'Preventivo' 
                    WHEN 'corrective' THEN 'Correctivo' 
                END) AS maintenance_type_view, 
                (CASE WHEN mr.schedule_date<now() THEN 'Vencida' ELSE 'Pendiente' END) AS estado 
                FROM maintenance_request AS mr 
                INNER JOIN maintenance_equipment AS me ON me.id=mr.equipment_id 
                INNER JOIN fleet_vehicle AS fv ON fv.id = me.vehicle_id 
                INNER JOIN maintenance_request_type AS mrt ON mrt.id=mr.type_ot 
                INNER JOIN 
                (SELECT date_log, next_odometer, equipment_id FROM equipment_odometer_log AS eoll 
                INNER JOIN maintenance_guideline AS mg ON mg.id=eoll.guideline_id 
                WHERE mg.measurement = 'frequently' ORDER BY eoll.id DESC LIMIT 1) AS T1 ON T1.equipment_id=me.id 
            """
        sql_where = "WHERE mr.equipment_id IS NOT NULL AND mr.stage_id IN (1, 2) "
        if dates:
            date_start, date_end = dates
            sql_where += "AND mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "AND mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        query = f"create or replace view fechas_de_vencimiento_de_mtto as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'fechas_de_vencimiento_de_mtto')
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
        view_tree = self.env.ref('report_maintenance_mblz2.fechas_de_vencimiento_de_mtto_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.fechas_de_vencimiento_de_mtto_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.fechas_de_vencimiento_de_mtto_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.fechas_de_vencimiento_de_mtto_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'fechas.de.vencimiento.de.mtto',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_graph.id, 'graph'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
                "search_default_preventivos": "preventive"
            }
        }

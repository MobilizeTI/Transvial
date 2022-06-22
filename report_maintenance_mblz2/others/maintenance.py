# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _, tools
from datetime import timedelta
from odoo.exceptions import Warning


class MaintenanceRequestDetails(models.Model):
    _name = 'maintenance.request.details'
    _description = '1-25'
    _auto = False

    maintenance_id = fields.Many2one('maintenance.request', string='Referencia OT', readonly=True, )
    name_seq = fields.Char(string='Numero de OT', readonly=True, )
    stage_id = fields.Many2one('maintenance.stage', string='Estado', readonly=True, )
    maintenance_type = fields.Char(string='Tipo mantenimiento', readonly=True, )
    schedule_date = fields.Date(string='Fecha planificación', readonly=True, )
    execution_date = fields.Date(string='Fecha ejecución', readonly=True, )
    request_date = fields.Date(string='Fecha solicitud', readonly=True, )
    company_id = fields.Many2one('res.company', string='Unidad de negocio', readonly=True, )
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipo', readonly=True, )
    category_id = fields.Many2one('maintenance.equipment.category', string='Tipología', readonly=True, )
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehículo', readonly=True, )
    license_plate = fields.Char(string='Matricula', readonly=True, )
    model_id = fields.Many2one('fleet.vehicle.model', string='Modelo', readonly=True, )
    odometro_planificacion = fields.Float(string='KM Planificación', readonly=True, )
    odometro_ejecucion = fields.Float(string='KM Ejecución', readonly=True, )
    preventivos = fields.Char(string='Preventivos', readonly=True, )
    correctivos = fields.Char(string='Correctivos', readonly=True, )
    maintenance_type_view = fields.Char(string='Tipo mantenimiento', readonly=True, )
    estado = fields.Char(string='Estatus', readonly=True, )

    def get_query(self, dates=False, date=False):
        sql = """
             SELECT row_number() OVER() as id,
                mr.id AS maintenance_id, 
                mr.name_seq, 
                mr.stage_id,
                mrt.maintenance_type,
                mr.schedule_date, 
                mr.close_date AS execution_date,
                mr.request_date, 
                mr.company_id,
                me.id AS equipment_id, 
                me.category_id, 
                fv.id AS vehicle_id, 
                fv.license_plate, 
                fv.model_id,
                (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<=mr.request_date ORDER BY fvo.date DESC LIMIT 1) AS odometro_planificacion,
                (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<=mr.close_date ORDER BY fvo.date DESC LIMIT 1) AS odometro_ejecucion,
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='preventive') AS preventivos,
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='corrective') AS correctivos,
                (CASE mrt.maintenance_type
                    WHEN 'preventive' THEN 'Preventivo'
                    WHEN 'corrective' THEN 'Correctivo'
                    END) AS maintenance_type_view,
                (CASE WHEN close_date IS NOT NULL THEN 'Ejecutado' ELSE 'Pentiente' END) AS estado
            FROM maintenance_request AS mr
                LEFT JOIN maintenance_equipment AS me ON me.id=mr.equipment_id
                LEFT JOIN fleet_vehicle AS fv ON fv.id = me.vehicle_id
                LEFT JOIN maintenance_request_type AS mrt ON mrt.id=mr.type_ot
                        --WHERE fv.id = 526 ORDER BY request_date  
            """
        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "WHERE mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "WHERE mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        query = f"create or replace view maintenance_request_details as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'maintenance_request_details')
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
        view_tree = self.env.ref('report_maintenance_mblz2.maintenance_request_details_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.maintenance_request_details_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.maintenance_request_details_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.maintenance_request_details_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.details',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_graph.id, 'graph'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
                'search_default_preventivos': 'preventive'
            }
        }

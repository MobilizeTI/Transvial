# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _, tools
from datetime import timedelta
from odoo.exceptions import Warning


class MaintenanceRequestPreventiveDetails(models.Model):
    _name = 'maintenance.request.preventive.details'
    _description = '1-24'
    _auto = False

    maintenance_id = fields.Many2one('maintenance.request', readonly=True, )
    name_seq = fields.Char(string='Numero de OT', readonly=True)
    name = fields.Char(string='Referencia de OT', readonly=True)
    type_id = fields.Many2one('maintenance.request.type', string='Tipo OT', readonly=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipo', readonly=True)
    license_plate = fields.Char(string='Matricula', readonly=True)
    model_id = fields.Many2one('fleet.vehicle.model', string='Modelo', readonly=True)
    category_id = fields.Many2one('maintenance.equipment.category', string='Tipología', readonly=True)
    activity_id = fields.Many2one('maintenance.request.task', string='Actividad', readonly=True)
    value = fields.Float(string='Kilometraje anterior', readonly=True)
    odometer_actual = fields.Float(string='Kilometraje actual', readonly=True)
    request_date = fields.Date(string='Fecha solicitud', readonly=True)
    schedule_date = fields.Date(string='Fecha prevista', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsable', readonly=True)
    stage_id = fields.Many2one('maintenance.stage', string='Estado', readonly=True)
    company_id = fields.Many2one('res.company', string='Unidad de negocio', readonly=True)
    preventivos = fields.Char(string='Preventivos', readonly=True, )
    correctivos = fields.Char(string='Correctivos', readonly=True, )
    maintenance_type_view = fields.Char(string='Tipo mantenimiento', readonly=True, )
    ejecutadas = fields.Integer(string='Mantenimientos Ejecutados', readonly=True, )
    no_ejecutadas = fields.Integer(string='Mantenimientos no Ejecutados', readonly=True, )

    # maintenance.request
    # maintenance.equipment
    # fleet.vehicle
    # maintenance.request.task
    # fleet.vehicle.odometer
    # maintenance.guideline *** -> schedule_date (segun)

    def get_query(self, dates=False, date=False):
        sql = """
            SELECT row_number() OVER() as id,
                mr.id AS maintenance_id, 
                mr.name_seq, 
                mr.name, 
                mr.type_ot AS type_id, 
                mr.request_date, 
                mr.user_id, 
                mr.stage_id, 
                mr.company_id, 
                mr.schedule_date,
                me.id AS equipment_id, 
                me.category_id,
                fv.license_plate, 
                fv.model_id,
                (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<mr.request_date ORDER BY fvo.date DESC LIMIT 1) AS value,
                (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<=mr.request_date ORDER BY fvo.date DESC LIMIT 1) AS odometer_actual,
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='preventive') AS preventivos,
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot AND maintenance_request_type.maintenance_type ='corrective') AS correctivos,
                (SELECT maintenance_type FROM maintenance_request_type WHERE maintenance_request_type.id=mr.type_ot) AS maintenance_type_view,
                mrt.id AS activity_id,
                (SELECT COUNT(*) FROM maintenance_stage AS ms WHERE mr.stage_id=ms.id AND ms.id IN (3,9)) AS ejecutadas,
                (SELECT COUNT(*) FROM maintenance_stage AS ms WHERE mr.stage_id=ms.id AND ms.id NOT IN (3,9)) AS no_ejecutadas
            FROM maintenance_request AS mr 
                LEFT JOIN maintenance_equipment AS me ON me.id=mr.equipment_id
                INNER JOIN fleet_vehicle AS fv ON fv.id=me.vehicle_id
                LEFT JOIN maintenance_request_task AS mrt ON mrt.request_id=mr.id
                """
        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "WHERE mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "WHERE mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        query = f"create or replace view maintenance_request_preventive_details as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'maintenance_request_preventive_details')
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
        view_tree = self.env.ref('report_maintenance_mblz2.maintenance_request_preventive_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.maintenance_request_preventive_details_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.maintenance_request_preventive_details_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.maintenance_request_preventive_details_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.preventive.details',
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

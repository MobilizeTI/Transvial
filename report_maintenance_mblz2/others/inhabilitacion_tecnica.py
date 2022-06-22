# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _, tools
from datetime import timedelta
from odoo.exceptions import Warning


class InhabilitacionTecnica(models.Model):
    _name = 'inhabilitacion.tecnica'
    _description = '1-43'
    _auto = False

    maintenance_id = fields.Many2one('maintenance.request', string='Referencia OT', readonly=True, )
    name_seq = fields.Char(string='Numero de OT', readonly=True, )
    type_ot_id = fields.Many2one('maintenance.request.type', string="Tipo Mantenimiento", readonly=True, )
    description = fields.Char(string='Descripción', readonly=True, )
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipo', readonly=True, )
    model_id = fields.Many2one('fleet.vehicle.model', string='Modelo', readonly=True, )
    category_id = fields.Many2one('maintenance.equipment.category', string='Tipología', readonly=True, )
    stage_id = fields.Many2one('maintenance.stage', string='Estado', readonly=True, )
    request_date = fields.Date(string='Fecha solicitud', readonly=True, )
    task_id = fields.Many2one('maintenance.request.task', string='Tarea', readonly=True, )
    activity_id = fields.Many2one('guideline.activity', string='Actividad', readonly=True, )
    component_id = fields.Many2one('maintenance.system.classification', string='Componente', readonly=True, )
    company_id = fields.Many2one('res.company', string='Unidad de negocio', readonly=True, )

    def get_query(self, dates=False, date=False):
        sql = """
            SELECT row_number() OVER() as id, 
                mr.id AS maintenance_id, 
                mr.name_seq, 
                mr.type_ot AS type_ot_id, 
                mr.description, 
                mr.equipment_id, 
                fv.model_id, 
                mr.stage_id, 
                mr.request_date, 
                mrt.id AS task_id, 
                ga.id AS activity_id,
                msc.id AS component_id, 
                mr.company_id, 
                msc.is_critical, 
                me.category_id
            FROM maintenance_request AS mr 
                INNER JOIN maintenance_request_type AS mrtt ON mrtt.id=mr.type_ot
                INNER JOIN maintenance_equipment AS me ON me.id=mr.equipment_id
                INNER JOIN fleet_vehicle AS fv ON fv.id=me.vehicle_id
                INNER JOIN maintenance_request_task AS mrt ON mrt.request_id=mr.id
                INNER JOIN guideline_activity AS ga ON ga.id=mrt.activity_id
                INNER JOIN maintenance_system_classification AS msc ON msc.id=ga.system_class_id
            """
        sql_where = " WHERE mr.stage_id != 9 AND mrtt.id IN (39,40) AND msc.is_critical = True "
        if dates:
            date_start, date_end = dates
            sql_where += "AND mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "AND mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        query = f"create or replace view inhabilitacion_tecnica as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'inhabilitacion_tecnica')
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
        view_tree = self.env.ref('report_maintenance_mblz2.inhabilitacion_tecnica_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.inhabilitacion_tecnica_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.inhabilitacion_tecnica_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.inhabilitacion_tecnica_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'cumplimiento.mtto.preventivo.details',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_graph.id, 'graph'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
            }
        }

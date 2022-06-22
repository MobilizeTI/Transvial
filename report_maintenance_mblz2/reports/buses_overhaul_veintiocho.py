from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class ReportBusesOverhaul(models.Model):
    _name = 'report.buses.overhaul'
    _description = 'report.buses.overhaul'
    _auto = False

    request_id = fields.Many2one(
        'maintenance.request',
        string='Referencia OT',
        readonly=True,
    )
    name = fields.Char(
        string='Nombre de OT',
        related='request_id.name',
    )

    name_seq = fields.Char(
        string='Número de OT',
        readonly=True,
    )

    maintenance_type = fields.Selection(
        string='Tipo de mantenimiento',
        selection=[('preventive', 'Preventivo'),
                   ('corrective', 'Correctivo')])

    stage_id = fields.Many2one(
        'maintenance.stage',
        string='Estado',
        readonly=True,
    )

    equipment_id = fields.Many2one(
        'maintenance.equipment',
        string='Equipo',
        readonly=True,
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        readonly=True,
    )

    license_plate = fields.Char(
        string='Matrícula',
        readonly=True,
    )

    category_id = fields.Many2one(
        'maintenance.equipment.category',
        string='Tipología',
        readonly=True,
    )

    task_id = fields.Many2one(
        'maintenance.request.task',
        string='Tarea',
        readonly=True,
    )

    task_activity_id = fields.Many2one(
        'guideline.activity',
        string='Actividad',
        readonly=True,
    )

    task_activity_system = fields.Many2one(
        'maintenance.system.classification',
        string='activity component',
        readonly=True,
    )
    system_name = fields.Char(
        string='Componente critico',
        related='task_activity_system.name',
    )

    system_parent_ids = fields.Many2many('maintenance.system', string='Sistemas',
                                         related='task_activity_system.parent_ids')

    is_critical = fields.Boolean(string='Check', readonly=True)

    odometer_actual = fields.Float(
        string='Odometro actual',
        related='vehicle_id.odometer',
    )

    schedule_date = fields.Date(
        string='Fecha prevista',
        readonly=True
    )
    request_date = fields.Date(
        string='Fecha solicitud', readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Unidad de negocio', readonly=True
    )

    company_name = fields.Char(
        string='Unidad de negocio',
        related='company_id.name',
    )

    def get_query(self, dates=False, date=False):
        sql = """
            select row_number() OVER () as id,
                       mr.id                as request_id,
                       mr.name_seq          as name_seq,
                       mrtype.maintenance_type  as maintenance_type,
                       mr.stage_id          as stage_id,
                       mr.equipment_id      as equipment_id,
                       me.vehicle_id        as vehicle_id,
                       fv.license_plate     as license_plate,
                       me.category_id       as category_id,
                       mrt.id               as task_id,
                       mrt.activity_id      as task_activity_id,
                       msc.id               as task_activity_system,
                       msc.is_critical      as is_critical,
                       mr.schedule_date,
                       mr.close_date        as execution_date,
                       mr.request_date,
                       mr.company_id
            from maintenance_request as mr
                         inner join maintenance_request_task mrt on mr.id = mrt.request_id
                         inner join maintenance_equipment as me on me.id = mr.equipment_id
                         inner join fleet_vehicle as fv on fv.id = me.vehicle_id
                         inner join guideline_activity as ga on ga.id = mrt.activity_id
                         inner join maintenance_system_classification as msc on msc.id = ga.system_class_id
                         inner join maintenance_request_type as mrtype on mrtype.id = mr.type_ot
            """

        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "where mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "where mr.request_date = '{0}'".format(date)
        sql += sql_where

        query = f"create or replace view report_buses_overhaul as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_buses_overhaul')
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
        view_tree = self.env.ref('report_maintenance_mblz2.report_buses_overhaul_tree')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_buses_overhaul_dashboard')
        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.buses.overhaul',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'), (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            'target': 'current',
            'context': {
                "search_default_groupby_request": True,
                "search_default_filter_corrective": "corrective",
                "search_default_filter_is_critical": True
            }
        }

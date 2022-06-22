from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class ReportBusesOperationalFailure(models.Model):
    _name = 'report.buses.operational.failure'
    _description = '1-42- KPI - Buses con falla operacionales'
    _auto = False

    request_id = fields.Many2one(
        'maintenance.request',
        string='Referencia OT',
        readonly=True,
    )
    name = fields.Char(
        string='Referencia de OT',
        related='request_id.name',
    )

    name_seq = fields.Char(
        string='Secuencia',
        readonly=True,
    )

    maintenance_type = fields.Selection(
        string='Naturaleza',
        selection=[('preventive', 'Preventivo'),
                   ('corrective', 'Correctivo')])

    type_ot = fields.Many2one('maintenance.request.type',
                              string='Tipo de OT', readonly=True)
    name_type_ot = fields.Char(
        string='Tipo de OT',
        related='type_ot.name',
    )

    motive = fields.Char(
        string='Motivo',
        readonly=True,
    )

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
        related='vehicle_id.license_plate',
    )

    model_id = fields.Many2one('fleet.vehicle.model', 'Modelo',
                               related='vehicle_id.model_id')

    category_id = fields.Many2one(
        'maintenance.equipment.category',
        string='Tipología',
        readonly=True,
    )

    request_date = fields.Date(
        string='Fecha de solicitud', readonly=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Unidad de negocio', readonly=True
    )

    company_name = fields.Char(
        string='Unidad de negocio',
        related='company_id.name',
    )

    def get_query(self, dates=False, date=False, data=False):
        sql = """
                select row_number() OVER ()    as id,
                       mr.id                   as request_id,
                       mr.name_seq             as name_seq,
                       mr.type_ot              as type_ot,
                       mr.description          as motive,
                       mrtype.maintenance_type as maintenance_type,
                       mr.maintenance_team_id  as maintenance_team_id,
                       mr.stage_id             as stage_id,
                       mr.equipment_id         as equipment_id,
                       me.vehicle_id           as vehicle_id,
                       me.category_id          as category_id,
                       mr.request_date         as request_date,
                       mr.company_id           as company_id
                from maintenance_request as mr
                         inner join maintenance_equipment as me on me.id = mr.equipment_id
                         inner join fleet_vehicle as fv on fv.id = me.vehicle_id
                         inner join maintenance_request_type as mrtype on mrtype.id = mr.type_ot
            """

        sql_where = "where mrtype.maintenance_type = 'corrective'"
        report_temp_id = data.get('report_temp_id', False) if data else False
        if report_temp_id:
            if not report_temp_id.all_stages:
                sql_where += "AND mr.stage_id in ({0})".format(
                    ','.join(map(str, report_temp_id.mt_stage_ids.ids)))
            if not report_temp_id.all_types:
                sql_where += "{0} mr.type_ot in ({1})".format('where' if sql_where == "" else ' AND',
                                                              ','.join(map(str, report_temp_id.type_ot_ids.mapped(
                                                                  'type_ot').ids)))
        if dates:
            date_start, date_end = dates
            sql_where += "{0} mr.request_date BETWEEN '{1}' AND '{2}'".format('where' if sql_where == "" else ' AND',
                                                                              date_start, date_end)
        if date:
            sql_where += "{0} mr.request_date = '{1}'".format('where' if sql_where == "" else ' AND', date)
        if sql_where != "":
            sql += sql_where

        query = f"create or replace view report_buses_operational_failure as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_buses_operational_failure')
        query = self.get_query()
        self._cr.execute(query)

    def get_act_window(self, data):
        if data['opc'] == 'dates':
            query = self.get_query(dates=data['dates'], data=data)
        elif data['opc'] == 'date':
            query = self.get_query(date=data['date'], data=data)
        else:
            query = self.get_query(data=data)
        self.env.cr.execute(query)
        if self.search_count([]) == 0:
            raise Warning('!No existe datos, para el filtro ingresado!')
        view_tree = self.env.ref('report_maintenance_mblz2.report_buses_operational_failure_tree')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_buses_operational_failure_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.buses.operational.failure',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'), (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
                # "search_default_groupby_request": True,
                # "search_default_filter_corrective": "corrective",
            }
        }

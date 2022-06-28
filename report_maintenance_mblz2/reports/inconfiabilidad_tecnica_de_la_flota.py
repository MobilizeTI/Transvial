from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning
from odoo.tools import groupby


class ReportFleetTechnicalUnreliability(models.Model):
    _name = 'report.fleet.technical.unreliability'
    _description = '2-13 - KPI - Inconfiabilidad técnica de la flota'
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

    odometer_actual = fields.Integer(
        string='Kilometraje',
        readonly=True)

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
    km_value = fields.Integer(string='kilometraje', readonly=True)

    # def _compute_km_value(self, value=0):
    #     for rec in self:
    #         rec.km_value = 0
    #         wz = rec.env['mtto.report.wz'].search([], limit=1, order='create_date desc')
    #         if wz:
    #             rec.km_value = wz.km_value

    def get_query(self, dates=False, date=False, data=False):
        km_value = data.get('km_value', 0) if data else 0

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
                       (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id AND fvo.date<=mr.request_date ORDER BY fvo.date DESC LIMIT 1) AS odometer_actual,
                       me.category_id          as category_id,
                       mr.request_date         as request_date,
                       mr.company_id           as company_id,
                       (select {} as km_value) as km_value
                from maintenance_request as mr
                         inner join maintenance_equipment as me on me.id = mr.equipment_id
                         inner join fleet_vehicle as fv on fv.id = me.vehicle_id
                         inner join maintenance_request_type as mrtype on mrtype.id = mr.type_ot
            """.format(km_value)
        sql_where = ""
        report_temp_id = data.get('report_temp_id', False) if data else False
        if report_temp_id:
            if not report_temp_id.all_stages:
                sql_where += "where mr.stage_id in ({0})".format(
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

        query = f"create or replace view report_fleet_technical_unreliability as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_fleet_technical_unreliability')
        query = self.get_query()
        self._cr.execute(query)

    @api.model
    def action_view_kpi(self, code_rpt_type=False, show_wz=False):
        total_odometer = 0
        km_value = 0
        records = self.search([])
        grouped = groupby(records, key=lambda it: it.equipment_id)
        total_equipment = 0
        for key, data in grouped:
            total_equipment += 1
            record_equip = self.concat(*data).sorted(key=lambda r: r.odometer_actual, reverse=True)
            aux = record_equip[0]
            km_value = aux.km_value
            total_odometer += aux.odometer_actual

        kpi = (total_equipment / total_odometer) * km_value

        message = f"<b>Total kilometraje: {total_odometer}<b/></br>" \
                  f"<b>Total buses inhabilitados: {total_equipment}<b/></br>" \
                  f"<b>Inconfiablididad {'Técnica' if code_rpt_type == '13' else ''}: <span class='text-danger text-bf'>{kpi:.2f}<span/><b/>"
        if not show_wz:
            self.env.user.notify_success(message=message, title=_('KPI'), sticky=True)
        else:
            return self.env.user.notify_success(message=message, title=_('KPI'), sticky=True)
            # wz_new = self.env['show.message.mtto'].sudo().create({'message': message})
            # context = dict(self._context or {})
            # context['message'] = message
            # return {
            #     # 'name': 'KPI',
            #     'type': 'ir.actions.act_window',
            #     'view_mode': 'form',
            #     'res_id': wz_new.id,
            #     'res_model': 'show.message.mtto',
            #     'target': 'new',
            # }
        # print(message)

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
        km_value = data.get('km_value', 0)
        code_rpt_type = data.get('code_rpt_type', False)
        self.action_view_kpi(code_rpt_type)

        view_tree = self.env.ref('report_maintenance_mblz2.report_fleet_technical_unreliability_tree')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_fleet_technical_unreliability_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.fleet.technical.unreliability',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'), (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {
                "search_default_equipment_id": True,
                # "search_default_filter_corrective": "corrective",
            }
        }

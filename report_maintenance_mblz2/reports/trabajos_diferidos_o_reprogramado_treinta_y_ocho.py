from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class ReportDeferredWork(models.Model):
    _name = 'report.deferred.work'
    _description = '1-35- Reporte - Trabajos diferidos o reprogramado'
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

    model_id = fields.Many2one('fleet.vehicle.model', 'Modelo',
                               related='vehicle_id.model_id')

    category_id = fields.Many2one(
        'maintenance.equipment.category',
        string='Tipología',
        readonly=True,
    )

    motive_log_ids = fields.One2many('maintenance.motive.log', related='request_id.motive_log_ids',
                                     string='Detail motives')

    last_record_motive = fields.Many2one(
        'maintenance.motive.log',
        string='last_record_motive',
        compute='_compute_last_motive_comment')

    last_motive = fields.Many2one('maintenance.motive.stage', string='Motivo',
                                  compute='_compute_last_motive_comment')

    last_motive_name = fields.Char(
        string='Motivo',
        related='last_motive.name')

    flag_with_motive_diff = fields.Boolean(
        string='flag_with_motive',
        related='request_id.flag_with_motive_diff')

    @api.depends('motive_log_ids')
    def _compute_last_motive_comment(self):
        """
            último motivo ya sea Repuestos no disponibles o Personal técnico no disponible
        """
        for request in self:
            # Número de días
            request.last_record_motive = False
            request.last_motive = False
            request.reset_date = False
            if request.motive_log_ids:
                record_filters = request.motive_log_ids.filtered(lambda l: l.motive_id.id in (5, 6))
                if record_filters:
                    last_record = record_filters.sorted(lambda l: l.date, reverse=True)[0]
                    request.last_record_motive = last_record.id
                    request.last_motive = last_record.motive_id.id
                    request.reset_date = last_record.date.date()

    request_date = fields.Date(
        string='Fecha de solicitud', readonly=True
    )

    reset_date = fields.Date(
        string='Fecha reprogramado',
        compute='_compute_last_motive_comment'
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
                select row_number() OVER ()    as id,
                       mr.id                   as request_id,
                       mr.name_seq             as name_seq,
                       mr.type_ot              as type_ot,
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

        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += " and  mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += " and mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where

        query = f"create or replace view report_deferred_work as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_deferred_work')
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
        if self.search_count([('flag_with_motive_diff', '=', True)]) == 0:
            raise Warning('!No existe datos, para el filtro ingresado!')
        view_tree = self.env.ref('report_maintenance_mblz2.report_deferred_work_tree')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_deferred_work_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.deferred.work',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'), (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            'domain': [('flag_with_motive_diff', '=', True)],
            'target': 'current',
            'context': {
                # "search_default_groupby_request": True,
                # "search_default_filter_corrective": "corrective",
            }
        }

import pytz

from odoo import fields, models, api, _, tools
from dateutil.relativedelta import relativedelta
# from pytz import timezone
from datetime import datetime, timedelta

from odoo.exceptions import Warning


# TZ_BOGOTA = timezone('America/Bogotá')


class ReportBusesStopped(models.Model):
    _name = 'report.buses.stopped'
    _description = 'Buses detenidos'
    _auto = False

    request_id = fields.Many2one(
        'maintenance.request',
        string='Referencia OT',
        readonly=True,
    )

    user_mtto_supervisor_id = fields.Many2one('res.users', string='MTTO supervisor',
                                              related='request_id.user_mtto_supervisor_id')

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

    type_ot = fields.Many2one('maintenance.request.type',
                              string='Tipo de OT', readonly=True)
    type_ot_name = fields.Char(
        string='Tipo de OT',
        related='type_ot.name')

    # motive_log_ids = fields.One2many('maintenance.motive.log', related='request_id.motive_log_ids',
    #                                  string='Detail motives')

    last_record_motive = fields.Many2one(
        'maintenance.motive.log',
        string='last_record_motive',
        compute='_compute_last_motive_comment')

    last_motive = fields.Many2one('maintenance.motive.stage', string='Motivo',
                                  compute='_compute_last_motive_comment')

    last_motive_name = fields.Char(
        string='Motivo',
        related='last_motive.name')

    detail_stop = fields.Char(string='Tiempo detenido', compute='_compute_last_motive_comment')

    def _get_datetime_now_localize(self):
        user_tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'America/Bogotá')
        now = datetime.now(tz=user_tz)
        return now

    def _date_to_datetime(self, value, h=0, m=0, s=0):
        date_convert = datetime(
            year=value.year,
            month=value.month,
            day=value.day,
        )
        return date_convert

    def _localize_datetime(self, date_time):
        user_tz = pytz.timezone(self._context.get('tz') or self.env.user.tz or 'America/Bogotá')
        datetime_localize = pytz.utc.localize(date_time).astimezone(user_tz)
        return datetime_localize

    datetime_detention = fields.Datetime(
        string='Fecha detención', compute='_compute_last_motive_comment'
    )

    @api.depends('request_id', 'confirm_datetime')
    def _compute_last_motive_comment(self):
        for record in self:
            # Número de días
            cant_days_stopped = 0
            cant_hours_stopped = 0
            cant_minutes_stopped = 0
            datetime_detention = False
            motive_log_ids = record.request_id.motive_log_ids

            if motive_log_ids:
                if len(motive_log_ids) > 1:
                    last_record = motive_log_ids.sorted(lambda l: l.date, reverse=True)[0]
                    record.last_record_motive = last_record.id
                    record.last_motive = last_record.motive_id.id
                    first_record = motive_log_ids.sorted(lambda l: l.date, reverse=False)[0]
                    if last_record and first_record:
                        datetime_detention = first_record.date  # fecha de detención del vehículo
                        diff_date = relativedelta(last_record.date, first_record.date)
                        cant_days_stopped += (last_record.date - first_record.date).days
                        cant_hours_stopped += diff_date.hours
                        cant_minutes_stopped += diff_date.minutes
                else:
                    last_record = motive_log_ids[0]
                    datetime_detention = last_record.date  # fecha de detención del vehículo

                if record.confirm_datetime and last_record:
                    if record.confirm_datetime > last_record.date:
                        diff_date = relativedelta(record.confirm_datetime, last_record.date)
                        cant_days_stopped += (record.confirm_datetime - last_record.date).days
                        cant_hours_stopped += diff_date.hours
                        cant_minutes_stopped += diff_date.minutes
                        record.last_record_motive = last_record.id
                        record.last_motive = last_record.motive_id.id
                    else:
                        record.last_motive = False

                if last_record and not record.confirm_datetime:
                    diff_date = relativedelta(fields.Datetime.now(), last_record.date)
                    cant_days_stopped += (fields.Datetime.now() - last_record.date).days
                    cant_hours_stopped += diff_date.hours
                    cant_minutes_stopped += diff_date.minutes

                    record.last_record_motive = last_record.id
                    record.last_motive = last_record.motive_id.id

            else:
                record.last_record_motive = False
                record.last_motive = False

            record.detail_stop = f'{cant_days_stopped + int(cant_hours_stopped / 24)} días {cant_hours_stopped % 24 + (cant_minutes_stopped * 60) % 60} horas {cant_minutes_stopped % 60} minutos'
            record.datetime_detention = datetime_detention

    maintenance_team_id = fields.Many2one('maintenance.team', string='Maintenance Team', readonly=True)

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

    stage_id = fields.Many2one(
        'maintenance.stage',
        string='Etapa',
        readonly=True,
    )

    request_date = fields.Date(
        string='Fecha de solicitud', readonly=True
    )

    confirm_datetime = fields.Datetime(
        string='Fecha de liberación',
        readonly=True
    )

    # picking_ids = fields.One2many('stock.picking', related='request_id.picking_ids', string='Transfers')
    task_id = fields.Many2one(
        comodel_name='maintenance.request.task',
        string='Task_id',
        required=False)

    employee_id = fields.Many2one('hr.employee', 'Técnico', related='task_id.employee_id')

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking', readonly=True
    )

    approval_id = fields.Many2one(
        comodel_name='approval.request',
        string='Aprobación',
        compute='_compute_approval_id')
    user_approver_ids = fields.Many2many('res.users',
                                         string="Aprobadores",
                                         compute='_compute_approval_id')

    @api.depends('picking_id')
    def _compute_approval_id(self):
        for record in self:
            approval_id = False
            user_approver_ids = [(6, 0, [])]
            if record.picking_id:
                approval = record.env['approval.request'].search(
                    [('picking_task_mtto_id.id', '=', record.picking_id.id)],
                    limit=1)
                if record:
                    approval_id = approval.id
                    user_approver_ids = [(6, 0,
                                          approval.approver_ids.filtered_domain([('status', '=', 'approved')]).mapped(
                                              'user_id.id'))]
            record.approval_id = approval_id
            record.user_approver_ids = user_approver_ids

    # date_planned = fields.Datetime('Fecha de recepción', compute='_compute_date_planned')
    #
    # @api.depends('picking_id')
    # def _compute_date_planned(self):
    #     for record in self:
    #         date_planned = False
    #         if record.picking_id and record.picking_id.origin:
    #             po = record.env['purchase.order'].sudo().search([('name', '=', record.picking_id.origin)], limit=1)
    #             if po:
    #                 date_planned = po.date_planned
    #         record.date_planned = date_planned

    pk_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Esperando otra operación'),
        ('confirmed', 'En espera'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Estado del Pk.', related='picking_id.state')

    stock_move_id = fields.Many2one(
        'stock.move',
        string='Move', readonly=True
    )
    sm_product_id = fields.Many2one(
        'product.product',
        string='Producto', readonly=True
    )
    sm_product_name = fields.Char(string='Producto', related='sm_product_id.name')
    sm_product_code = fields.Char(string='Código', related='sm_product_id.default_code')

    flag_with_motive = fields.Boolean(
        string='flag_with_motive',
        related='request_id.flag_with_motive')

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
                   mrt.id                  as task_id,
                   mrt.activity_id         as task_activity_id,
                   msc.id                  as task_activity_system,
                   msc.is_critical         as is_critical,
                   mr.confirm_datetime       as confirm_datetime,
                   mr.request_date         as request_date,
                   sp.id                   as picking_id,
                   sm.id                   as stock_move_id,
                   sm.product_id           as sm_product_id,
                   mr.company_id           as company_id
            from maintenance_request as mr
                     left join maintenance_request_task mrt on mr.id = mrt.request_id
                     left join maintenance_equipment as me on me.id = mr.equipment_id
                     left join fleet_vehicle as fv on fv.id = me.vehicle_id
                     left join guideline_activity as ga on ga.id = mrt.activity_id
                     left join maintenance_system_classification as msc on msc.id = ga.system_class_id
                     left join maintenance_request_type as mrtype on mrtype.id = mr.type_ot
                     left join stock_picking as sp on sp.maintenance_id = mr.id
                     left join stock_move sm on sp.id = sm.picking_id
        """

        sql_where = "where mr.flag_with_motive "
        # sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "AND mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "AND mr.request_date = '{0}'".format(date)
        sql += sql_where

        query = f"create or replace view report_buses_stopped as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_buses_stopped')
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
        if self.search_count([('flag_with_motive', '=', True)]) == 0:
            raise Warning('!No existe datos, para el filtro ingresado!')
        view_tree = self.env.ref('report_maintenance_mblz2.report_buses_stopped_tree')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_buses_stopped_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.buses.stopped',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'), (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [('flag_with_motive', '=', True)],
            'target': 'current',
            'context': {
                # "search_default_groupby_request": True,
                "search_default_filter_corrective": "corrective",
            }
        }

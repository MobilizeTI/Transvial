import datetime
import difflib
import json
import time

from dateutil.relativedelta import relativedelta
from datetime import timedelta

from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MaintenanceRequestType(models.Model):
    _name = 'maintenance.request.type'
    _description = 'Maintenance request type'

    sequence = fields.Integer(required=True, default=10)
    nro_type = fields.Char(string='Nro', required=False)
    name = fields.Char(string='Name', required=True)
    maintenance_type = fields.Selection(
        string=' Maintenance type',
        selection=[('preventive', 'Preventive'),
                   ('corrective', 'Corrective')],
        required=True, default='preventive')

    type_of_fault = fields.Selection(
        string=' Tipo de falla',
        selection=[('tec', 'Técnica'), ('ope', 'Operacional')],
        required=False)

    is_sirci = fields.Boolean(string='Es SIRCI', required=False)
    is_its = fields.Boolean(string='Es ITS', required=False)
    # is_sirci_or_its = fields.Selection(
    #     string='SIRCI/ITS',
    #     selection=[('sirci', 'SIRCI'), ('its', 'ITS')],
    #     required=False)

    description = fields.Text(string="Description", required=False)

    # _sql_constraints = [
    #     ('unique_name', 'unique (name)', 'El tipo de OT debe ser única!'),
    # ]

    # @api.model
    # def name_get(self):
    #     result = []
    #     for record in self:
    #         name = record.name
    #         type_trad = False
    #         if record.maintenance_type:
    #             type_trad = 'Correctivo' if record.maintenance_type == 'corrective' else 'Preventivo'
    #         type_of_fault = False
    #         if record.type_of_fault:
    #             type_of_fault = 'Técnica' if record.type_of_fault == 'tec' else 'Operacional'
    #         if type_trad and type_of_fault:
    #             name = f'{record.name} [{type_trad} - {type_of_fault}]'
    #         result.append((record.id, name))
    #         result.append((record.id, record.name))
    #     return result


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    user_mtto_supervisor_id = fields.Many2one('res.users', string='MTTO supervisor', tracking=True)

    name_seq = fields.Char(string='OT Reference', required=True, copy=False,
                           readonly=True,
                           index=True, default=lambda self: _('New'))

    type_ot = fields.Many2one('maintenance.request.type',
                              string='Type OT', required=True)

    create_type = fields.Selection(
        string=' Create type',
        selection=[('manual', 'Manual'),
                   ('master', 'Master'),
                   ('auto', 'Automatic')],
        required=False, default='manual')

    # def _get_default_team_id(self):
    #     MT = self.env['maintenance.team']
    #     team = MT.search([('company_id', '=', self.env.company.id)], limit=1)
    #     if not team:
    #         team = MT.search([], limit=1)
    #     return team.id
    #
    # maintenance_team_id = fields.Many2one('maintenance.team', string='Group', required=True,
    #                                       default=_get_default_team_id, check_company=True)

    maintenance_type = fields.Selection(related='type_ot.maintenance_type', string=' Maintenance type')

    maintenance_guideline_ids = fields.Many2many('maintenance.guideline',
                                                 string='Guidelines Of Maintenance',
                                                 check_company=True)

    @api.onchange('maintenance_guideline_ids')
    def onchange_maintenance_guideline_ids(self):
        for guideline in self.maintenance_guideline_ids:
            self.valid_create(self.equipment_id, guideline, opc=True)

    stage_name = fields.Char(related='stage_id.name')
    guide_line_ids = fields.One2many('maintenance.guideline', compute='_compute_guide_line_ids')

    @api.depends('equipment_id', 'maintenance_type')
    def _compute_guide_line_ids(self):
        for line in self:
            guide_line_ids = line.guide_line_ids.sudo().search([('equipment_ids', 'in', [line.equipment_id.id]),
                                                                ('maintenance_type', '=', line.maintenance_type)])
            line.guide_line_ids = guide_line_ids

    # equipment_activity_id = fields.Many2one('maintenance.equipment.activity',
    #                                         'Equipment Activity',
    #                                         related="maintenance_guideline_id.equipment_activity_id")

    flag_validate_auto = fields.Boolean(string='Validate automatically', required=False,
                                        help='This option changes to Repaired status when the tasks are completed.')

    task_ids = fields.One2many('maintenance.request.task',
                               'request_id', string='Tasks', required=False)

    task_done_percent = fields.Float('Advance percentage', compute='_compute_task_done_percent',
                                     help='Percentage of completed tasks')

    task_done_count = fields.Integer('Advance', compute='_compute_task_done_count',
                                     help='Number of completed tasks')

    count_task = fields.Integer(
        string='Count task',
        compute='_compute_task_done_percent')

    @api.depends('task_ids', 'task_done_count')
    def _compute_task_done_percent(self):
        for rec in self:
            task_done_percent = 0
            count_task = 0
            if rec.task_ids:
                cant_tasks = len(rec.task_ids)
                count_task = cant_tasks
                value = (rec.task_done_count / cant_tasks) * 100
                task_done_percent = value
            rec.sudo().count_task = count_task
            rec.sudo().task_done_percent = task_done_percent

    @api.depends('task_ids')
    def _compute_task_done_count(self):
        for rec in self:
            task_done_count = 0
            if rec.task_ids:
                tasks_done = rec.task_ids.filtered(lambda l: l.stage_id.id == 2)  # 2=Hecho
                if tasks_done:
                    task_done_count = len(tasks_done)

            rec.sudo().task_done_count = task_done_count

    task_count = fields.Integer('Quantity task', compute='compute_count_tasks')
    activity_count = fields.Integer('Quantity activities', compute='compute_count_tasks')

    def compute_count_tasks(self):
        for record in self:
            record.task_count = len(record.task_ids)
            record.activity_count = len(record.repetitive_activity_ids)

    def update_is_complete_task(self):
        for task in self.task_ids:
            # todo:// uso la lista de materiales el modulo l10n_cl_mrp_maintenance
            pickings_stage = task.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))

            # todo:// solicitudes de aprobación que esten pendientes
            approvals_satge = task.approval_ids.filtered(
                lambda r: r.request_status not in ('approved', 'refused', 'cancel'))

            if len(pickings_stage) == 0:
                if len(approvals_satge) == 0:
                    if not task.employee_id:
                        task.sudo().alert_close_task = 'no-employee'
                    # else:
                    #     task.sudo().alert_close_task = False
                else:
                    task.sudo().alert_close_task = 'approve_ma'
            else:
                task.sudo().alert_close_task = 'pickings'

    def get_tasks(self):
        self.ensure_one()
        self.update_is_complete_task()  # actualiza la alerta de cierre

        action = \
            self.env.ref('l10n_cl_maintenance.maintenance_request_task_admin_action').sudo().read()[
                0]
        action['domain'] = [('request_id', '=', self.id)]
        context = dict(self._context, create=True)
        if 'search_default_todo' in context:
            context.pop('search_default_todo')

        context.update({'default_request_id': self.id, 'default_flag_from_request': True})
        action['context'] = context
        if self.task_ids:
            if len(self.task_ids) == 1:
                temp_id = self.task_ids[:1]
                res = self.env.ref('l10n_cl_maintenance.maintenance_request_task_view_form', False)
                form_view = [(res and res.id or False, 'form')]
                action['views'] = form_view
                action['res_id'] = temp_id.id
        else:
            action['views'] = action['views'][1:]
        return action

    guideline_speciality_ids = fields.Many2many(
        'hr.specialty.tag',
        compute='_compute_guideline_speciality_ids',
        string='Specialities')

    @api.depends('maintenance_guideline_ids')
    def _compute_guideline_speciality_ids(self):
        for rec in self:
            set_speciality = set()
            for guideline in rec.maintenance_guideline_ids:
                for line in guideline.activities_ids:
                    for speciality in line.activity_speciality_ids:
                        set_speciality.add(speciality.id)
            rec.sudo().guideline_speciality_ids = [
                (6, 0, list(set_speciality))]

    @api.onchange('maintenance_type')
    def onchange_maintenance_type(self):
        if self.maintenance_guideline_ids and not self.flag_from_otm:
            self.sudo().update(
                dict(maintenance_guideline_ids=[(6, 0, [])]))

    def write(self, values):
        # Add code
        if 'maintenance_guideline_ids' in values:
            aux_ids = values.get('maintenance_guideline_ids', [])
            ids = []
            for aux in aux_ids:
                ids += aux[2]
            maintenance_guideline_ids = self.env['maintenance.guideline'].browse(ids)
            data_task = []
            for guideline in maintenance_guideline_ids:
                guideline.bool_in_request = True
                common_activities = guideline.activities_ids
                for line in common_activities:
                    data_task.append((0, 0, dict(activity_id=line.activity_id.id,
                                                 flag_create_task=True,
                                                 request_id=self.id)))
            values.update(dict(task_ids=data_task))
            if self.task_ids:
                self.sudo().task_ids = [(6, 0, [])]
        rec = super(MaintenanceRequest, self).write(values)
        # if 'stage_id' in values:
        #     stage_id = self.stage_id.browse(values.get('stage_id'))
        #     if stage_id == 9:  # cerrada
        #         tasks = self.task_ids.filtered(lambda l: l.stage_id.id == 1)
        #         if len(tasks) > 0:
        #             raise ValidationError(_(f'Hay tareas que hacer relacionadas con la solicitud {self.name}'))
        # FIXME: validar!
        # ot_new = self
        # self.create_write_log_odometer(ot_new)
        return rec

    def valid_create(self, equipment, guideline, opc=False):
        ot_ids = self.search(
            [('equipment_id', '=', equipment.id), ('company_id', '=', self.env.company.id)])

        count_ot_created = len(
            ot_ids.filtered(lambda ot: guideline.name in ot.maintenance_guideline_ids.mapped('name')))
        if count_ot_created > 0 and guideline.measurement == 'frequently':
            odometer_actual = equipment.vehicle_id.odometer
            value = odometer_actual / (guideline.percentage_value if guideline.percentage_value > 0 else 1)
            result = count_ot_created < value
            if opc and not result:
                raise ValidationError(
                    f'El odómetro actual {odometer_actual} no cumple con lo establecido en la pauta {guideline.name} para poder ejecutarse!\n\n'
                    f'Equipo: {equipment.name} ---- Pauta: {guideline.name}\n'
                    f'Cantidad de OT creadas: {count_ot_created}\n'
                    f'Cantidad de OT permitidas promedio: {round(value, 2)}')
            else:
                return result
        else:
            result = count_ot_created >= 1
            if opc and result:
                raise ValidationError(f'La pauta {guideline.name} ya ha sido ejecuta para el bus {equipment.name}')
            else:
                return not result

    # MSJ: OT reiterativas
    alert_repetitive = fields.Html(string="Alerta ot's reiterativas", copy=False)
    flag_alert_repetitive = fields.Boolean(string='alert_repetitive', copy=False)
    last_update_ar = fields.Date(string="Fecha de act. de alerta ot's reiterativas", copy=False)

    repetitive_activity_ids = fields.Many2many(comodel_name='guideline.activity', string='Actividades reiterativas',
                                               copy=False)

    def valid_alert_ots_repetitive(self, request_id):
        domain = [('request_date', '>=',
                   ((fields.Date.context_today(self) + relativedelta(days=-7)).strftime('%Y-%m-%d'))),
                  ('equipment_id', '=', self.equipment_id.id),
                  ('id', '!=', request_id),
                  ('company_id', '=', self.env.company.id)]
        requests_last_day7 = self.search(domain)
        valid_activity = []
        actual_activity_id_ids = self.task_ids.mapped('activity_id').ids
        for request in requests_last_day7:
            activity_id_ids = request.task_ids.mapped('activity_id').ids
            # las tareas que tengan el mayor o igual 90% de similitud lo toma en cuenta
            set1 = set(actual_activity_id_ids)
            set2 = set(activity_id_ids)
            # sm_activity = difflib.SequenceMatcher(None, list(set1), list(set2))
            # print(f'actual: {set1} -- {set2} sm: {sm_activity.ratio()}')
            # if sm_activity.ratio() >= 0.9:
            activity_intersection = set.intersection(set1, set2)
            valid_activity += list(activity_intersection)
        rep = set(valid_activity)
        if rep:
            filter_activity_ids = self.env['guideline.activity'].sudo().browse(list(rep))
            alert_repetitive = f"""En los últimos 7 días, el autobús {self.equipment_id.name} ha tenido las actividades designadas."""
            self.sudo().write(
                {
                    'alert_repetitive': alert_repetitive,
                    'flag_alert_repetitive': True,
                    'last_update_ar': fields.Datetime.now().date(),
                    'repetitive_activity_ids': [(6, 0, filter_activity_ids.ids)]
                }
            )

    def button_view_activities_reiteratives(self):
        self.ensure_one()
        action = \
            self.env.ref('l10n_cl_maintenance.guideline_activity_act_window').sudo().read()[
                0]
        action['domain'] = [('id', 'in', self.repetitive_activity_ids.ids)]
        context = dict(self._context, create=True)
        action['context'] = context
        if self.repetitive_activity_ids:
            if len(self.repetitive_activity_ids) == 1:
                temp_id = self.repetitive_activity_ids[:1]
                res = self.env.ref('l10n_cl_maintenance.guideline_activity_form_view', False)
                form_view = [(res and res.id or False, 'form')]
                action['views'] = form_view
                action['res_id'] = temp_id.id
        else:
            action['views'] = action['views'][1:]
        return action

    @api.model
    def clear_activities_reiteratives(self):
        domain = [('request_date', '>=',
                   ((fields.Date.context_today(self) + relativedelta(days=-7)).strftime('%Y-%m-%d'))),
                  ('company_id', '=', self.env.company.id)]
        request_ids = self.search(domain)
        for request in self.search([('id', 'not in', request_ids.ids)]):
            request.sudo().write({
                'alert_repetitive': False,
                'flag_alert_repetitive': False,
                'last_update_ar': False,
                'repetitive_activity_ids': [(6, 0, [])]
            }
            )

    @api.model
    def create(self, values):
        if 'equipment_id' in values:
            equipment_id = values.get('equipment_id', False)
        if not equipment_id:
            raise ValidationError(_('The equipment field is mandatory for the creation of a OT!!!'))
        # Add code here
        if values.get('name_seq', _('New')) == _('New'):
            name_seq = self.env['ir.sequence'].next_by_code('mt.sequence')
            values.update(dict(name_seq=name_seq))
        ot_new = super(MaintenanceRequest, self).create(values)
        if 'maintenance_guideline_ids' in values:
            aux_ids = values.get('maintenance_guideline_ids', [])
            ids = []
            for aux in aux_ids:
                ids += aux[2]
            maintenance_guideline_ids = self.env['maintenance.guideline'].browse(ids)
            data_task = []
            for guideline in maintenance_guideline_ids:
                guideline.bool_in_request = True
                common_activities = guideline.activities_ids
                for line in common_activities:
                    data_task.append((0, 0, dict(activity_id=line.activity_id.id,
                                                 flag_create_task=True,
                                                 request_id=ot_new.id)))
            ot_new.write(dict(task_ids=data_task))

        if ot_new.equipment_id and ot_new.guide_line_ids:
            self.create_write_log_odometer(ot_new)
        return ot_new

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f'{record.name} [{record.name_seq}]'))
        return result

    def create_write_log_odometer(self, ot_new):
        # Se crea/actualzia el log para el bus con us km actual
        obj_log_odometer = self.env['equipment.odometer.log'].sudo()
        # date_now = fields.datetime.now().date()
        vals_log = {
            'equipment_id': ot_new.equipment_id.id,
            'vehicle_id': ot_new.equipment_id.vehicle_id.id,
            'last_odometer': ot_new.equipment_id.vehicle_id.odometer,
            'odometer_unit': ot_new.equipment_id.vehicle_id.odometer_unit,
        }

        for guideline in ot_new.maintenance_guideline_ids:
            res = obj_log_odometer.is_log_date(ot_new.equipment_id.id, guideline.id)
            vals_log.update({'guideline_id': guideline.id})
            if not res.get('ok', False):
                # crea el log
                if guideline.type_auto_planning == 'accumulated':
                    vals_log.update({'next_odometer': 0.0,
                                     'type_odometer': 'next'})
                log_new = obj_log_odometer.create(vals_log)
                if log_new:
                    _logger.info(f"New log odometer for guideline {guideline.name} ok!")
                else:
                    _logger.error("Error new log odometer!")
            elif res.get('log', False):
                # actualiza el log
                log = res.get('log')
                if guideline.type_auto_planning == 'accumulated':
                    if guideline.measurement == 'frequently':
                        odometer_new = log.odometer + guideline.percentage_value
                        vals_log.update({'next_odometer': odometer_new})
                    else:
                        vals_log.update({'flag_process': True})
                log.write(vals_log)
                _logger.info(f"Update log guideline {guideline.name} ok!")

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        if self.equipment_id:
            # self.user_id = self.equipment_id.technician_user_id if self.equipment_id.technician_user_id else self.equipment_id.category_id.technician_user_id
            self.category_id = self.equipment_id.category_id
            if self.equipment_id.maintenance_team_id:
                self.maintenance_team_id = self.equipment_id.maintenance_team_id.id

    @api.onchange('category_id')
    def onchange_category_id(self):
        # if not self.user_id or not self.equipment_id or (self.user_id and not self.equipment_id.technician_user_id):
        #     if self.equipment_id:
        #         self.user_id = self.category_id.technician_user_id
        #     else:
        self.user_id = self.env.user.id

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['schedule_date'] = fields.Datetime.now()
        res['user_id'] = self.env.user.id
        return res

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        # Realizar una búsqueda con criterios predeterminados
        names1 = super().name_search(
            name=name, args=args, operator=operator, limit=limit
        )
        # Haz la otra búsqueda
        names2 = []
        if name:
            domain = [("name_seq", "=ilike", name + "%")]
            names2 = self.sudo().search(domain, limit=limit).name_get()
        # Fusionar ambos resultados
        return list(set(names1) | set(names2))[:limit]

    timesheet_total_hours = fields.Float(compute="_compute_timesheet_total_hours")

    @api.depends("task_ids.timesheet_ids")
    def _compute_timesheet_total_hours(self):
        for request in self:
            timesheet_total_hours = 0
            for task in request.task_ids:
                timesheet_total_hours += sum(task.timesheet_ids.mapped('unit_amount'))
            request.sudo().timesheet_total_hours = timesheet_total_hours

    # Duración
    duration_compute = fields.Float(compute='_compute_duration_compute')

    @api.depends('task_ids')
    def _compute_duration_compute(self):
        for request in self:
            request.sudo().duration_compute = 0
            if request.task_ids:
                sum_duration = 0
                for task in request.task_ids:
                    sum_duration += task.activity_id.duration
                request.duration_compute = sum_duration
                if request.duration == 0:
                    request.sudo().duration = sum_duration

    #
    # @api.onchange('duration_compute')
    # def onchange_duration_compute(self):
    #     self.duration = self.duration_compute

    # OT Maestra
    ot_master_id = fields.Many2one('maintenance.request.master', string='OT Master',
                                   ondelete='cascade',
                                   required=False)
    flag_from_otm = fields.Boolean(string='Flag from OTM', required=False)
    flag_from_auto = fields.Boolean(string='Flag from auto', required=False)

    # Ejecutar Planificador
    @api.model
    def run_scheduler(self, get_log=False):
        _logger.info(f'>>>>> Ejecutar cron para crear una nueva OT...!!!')
        data_log = []
        equipments = self.env['maintenance.equipment'].sudo().search([
            ('vehicle_id', '!=', False),
            ('active', '=', True),
            ('company_id', '=', self.env.company.id)])

        guidelines = self.env['maintenance.guideline'].sudo().search(
            [('maintenance_type', '=', 'preventive'),
             ('flag_create_auto', '=', True),
             ('flag_execute_auto', '=', False),
             ])

        obj_log_odometer = self.env['equipment.odometer.log'].sudo()
        for equipment in equipments:
            for guideline in guidelines:

                # Se valida que la ot no este creada para el equipo y pauta especifica desde el cron
                is_created = self.valid_create(equipment, guideline)
                if is_created:
                    # último odometro registrado para bus con la pauta específica
                    log_last = obj_log_odometer.get_last_log(equipment.id, guideline.id)
                    if log_last:
                        odometer_actual = equipment.vehicle_id.odometer
                        if log_last.type_auto_planning == 'latest':
                            # cálculo de la diferencia entre el odometro actual y el ultimo registrado
                            dif_odometer_value = odometer_actual - log_last.last_odometer
                            if dif_odometer_value >= guideline.percentage_value:
                                record_log = self._create_ot_auto(equipment, guideline)
                                if record_log:
                                    data_log.append(record_log)
                        else:
                            if odometer_actual >= log_last.odometer:
                                record_log = self._create_ot_auto(equipment, guideline)
                                if record_log:
                                    data_log.append(record_log)
                    else:
                        msj = f'El odómetro del bus: {equipment.name} no cumple con el % registrado en la pauta!'
                        _logger.info(msj)
                        # data_log.append({
                        #     'bus': equipment.name,
                        #     'msj': msj,
                        #     'result': 'Advertencia'
                        # })

                else:
                    msj = f'Ya existe la ot creada para: {equipment.name} y la pauta {guideline.name}!'
                    _logger.info(msj)
                    data_log.append({
                        'bus': equipment,
                        'pauta': guideline,
                        'msj': msj,
                        'result': 'Advertencia'
                    })

        if get_log:
            return data_log

    def _create_ot_auto(self, equipment, guideline):
        # se crea la ot con la pauta actual para el bus
        # ot_template = self.env['ot.template'].sudo().search([('guideline_id', '=', guideline.id)],
        #                                                     limit=1)
        obj_maintenance_request = self.env['maintenance.request'].sudo()
        ot_template = guideline.ot_template_id
        record_log = {}
        if ot_template:
            ot_vals = {
                'name': f'{ot_template.name_header} - {equipment.name}',
                'equipment_id': equipment.id,
                'employee_id': ot_template.employee_id.id,
                'user_id': ot_template.employee_id.user_id.id,
                'type_ot': ot_template.type_ot.id,
                'maintenance_guideline_ids': [(6, 0, [guideline.id])],
                'schedule_date': fields.Datetime.now(),
                'flag_from_auto': True,
                'create_type': 'auto',
            }
            try:
                ot_new = obj_maintenance_request.create(ot_vals)
                # si la medición al alcanzar el valor se actualiza el flag para que ya no se vuelva a ejecutar
                if guideline.measurement == 'fixed':
                    guideline.flag_execute_auto = True
                record_log = {
                    'bus': equipment,
                    'pauta': guideline,
                    'msj': f'OT: {ot_new.name} SEQ: {ot_new.name_seq} creada correctamente',
                    'result': 'Éxito'
                }
                _logger.info(f'>>> Nueva OT: {ot_new.name}')
            except Exception as e:
                _logger.error(str(e))
        else:
            record_log = {
                'bus': equipment,
                'pauta': guideline,
                'msj': f'No existe plantilla para la pauta de mantenimiento de {guideline.name}',
                'result': 'Error'
            }
            # raise ValidationError(
            #     _(f'There is no template for the {guideline.name} maintenance guideline.'))
        return record_log

    def _validate_create_ot_cron(self, equipment_id, guideline_id):
        ot_ids = self.search(
            [('equipment_id', '=', equipment_id), ('company_id', '=', self.env.company.id)])
        ot_filter = ot_ids.filtered(lambda ot: guideline_id in ot.maintenance_guideline_ids.ids)
        if not ot_filter:
            return False
        else:
            return True

    # cierre automatizado
    closing_comment = fields.Text(string="Closing comment", required=False)

    # filtros de cierre
    is_close_30 = fields.Boolean(string='Close 30 days', required=False)
    is_close_15 = fields.Boolean(string='Close 15 days', required=False)
    is_close_7 = fields.Boolean(string='Close 7 days', required=False)

    @api.model
    def refresh_filter_close_days(self):
        # Se inicializa las flags de para los filtros
        request_all = self.search([])
        for r in request_all:
            r.sudo().is_close_30 = False
            r.sudo().is_close_15 = False
            r.sudo().is_close_7 = False

        self._get_request_for_days()
        self._get_request_for_days(15)
        self._get_request_for_days(7)

    def _get_request_for_days(self, day=30):
        domain = [('close_date', '>=',
                   ((fields.Date.context_today(self) + relativedelta(months=-1)).strftime('%Y-%m-%d')))]

        if day == 15:
            domain = [('close_date', '>=',
                       ((fields.Date.context_today(self) + relativedelta(days=-15)).strftime('%Y-%m-%d')))]

        elif day == 7:
            domain = [('close_date', '>=',
                       ((fields.Date.context_today(self) + relativedelta(days=-7)).strftime('%Y-%m-%d')))]

        # print(domain)
        request_filter = self.search(domain)
        request_filter_close = self.search([('stage_name', '!=', 'Cerrada')])
        data = request_filter + request_filter_close
        _logger.info(f'days: {day}\ndomain: {domain}\nlen close: {len(request_filter)} len all: {len(data)}')

        for r in data:
            if day == 30:
                r.sudo().is_close_30 = True
            elif day == 15:
                r.sudo().is_close_15 = True
            elif day == 7:
                r.sudo().is_close_7 = True

    # color en las lineas de ot masivas
    alert_otm = fields.Selection(
        string='Alerta OTM',
        selection=[('approve_ma', 'Solicitud de materiales'),
                   ('pickings', 'Pickings abiertos'),
                   ('no-employee', 'No empleado'),
                   ('all', 'Todas'),
                   ],
        required=False, )

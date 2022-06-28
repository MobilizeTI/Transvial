import json

from odoo import models, fields, api, _
import pytz

from odoo.exceptions import Warning, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, date_utils
from datetime import date, datetime, time, timedelta


class MRT(models.Model):
    _inherit = 'maintenance.request.task'

    #
    # activity_id_domain = fields.Char(
    #     compute="_compute_activity_id_domain",
    #     readonly=True,
    #     store=False,
    # )
    #
    # @api.depends('request_id')
    # def _compute_activity_id_domain(self):
    #     for rec in self:
    #         domain = []
    #         if rec.request_id:
    #             if rec.request_id.create_type == 'ticket':
    #                 activity_its = self.env['hr.specialty.tag'].sudo().search([('name', '=', 'ITS')], limit=1)
    #                 if not activity_its:
    #                     raise ValidationError('No existe la especialidad de nombre ITS ')
    #                 activity_all = rec.activity_id.search([])
    #                 activity_filter = activity_all.filtered(lambda a: activity_its.id in a.specialty_tag_ids.ids)
    #                 domain = [('id', 'in', activity_filter.ids)]
    #
    #         rec.activity_id_domain = json.dumps(domain)

    @api.onchange('request_id')
    def onchange_request_id(self):
        if self.request_id.create_type == 'ticket':
            activity_its = self.env['hr.specialty.tag'].sudo().search([('name', '=', 'ITS')], limit=1)
            if not activity_its:
                raise ValidationError('No existe la especialidad de nombre ITS ')
            activity_all = self.activity_id.search([])
            activity_filter = activity_all.filtered(lambda a: activity_its.id in a.specialty_tag_ids.ids)
            return {'domain': {'activity_id': [('id', 'in', activity_filter.ids)]}}


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    create_type = fields.Selection(selection_add=[('ticket', 'Ticket'), ('totem', 'Totem')])

    ticket_id = fields.Many2one(comodel_name='helpdesk.ticket', string='Ticket',
                                required=False, copy=False)

    is_complete_task = fields.Boolean(string='Tareas completadas', required=False)

    datetime_create_ot = fields.Datetime(string='Fecha y hora de creación', compute='_compute_datetime_create_ot')
    msj_solution_close = fields.Text(string="Solución", required=False,
                                     help='Mensaje de solución de cierre de de OT para el ticket')

    @api.depends('create_date')
    def _compute_datetime_create_ot(self):
        for rec in self:
            if rec.create_date:
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'America/Bogotá')
                time_in_timezone = pytz.utc.localize(rec.create_date).astimezone(user_tz)
                rec.datetime_create_ot = time_in_timezone.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                rec.datetime_create_ot = False

    def write(self, values):
        # Add code here
        upd_ot = super(MaintenanceRequest, self).write(values)

        # si el estado es in progreso -> actualiza el estado del ticket a en progreso
        if self.stage_id.id == 2:
            self.ticket_id.stage_id = 2
        # si el estado es reparado o terminado -> actualiza el estado del ticket a resuelto
        elif self.stage_id.id == 9:
            self.with_context(update_ot_tickt=True).ticket_id.stage_id = 3

        return upd_ot

    def _date_to_datetime(self, value, h=0, m=0, s=0):
        date_convert = datetime(
            year=value.year,
            month=value.month,
            day=value.day,
        )
        return date_convert

    def action_update_confirm_datetime(self):
        for rec in self.search([('stage_id', '=', 9)]):
            confirm_datetime = self._date_to_datetime(rec.confirm_date) if rec.confirm_date else False
            for mjs in rec.message_ids:
                if mjs.tracking_value_ids:
                    tracking_value = mjs.tracking_value_ids[0]
                    if tracking_value.new_value_char and tracking_value.new_value_char == 'Confirmada':
                        confirm_datetime = mjs.date
            rec.confirm_datetime = confirm_datetime

    def _set_maintenance_stage(self, next_stage_id):
        if next_stage_id == 9 and self.ticket_id and not self.msj_solution_close:
            return self.open_solution_wizard()
            # raise ValidationError(f'Ingrese la solución de cierre para el ticket {self.ticket_id.name}')
        return super(MaintenanceRequest, self)._set_maintenance_stage(next_stage_id)

    def open_solution_wizard(self, next_stage_id=9):
        action = self.env.ref('mblz_mueve.action_stage_solution_wizard').read()[0]
        context = dict(self._context or {})
        context['default_stage_id'] = next_stage_id
        context['default_request_id'] = self.id
        action['context'] = context
        return action

    @api.model
    def default_get(self, fields_list):
        values = super(MaintenanceRequest, self).default_get(fields_list)
        if values.get('employee_id', False):
            values.update(dict(employee_id=False))
        return values

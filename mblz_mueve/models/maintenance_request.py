from odoo import models, fields, api, _
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, date_utils
from datetime import date, datetime, time, timedelta


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    create_type = fields.Selection(selection_add=[('ticket', 'Ticket')])

    ticket_id = fields.Many2one(comodel_name='helpdesk.ticket', string='Ticket',
                                required=False)

    is_complete_task = fields.Boolean(string='Tareas completadas', required=False)

    datetime_create_ot = fields.Datetime(
        string='datetime_create_ot',
        compute='_compute_datetime_create_ot')

    @api.depends('create_date')
    def _compute_datetime_create_ot(self):
        for rec in self:
            if rec.create_date:
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'America/Bogota')
                time_in_timezone = pytz.utc.localize(rec.create_date).astimezone(user_tz)
                rec.datetime_create_ot = time_in_timezone.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            else:
                rec.datetime_create_ot = False

    @api.model
    def create(self, values):
        # Add code here
        request_new = super(MaintenanceRequest, self).create(values)
        user_tkt_id = self._context.get('user_tkt_id', False)
        if user_tkt_id:
            request_new.user_id = user_tkt_id

        if request_new.create_type == 'ticket':
            request_new.ticket_id.mtm_request_id = request_new.id
            task_data = []
            for line in request_new.ticket_id.support_activity_ids:
                task_data.append((0, 0, dict(activity_id=line.activity_id.id,
                                             request_id=request_new.id
                                             )
                                  ))

            request_new.task_ids = task_data

        return request_new

    def _date_to_datetime(self, value, h=0, m=0, s=0):
        date_convert = datetime(
            year=value.year,
            month=value.month,
            day=value.day,
        )
        return date_convert

    def action_update_confirm_datetime(self):
        for rec in self.sudo().search([('stage_id', '=', 9)]):
            confirm_datetime = self._date_to_datetime(rec.confirm_date) if rec.confirm_date else False
            for mjs in rec.message_ids:
                if mjs.tracking_value_ids:
                    tracking_value = mjs.tracking_value_ids[0]
                    if tracking_value.new_value_char and tracking_value.new_value_char == 'Confirmada':
                        confirm_datetime = mjs.date
            rec.sudo().confirm_datetime = confirm_datetime

    # REPORTES
    # @api.model
    # def action_create_xlsx_01(self, parameter=False):
    #     data = {'selected': False}
    #     return self.env.ref('mblz_mueve.action_report_mr_xlsx_01').report_action(self, data=data)

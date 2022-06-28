# -*- coding: utf-8 -*-
import json

from odoo import api, models, tools, fields, _
from datetime import timedelta, datetime
from pytz import timezone

import logging
import threading

from odoo.exceptions import ValidationError, Warning

_logger = logging.getLogger(__name__)

TZ_BOGOTA = timezone('America/Bogota')


class CloseTKTMassive(models.TransientModel):
    _name = 'close.tkt.massive'
    _description = 'Close TKT Massive'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    flag_employee = fields.Boolean(string='¿Asignar empleado masivo?', required=False)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', required=False)

    time_spent = fields.Float('Duración', digits=(16, 2))
    description_ph = fields.Char('Descripción', help='Descripción parte de horas')
    msj_solution_close = fields.Text(string="Solución",
                                     help='Mensaje de solución de cierre de de OT para el ticket')

    # OT Maestra
    tkt_master_id = fields.Many2one('helpdesk.ticket.master', string='TKT Master',
                                    ondelete='cascade',
                                    required=False)

    select_all_request = fields.Many2many('maintenance.request', string="Seleccionar OT's")

    option = fields.Selection(
        string='Option',
        selection=[('close_ot', "Cerrar ot's"),
                   ('close_task', 'Cerrar tareas'), ],
        required=True, default='close_ot')

    specialty_tag_ids = fields.Many2many("hr.specialty.tag", string="Especialidades",
                                         compute='_compute_specialty_tag_ids')

    @api.depends('tkt_master_id')
    def _compute_specialty_tag_ids(self):
        for rec in self:
            if rec.tkt_master_id:
                specialty_tag_ids = []
                requests = rec.tkt_master_id.ticket_ids.mapped('mtm_request_id')
                for ot in requests:
                    for task in ot.task_ids:
                        specialty_tag_ids += task.activity_speciality_ids.ids
                rec.specialty_tag_ids = [(6, 0, list(set(specialty_tag_ids)))]
            else:
                rec.specialty_tag_ids = [(6, 0, [])]

    def _get_request(self, tkt_master):
        request_ids = tkt_master.ticket_ids.mapped('mtm_request_id').filtered_domain(
            [('stage_id.id', '!=', 9)])
        requests = []
        for request in request_ids:
            if request.task_ids:
                tasks_aux = request.task_ids.filtered(lambda l: l.stage_id.id == 1)
                if len(tasks_aux) == 0 and not request.alert_otm:
                    requests.append(request.id)
            else:
                requests.append(request.id)
        return requests

    @api.onchange('tkt_master_id')
    def onchange_tkt_master_id(self):
        for rec in self:
            request_ids = rec._get_request(rec.tkt_master_id)
            if not request_ids:
                rec.option = 'close_task'
                # raise Warning(_('There are no work orders that meet the automatic closing conditions.'))
            return {'domain': {'select_all_request': [('id', 'in', request_ids)]}}

    flag_employees_additional = fields.Boolean(string='Añadír empleados adicionales', required=False)

    @api.onchange('flag_employees_additional')
    def onchange_flag_employees_additional(self):
        if self.flag_employees_additional:
            user_technical_add_ids = self.tkt_master_id.user_technical_add_ids
            employee_ids = []
            for user in user_technical_add_ids:
                if user.employee_id:
                    employee_ids.append(user.employee_id.id)
            self.employee_ids = [(6, 0, employee_ids)]
        else:
            self.employee_ids = [(6, 0, [])]

    employee_ids = fields.Many2many(comodel_name='hr.employee', string='Empleados adicionales', required=False)

    option_ots = fields.Selection(
        string='Seleccione',
        selection=[('one', "OT"), ('custom', "OT's"), ('all', 'Todas')],
        required=False, default='all')

    ot_select_id = fields.Many2one('maintenance.request', string="OT", required=False)
    ot_select_ids = fields.Many2many('maintenance.request',
                                     'wz_close_tkt_massive_rel',
                                     'wz_tkt_select_id', 'request_id',
                                     string="OT's")

    ticket_ids = fields.One2many('helpdesk.ticket', string='Tickets', related='tkt_master_id.ticket_ids')

    def action_close_ot(self):
        # self.ensure_one()
        self._close_ots()

    def action_close_task(self):
        # self.ensure_one()
        return self._close_task()

    def _close_ots(self):
        for request in self.select_all_request:
            stage_close_id = self.env['maintenance.stage'].sudo().search([('name', '=ilike', 'cerrada')], limit=1)
            if not stage_close_id:
                raise ValidationError(_('No se pudo encontrar la etapa de cierre'))
            request.sudo().write({
                'stage_id': stage_close_id.id,
                'close_datetime': fields.datetime.now(),
                'msj_solution_close': self.msj_solution_close
            })
            request.ticket_id.sudo().write({'closing_comment': self.msj_solution_close})

    def _get_request_custom(self):
        if self.option_ots == 'one':
            return [self.ot_select_id]
        elif self.option_ots == 'custom':
            return self.ot_select_ids
        else:
            data = self.tkt_master_id.ticket_ids.mapped('mtm_request_id').filtered_domain([('stage_id', '!=', 9)])
            return data

    def _get_data_timesheet(self, task, employee_ids):
        timesheet_ids = []
        for employee_id in employee_ids:
            timesheet_ids.append((0, 0, {
                'task_request_id': task.id,
                'employee_id': employee_id,
                'date': fields.Date.context_today(self),
                'name': self.description_ph,
                'user_id': task.user_id.id,
                'unit_amount': self.time_spent,
            }))

        return timesheet_ids

    def _close_task(self):
        # txt_error = ""
        requests = self._get_request_custom()
        for ot in requests:
            tasks = ot.task_ids.filtered(lambda l: l.stage_id.id == 1)
            for task in tasks:
                # id = 2 estado HECHO

                vals = {
                    'stage_id': 2,
                }
                employee_ids = []
                if self.flag_employees_additional:
                    ids = task.employee_additional_ids.ids + self.employee_ids.ids
                    employee_ids += ids
                    vals.update({
                        'employee_additional_ids': [(6, 0, ids)]
                    })

                if self.employee_id and not task.employee_id:
                    # Se asigna el empleado y se crea un parte de horas generico
                    employee_ids.append(self.employee_id.id)
                    vals.update({
                        'employee_id': self.employee_id.id,
                    })
                else:
                    employee_ids.append(task.employee_id.id)

                timesheet_ids = self._get_data_timesheet(task, employee_ids)
                vals.update({
                    'timesheet_ids': timesheet_ids
                })

                # todo:// uso la lista de materiales el modulo l10n_cl_mrp_maintenance
                pickings_stage = task.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))

                # todo:// solicitudes de aprobación que esten pendientes
                approvals_satge = task.approval_ids.filtered(
                    lambda r: r.request_status not in ('approved', 'refused', 'cancel'))

                if len(pickings_stage) == 0:
                    if len(approvals_satge) == 0:
                        task.sudo().write(vals)
                        if not task.employee_id:
                            ot.sudo().alert_otm = 'no-employee'
                    else:
                        ot.sudo().alert_otm = 'approve_ma'
                else:
                    ot.sudo().alert_otm = 'pickings'
                ot.sudo().is_complete_task = False

            if len(tasks) == 0:
                ot.sudo().is_complete_task = True

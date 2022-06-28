# -*- coding: utf-8 -*-
from pprint import pprint
import pytz
from datetime import date, datetime, time, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, date_utils

TICKET_PRIORITY = [
    ('0', 'Todos'),
    ('1', 'Baja'),
    ('2', 'Alta'),
    ('3', 'Urgente'),
]


class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"

    def _default_stage_ids(self):
        default_stage = self.env['helpdesk.stage'].search([('name', '=', _('New'))], limit=1)
        if default_stage:
            return [(4, default_stage.id)]
        return [(0, 0, {'name': _('New'), 'sequence': 0,
                        'template_id': self.env.ref('mblz_mueve.new_ticket_request_email_template_mblz',
                                                    raise_if_not_found=False) or None})]


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'
    _order = 'name_seq desc'

    # Usuario cliente -> Asignado a (ok)
    # ID ticket:
    name_seq = fields.Char(string='SEQ', required=True, copy=False,
                           readonly=True,
                           index=True, default=lambda self: _('New'))

    # Tipo -> Tipo de ticket (ok)

    # Equipo
    equipment_id = fields.Many2one('maintenance.equipment',
                                   string='ID del vehículo')

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        if self.equipment_category_id and self.element_id:
            if self.equipment_category_id.id not in self.element_id.categ_ids.ids:
                self.element_id = False

    # ID movil
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', related='equipment_id.vehicle_id')
    equipment_category_id = fields.Many2one('maintenance.equipment.category',
                                            string='Equipment Category',
                                            related='equipment_id.category_id')
    # Detalle del incidente -> Descripción del ticket (ok)

    # Nivel de falla
    # failure_level_id = fields.Many2one('helpdesk.failure.level', string='Failure Level')

    # Nivel de soport
    support_level_ids = fields.Many2many('helpdesk.support.level', string='Support Levels')

    support_activity_ids = fields.Many2many('maintenance.guideline.activity',
                                            compute='_compute_support_activity_ids',
                                            string='Activities')

    # place_of_care = fields.Char(string='Place of care', required=False, help="Barrio")

    @api.depends('support_level_ids')
    def _compute_support_activity_ids(self):
        for rec in self:
            support_activity_ids = []
            if rec.support_level_ids:
                activities = set()
                for record in rec.support_level_ids:
                    aux = set(record.support_activity_ids.ids)
                    activities = activities.union(aux)
                support_activity_ids = [(6, 0, list(activities))]
            rec.sudo().support_activity_ids = support_activity_ids

    # OT
    mtm_request_id = fields.Many2one('maintenance.request', string='OT', required=False, copy=False, ondelete='cascade')
    ot_close_datetime = fields.Datetime('Fecha de cierre (OT)', related='mtm_request_id.close_datetime')

    # color en las lineas de ot masivas
    alert_otm = fields.Selection(
        string='Alerta OTM',
        selection=[('approve_ma', 'Solicitud de materiales'),
                   ('pickings', 'Pickings abiertos'),
                   ('no-employee', 'No empleado'),
                   ('all', 'Todas'),
                   ],
        related='mtm_request_id.alert_otm')
    # maintenance_guideline_ids = fields.Many2many('maintenance.guideline',
    #                                              string='Pautas', related='mtm_request_id.maintenance_guideline_ids')
    request_stage_id = fields.Many2one('maintenance.stage', string='Stage', related='mtm_request_id.stage_id')
    task_done_percent = fields.Float('Advance percentage', related='mtm_request_id.task_done_percent',
                                     help='Percentage of completed tasks')
    is_complete_task = fields.Boolean(string='Tareas', related='mtm_request_id.is_complete_task')

    # task_count = fields.Integer('Quantity task', related='mtm_request_id.task_count')

    def action_view_ot(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window',
                'res_model': 'maintenance.request',
                'view_mode': 'form',
                'res_id': self.mtm_request_id.id,
                'target': 'current',
                'flags': {'form': {'action_buttons': True}}}

    type_ot = fields.Many2one('maintenance.request.type', string='Tipo de OT', required=False, copy=True)

    @api.model
    def create(self, values):
        # Add code here
        if values.get('name_seq', _('New')) == _('New'):
            name_seq = self.env['ir.sequence'].next_by_code('ticket.sequence')
            values.update(dict(name_seq=name_seq, user_default_id=self.env.user.id))
        if values.get('flag_create_ot_auto', False):
            new_ot = self.action_create_ot(auto=True, values=values)
            if new_ot:
                values.update({'mtm_request_id': new_ot.id})
            else:
                raise ValidationError('No se pudo crear la OT')
        new_tkt = super(HelpdeskTicket, self).create(values)
        new_tkt.mtm_request_id.ticket_id = new_tkt.id

        # Se actualiza las tareas con las actividades (Niveles de soporte)
        if new_tkt.support_activity_ids:
            task_data = []
            activity_ids = new_tkt.mtm_request_id.task_ids.mapped('activity_id').ids
            for line in new_tkt.support_activity_ids:
                if line.activity_id.id not in activity_ids:
                    task_data.append((0, 0, dict(activity_id=line.activity_id.id,
                                                 request_id=new_tkt.mtm_request_id.id
                                                 )))

            new_tkt.mtm_request_id.task_ids = task_data
        return new_tkt

    def action_create_ot(self, auto=False, values=False):
        # self.ensure_one()
        if not auto:
            # action = self.env.ref('account.action_account_payments').read()[0]
            action = self.env['ir.actions.act_window']._for_xml_id('maintenance.hr_equipment_request_action')
            self.env.context = dict(self.env.context)
            self.env.context.update({'user_tkt_id': self.user_id.id, })
            context = dict(self._context)

            context.update({'default_name': self.name,
                            # 'default_partner_id': self.partner_id.id,
                            'default_user_id': self.user_id.id,
                            'default_ticket_id': self.id,
                            'default_equipment_id': self.equipment_id.id,
                            'default_type_ot': self.type_ot.id,
                            'default_create_type': 'ticket',
                            })
            # pprint(context)
            action['context'] = context

            res = self.env.ref('maintenance.hr_equipment_request_view_form', False)
            form_view = [(res and res.id or False, 'form')]
            action['views'] = form_view
            # action['res_id'] = self.id
            action['target'] = 'current'
            return action
        elif values:
            # pprint(values)
            vals = {'name': values['name'],
                    'user_id': values['user_id'],
                    'equipment_id': values['equipment_id'],
                    'type_ot': values['type_ot'],
                    'schedule_date': fields.Datetime.now(),
                    'maintenance_guideline_ids': values.get('maintenance_guideline_ids', [(6, 0, [])]),
                    'create_type': 'ticket'}
            new_ot = self.env['maintenance.request'].sudo().create(vals)
            return new_ot
        else:
            vals = {'name': self.name,
                    'user_id': self.user_id.id,
                    'ticket_id': self.id,
                    'equipment_id': self.equipment_id.id,
                    'type_ot': self.type_ot.id,
                    'schedule_date': self.schedule_date,
                    'create_type': 'ticket'}
            new_ot = self.env['maintenance.request'].sudo().create(vals)
            return new_ot

    @api.model
    def action_create_by_monthly_pdf(self, opc=None):
        data = {
            'model_id': self.id,
            'opc': opc
        }
        return self.env.ref('mblz_mueve.action_report_monthly_tickets_pdf_by_month').report_action(self, data=data)

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        level0 = self.env['helpdesk.support.level'].sudo().search([('name', '=ilike', 'Nivel 0')], limit=1)
        # defaults['user_id'] = self.env.user.id
        if level0:
            defaults.update({
                'support_level_ids': [(6, 0, [level0.id])],
                'ticket_type_id': self.env.ref('helpdesk.type_question').id
                # 'failure_level_id': self.env.ref('__export__.helpdesk_failure_level_4_b9a73272').id
            })
        return defaults

    @api.onchange('ticket_type_id')
    def onchange_ticket_type_id(self):
        if self.ticket_type_id and self.ticket_type_id.priority:
            self.priority = self.ticket_type_id.priority
        else:
            raise ValidationError('Configure la prioridan en el nivel de fallo')
        # if self.ticket_type_id.id == 1:  # ANS Bajo
        #     self.priority = '1'
        # elif self.ticket_type_id.id == 2:  # ANS Medio
        #     self.priority = '1'
        # elif self.ticket_type_id.id == 3:  # ANS Alto
        #     self.priority = '2'
        # elif self.ticket_type_id.id == 4:  # ANS de Emergencia
        #     self.priority = '3'
        # else:
        #     self.priority = '1'

    # ----------------------- REQ: Mesa de Ayuda - Prototipo _ Requerimientos -----------------------
    flag_create_ot_auto = fields.Boolean(string='Crear ot automático', default=True, copy=True)
    nature_type = fields.Selection(
        string='Naturaleza',
        selection=[('corrective', 'Correctivo ITS'),
                   ('preventive', 'Preventivo ITS')],
        required=False, default='preventive')

    @api.onchange('nature_type')
    def onchange_nature_type(self):
        if self.type_ot.maintenance_type != self.nature_type:
            self.type_ot = False

    user_technical_add_ids = fields.Many2many('res.users', string='Técnicos adicionales')

    user_default_id = fields.Many2one('res.users', 'Usuario por defecto', default=lambda self: self.env.user)

    categ_id = fields.Many2one('helpdesk.categ.category', string='Categotización', required=False)
    categ_code = fields.Char(string='Cod. componente', related='categ_id.code')

    element_ids = fields.One2many('helpdesk.categ.element', string='Elementos', compute='_compute_element_ids')

    @api.depends('categ_id')
    def _compute_element_ids(self):
        for rec in self:
            element_ids = [(6, 0, [])]
            if rec.categ_id:
                element_ids = [(6, 0, rec.categ_id.element_ids.mapped('element_id').ids)]
                print(element_ids)
            rec.element_ids = element_ids

    @api.onchange('categ_id')
    def onchange_categ_id(self):
        self.element_id = False

    element_id = fields.Many2one('helpdesk.categ.element', string='Elemento', required=False)
    element_code = fields.Char(string='Cód. elemento', related='element_id.code')
    element_system_id = fields.Many2one('maintenance.system', string='Subsistema', related='element_id.system_id')
    schedule_date = fields.Datetime(string='Fecha prevista', default=fields.Datetime.now())
    priority = fields.Selection(TICKET_PRIORITY, string='Prioridad', default='1', required=True)

    maintenance_guideline_ids = fields.Many2many('maintenance.guideline', string='Pautas', check_company=True)

    create_type = fields.Selection(
        string='Create type',
        selection=[('manual', 'Manual'),
                   ('master', 'Master'),
                   ('other', 'Other')],
        required=True, default='manual')

    # OT Maestra
    tkt_master_id = fields.Many2one('helpdesk.ticket.master', string='TKT Maestro',
                                    ondelete='cascade',
                                    readonly=True)

    closing_comment = fields.Text(string="Solución", required=False)

    msj_dif_dates = fields.Html(string='Mensaje de SLA', compute='_compute_msj_dif_dates')

    @api.depends('sla_deadline')
    def _compute_msj_dif_dates(self):
        for tkt in self:
            msj_dif_dates = False
            if tkt.sla_deadline:
                date_now = fields.Datetime.now() + timedelta(hours=-5)
                diff = relativedelta(tkt.sla_deadline, date_now)
                msj_dif_dates = f'<b>{diff.days} días {diff.hours} horas {diff.minutes} minutos.</b>'
            tkt.msj_dif_dates = msj_dif_dates

    def write(self, values):
        # Add code here
        resp = super(HelpdeskTicket, self).write(values)
        context = self._context
        update_ot_tickt = context.get('update_ot_tickt', False)
        if self.stage_id.is_close and not update_ot_tickt:
            # si la ot no se encuentra cancelada o cerrada no se permite cerrar el ticket
            if self.mtm_request_id and self.mtm_request_id.stage_id.id not in (4, 9):
                raise ValidationError('No se puede cerrar el ticket con una OT asociada pendiente de cierre')
        return resp

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_deadline(self):
        """ Keep the deadline for the last stage (closed one), so a closed ticket can have a status failed.
            Note: a ticket in a closed stage will probably have no deadline
        """
        for ticket in self:
            deadline = False
            # status_not_reached = ticket.sla_status_ids.filtered(
            #     lambda status: not status.reached_datetime and status.deadline)
            # print(status_not_reached)
            #
            # deadline = min(status_not_reached.mapped('deadline')) if status_not_reached else deadline

            # Se anula el método computado de la fecha límite
            if ticket.sla_status_ids:
                sla_menor_days = ticket.sla_status_ids[0].sla_id  # sla con menos días
                for sla in ticket.sla_status_ids:
                    if sla.sla_id.time_days < sla_menor_days.time_days:
                        sla_menor_days = sla
                deadline = fields.Datetime.now() + timedelta(hours=-5)
                deadline = deadline + timedelta(days=sla_menor_days.time_days)
                deadline = deadline + timedelta(hours=sla_menor_days.time_hours)
                deadline = deadline + timedelta(minutes=sla_menor_days.time_minutes)

            ticket.sla_deadline = deadline

    tag_id = fields.Many2one('helpdesk.tag', string='Canal de contacto')

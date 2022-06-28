import logging
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

TICKET_PRIORITY = [
    ('0', 'Todos'),
    ('1', 'Baja'),
    ('2', 'Alta'),
    ('3', 'Urgente'),
]


class HTM(models.Model):
    _name = 'helpdesk.ticket.master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Generación de tickets masivos'
    _check_company_auto = True

    name = fields.Char(string='Nombre', required=True, index=True)
    name_seq = fields.Char(string='SEQ', required=True, copy=False,
                           readonly=True,
                           index=True, default=lambda self: _('New'))

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, readonly=True)
    flag_create_ot_auto = fields.Boolean(string='Crear ot automático', default=True, copy=True)

    user_id = fields.Many2one('res.users', 'Asignado a', required=True)
    domain_user_ids = fields.Many2many('res.users', compute='_compute_domain_user_ids')

    @api.depends('team_id')
    def _compute_domain_user_ids(self):
        for task in self:
            if task.team_id and task.team_id.visibility_member_ids:
                helpdesk_manager = self.env['res.users'].search(
                    [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_manager').id)])
                task.domain_user_ids = [(6, 0, (helpdesk_manager + task.team_id.visibility_member_ids).ids)]
            else:
                helpdesk_users = self.env['res.users'].search(
                    [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)]).ids
                task.domain_user_ids = [(6, 0, helpdesk_users)]

    def _default_team_id(self):
        team_id = self.env['helpdesk.team'].search([('member_ids', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['helpdesk.team'].search([], limit=1).id
        return team_id

    team_id = fields.Many2one('helpdesk.team', string='Equipo de asistencia técnica', default=_default_team_id,
                              index=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Nivel de falla")
    priority = fields.Selection(TICKET_PRIORITY, string='Prioridad', default='1', required=True)

    partner_id = fields.Many2one('res.partner', string='Cliente')
    partner_name = fields.Char(string='Nombre del cliente', compute='_compute_partner_name', store=True, readonly=False)
    partner_email = fields.Char(string='Correo electrónico del cliente', compute='_compute_partner_email', store=True,
                                readonly=False)

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_name = ticket.partner_id.name

    @api.depends('partner_id')
    def _compute_partner_email(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_email = ticket.partner_id.email

    # Nivel de soport
    support_level_ids = fields.Many2many('helpdesk.support.level', string='Niveles de soporte')
    # place_of_care = fields.Char(string='Lugar de atención', required=False, help="Barrio")

    support_activity_ids = fields.Many2many('maintenance.guideline.activity',
                                            compute='_compute_support_activity_ids',
                                            string='Actividades')

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

    state = fields.Selection(
        string='State',
        selection=[('draft', 'Borrador'),
                   ('progress', 'Progreso'),
                   ('done', 'Terminado')],
        readonly=True, default='draft')

    equipment_ids = fields.Many2many(
        'maintenance.equipment',
        ondelete='cascade',
        required=True,
        string='Equipments', check_company=True)

    guideline_ids = fields.Many2many(
        'maintenance.guideline',
        required=True,
        ondelete='cascade',
        string='Guidelines', check_company=True)

    # guideline_ids = fields.Many2many(
    #     'maintenance.guideline',
    #     required=True,
    #     ondelete='cascade',
    #     string='Guidelines', check_company=True)

    ticket_ids = fields.One2many(
        'helpdesk.ticket',
        'tkt_master_id',
        string='Tickets',
        required=False, copy=False,
        auto_join=True)

    description = fields.Html(string='Description', required=False)

    nature_type = fields.Selection(
        string='Naturaleza',
        selection=[('corrective', 'Correctivo ITS'),
                   ('preventive', 'Preventivo ITS')],
        required=False, default='preventive')

    flag_complete_close = fields.Boolean(
        string="Todos las ot's cerradas",
        compute='_compute_flag_complete_close')

    flag_complete_tkt_close = fields.Boolean(
        string="Todos las tkt's cerradas",
        compute='_compute_flag_complete_close')

    @api.depends('ticket_ids')
    def _compute_flag_complete_close(self):
        for rec in self:
            # id = 3 -> Resuelto
            rec.flag_complete_close = len(
                rec.ticket_ids.mapped('mtm_request_id').filtered_domain([('stage_id', '!=', 9)])) > 0
            rec.flag_complete_tkt_close = len(rec.ticket_ids.filtered(lambda l: l.stage_id.id != 3)) > 0

    # @api.onchange('maintenance_type')
    # def onchange_maintenance_type(self):
    #     self.guideline_ids = [(6, 0, [])]

    type_ot = fields.Many2one('maintenance.request.type',
                              string='Tipo de OT', required=True)
    # schedule_date = fields.Datetime('Fecha prevista',
    #                                 help="Fecha en la que el equipo de mantenimiento planifica el mantenimiento. No debe diferir mucho de la fecha de solicitud.")
    user_technical_add_ids = fields.Many2many('res.users', string='Técnicos adicionales')

    categ_id = fields.Many2one('helpdesk.categ.category', string='Categotización', required=False)
    categ_code = fields.Char(string='Cod. componente', related='categ_id.code')

    element_ids = fields.One2many('helpdesk.categ.element', string='Elementos', compute='_compute_element_ids')

    @api.depends('categ_id')
    def _compute_element_ids(self):
        for rec in self:
            element_ids = [(6, 0, [])]
            if rec.categ_id:
                element_ids = [(6, 0, rec.categ_id.element_ids.mapped('element_id').ids)]
                # print(element_ids)
            rec.element_ids = element_ids

    element_id = fields.Many2one('helpdesk.categ.element', string='Elemento', required=False)
    element_code = fields.Char(string='Cód. elemento', related='element_id.code')
    element_system_id = fields.Many2one('maintenance.system', string='Subsistema', related='element_id.system_id')
    user_default_id = fields.Many2one('res.users', 'Usuario por defecto', default=lambda self: self.env.user)

    # def _valid_guideline_ids(self, equipment, guideline_ids):
    #     OBJ_TK = self.env['maintenance.request'].sudo()
    #     for guideline in guideline_ids:
    #         resp = OBJ_TK.valid_create(equipment, guideline, opc=True)
    #         print(f'result valid guideline {guideline.name} for {equipment.name}: {resp}')

    def action_create_tickets(self):
        if not self.ticket_ids:
            OBJ_TK = self.env['helpdesk.ticket'].sudo()
            for index, equipment in enumerate(self.equipment_ids):
                # self._valid_guideline_ids(equipment, self.guideline_ids)
                # if guideline_ids and len(guideline_ids) > 0:
                tkt_data = {
                    'name': f'TKT{index + 1} - {equipment.name}',
                    'flag_create_ot_auto': self.flag_create_ot_auto,
                    'tkt_master_id': self.id,
                    'team_id': self.team_id.id,
                    'user_id': self.user_id.id,
                    'ticket_type_id': self.ticket_type_id.id,
                    'priority': self.priority,
                    'nature_type': self.nature_type,
                    'type_ot': self.type_ot.id,
                    'equipment_id': equipment.id,
                    'partner_id': self.partner_id.id,
                    'support_activity_ids': [(6, 0, self.support_activity_ids.ids)],
                    # 'place_of_care': self.place_of_care,
                    'categ_id': self.categ_id.id,
                    'element_id': self.element_id.id,
                    'description': self.env['ir.fields.converter'].text_from_html(self.description),

                    # 'flag_from_otm': True,
                    'create_type': 'master',
                    'company_id': self.company_id.id,
                    # 'schedule_date': self.schedule_date,
                    'tag_id': self.tag_id.id,
                    'maintenance_guideline_ids': [(6, 0, self.guideline_ids.ids)]
                }
                tkt_new = OBJ_TK.create(tkt_data)

                _logger.info(f'New Request -->>> {tkt_new.name_seq}')
            # else:
            #         raise ValidationError(_('Guidelines have already been executed for the busses entered!'))
            if len(self.ticket_ids) > 0:
                self.state = 'progress'
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Tickets masivos creados correctamente',
                'type': 'rainbow_man',
            }
        }

    @api.model
    def create(self, values):
        # Add code here
        if values.get('name_seq', _('New')) == _('New'):
            name_seq = self.env['ir.sequence'].next_by_code('tkt.master.sequence')
            values.update(dict(name_seq=name_seq))
        return super(HTM, self).create(values)

    # flag warning
    flag_ot_ok = fields.Boolean(compute='_compute_flag_ot_ok')

    @api.depends('ticket_ids')
    def _compute_flag_ot_ok(self):
        for otm in self:
            otm.flag_ot_ok = False
            if otm.ticket_ids:
                ots = otm.ticket_ids.filtered(lambda r: not (r.type_ot or r.schedule_date))
                if not ots:
                    otm.flag_ot_ok = True

    flag_request_completed = fields.Boolean(compute='_compute_flag_request_completed')
    tag_id = fields.Many2one('helpdesk.tag', string='Canal de contacto')

    @api.depends('ticket_ids')
    def _compute_flag_request_completed(self):
        for rec in self:
            flag_request_completed = True
            if rec.ticket_ids:
                requests = rec.ticket_ids.filtered(lambda r: not r.stage_id.is_close)
                if requests:
                    flag_request_completed = False
            rec.flag_request_completed = flag_request_completed

    def action_done(self):
        self.ensure_one()
        if not self.flag_request_completed:
            raise ValidationError(_('Hay tickets que no han sido completados.'))
        self.sudo().state = 'done'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        # message = {
        #     'type': 'ir.actions.client',
        #     'tag': 'reload',
        #     'params': {
        #         'title': _('Information'),
        #         'message': _(f'master work {self.name} order completed'),
        #         'sticky': False,
        #     }
        # }
        # return message

    @api.onchange('ticket_type_id')
    def onchange_ticket_type_id(self):
        if self.ticket_type_id and self.ticket_type_id.priority:
            self.priority = self.ticket_type_id.priority
        else:
            raise ValidationError('Configure la prioridan en el nivel fallo!')
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

    def action_close_all_request(self):
        view = self.env.ref('mblz_mueve.view_close_tkt_massive_wizard', False)
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['default_tkt_master_id'] = self.id
        return {
            'name': _("Cierre masivo de ordenes de trabajo"),
            'type': 'ir.actions.act_window',
            'res_model': 'close.tkt.massive',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def action_close_all_tickets(self):
        view = self.env.ref('mblz_mueve.view_close_aux_massive_wizard', False)
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['default_tkt_master_id'] = self.id
        return {
            'name': _("Cierre masivo de tickets"),
            'type': 'ir.actions.act_window',
            'res_model': 'close.tkt.massive.aux',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    # @api.model
    # def action_close_all_request2(self, selected_ids):
    #     view = self.env.ref('l10n_cl_maintenance.view_close_ots_massive_wizard', False)
    #     view_id = view and view.id or False
    #
    #     otm_sudo = self.env['maintenance.request'].sudo()
    #     ot_lines = otm_sudo.browse(selected_ids)
    #
    #     context = dict(self._context or {})
    #     context['default_ot_master_id'] = 18
    #     context['default_select_all_request'] = [(6, 0, ot_lines.ids)]
    #     return {
    #         'name': _("Close Massive OT's"),
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'close.ots.massive',
    #         'view_mode': 'form',
    #         'views': [(view_id, 'form')],
    #         'view_id': view_id,
    #         'target': 'new',
    #         'context': context,
    #     }

    @api.model
    def default_get(self, field_list):
        resp = super(HTM, self).default_get(field_list)
        resp.update({
            'categ_id': self.env.ref('mblz_mueve.helpdesk_categ_categpry_discentral').id,
            'element_id': self.env.ref('mblz_mueve.tkt_categ_elemt_0024').id,
            'ticket_type_id': self.env.ref('helpdesk.type_question').id
        })
        return resp

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        try:
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
        except ValueError:
            default['name'] = _("%s (copy)") % (self.name or '')
        return super(HTM, self).copy(default)

    refresh_alert_otm = fields.Boolean(string='Actualizar alerta ots', compute='_compute_refresh_alert_otm')

    # @api.depends('')
    def _compute_refresh_alert_otm(self):
        for tkm in self:
            if tkm.state != 'done':
                tkm._update_alert(tkm.ticket_ids)
            tkm.refresh_alert_otm = True

    def _update_alert(self, ticket_ids):
        for tkt in ticket_ids:
            ot = tkt.mtm_request_id
            tasks = ot.task_ids.filtered(lambda l: l.stage_id.id == 1)
            alert_otm = False
            for task in tasks:
                # todo:// uso la lista de materiales el modulo l10n_cl_mrp_maintenance
                pickings_stage = task.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))

                # todo:// solicitudes de aprobación que esten pendientes
                approvals_satge = task.approval_ids.filtered(
                    lambda r: r.request_status not in ('approved', 'refused', 'cancel'))

                if len(pickings_stage) > 0:
                    alert_otm = 'pickings'

                if len(approvals_satge) > 0:
                    alert_otm = 'approve_ma'
                if not task.employee_id:
                    alert_otm = 'no-employee'
            ot.sudo().alert_otm = alert_otm
            if len(tasks) == 0:
                ot.sudo().alert_otm = False

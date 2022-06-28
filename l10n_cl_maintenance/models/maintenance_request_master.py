import logging
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MaintenanceRequestMaster(models.Model):
    _name = 'maintenance.request.master'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _description = 'Maintenance Request Master '
    _check_company_auto = True

    name = fields.Char(string='OT Reference', required=True, copy=False,
                       readonly=True,
                       index=True, default=lambda self: _('New'))

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)

    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('progress', 'Progress'),
                   ('done', 'Done'),
                   ],
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

    request_ids = fields.One2many(
        'maintenance.request',
        'ot_master_id',
        string='Requests',
        required=False, copy=False,
        auto_join=True)

    description = fields.Html(string='Description', required=False)

    maintenance_type = fields.Selection(
        string='Nature',
        selection=[('preventive', 'Preventive'),
                   ('corrective', 'Corrective')],
        required=True, default='preventive')

    flag_complete_close = fields.Boolean(
        string="Toda las ot's cerradas",
        compute='_compute_flag_complete_close')

    request_done_count = fields.Integer('Cant. cerradas', compute='_compute_ot_done_count',
                                        help="Número de ot's cerradas")

    @api.depends('request_ids')
    def _compute_ot_done_count(self):
        for rec in self:
            request_done_count = 0
            if rec.request_ids:
                tasks_done = rec.request_ids.filtered(lambda l: l.stage_id.id == 9)
                if tasks_done:
                    request_done_count = len(tasks_done)

            rec.sudo().request_done_count = request_done_count

    request_done_percent = fields.Float('Avance(%)', compute='_compute_request_done_count',
                                        help='Porcentaje sobre las Ordenes de trabajo cerradas')
    count_request = fields.Integer(
        string='Count OTs',
        compute='_compute_request_done_count')

    @api.depends('request_ids', 'request_done_count')
    def _compute_request_done_count(self):
        for rec in self:
            request_done_percent = 0
            count_request = 0
            if rec.request_ids:
                count_request = len(rec.request_ids)
                value = (rec.request_done_count / count_request) * 100
                request_done_percent = value
            rec.sudo().count_request = count_request
            rec.sudo().request_done_percent = request_done_percent

    @api.depends('request_ids')
    def _compute_flag_complete_close(self):
        for rec in self:
            rec.flag_complete_close = len(rec.request_ids.filtered(lambda l: l.stage_id.id != 9)) > 0  # 9= Cerrada

    @api.onchange('maintenance_type')
    def onchange_maintenance_type(self):
        self.guideline_ids = [(6, 0, [])]

    type_ot = fields.Many2one('maintenance.request.type',
                              string='Type OT', required=True)
    schedule_date = fields.Datetime('Scheduled Date',
                                    help="Date the maintenance team plans the maintenance. It should not differ much from the Request Date. ")

    def _valid_guideline_ids(self, equipment, guideline_ids):
        obj_maintenance_request = self.env['maintenance.request'].sudo()
        for guideline in guideline_ids:
            resp = obj_maintenance_request.valid_create(equipment, guideline, opc=True)
            print(f'result valid guideline {guideline.name} for {equipment.name}: {resp}')

    def action_create_requests(self):
        if not self.request_ids:
            obj_maintenance_request = self.env['maintenance.request'].sudo()
            for index, equipment in enumerate(self.equipment_ids):
                self._valid_guideline_ids(equipment, self.guideline_ids)
                # if guideline_ids and len(guideline_ids) > 0:
                ot_data = {
                    'name': f'OT{index + 1} - {equipment.name}',
                    'ot_master_id': self.id,
                    'equipment_id': equipment.id,
                    'flag_from_otm': True,
                    'create_type': 'master',
                    'company_id': self.company_id.id,
                    'user_id': self.user_id.id,
                    'type_ot': self.type_ot.id,
                    'schedule_date': self.schedule_date,
                    'maintenance_guideline_ids': [(6, 0, self.guideline_ids.ids)]
                }
                request_new = obj_maintenance_request.create(ot_data)

                _logger.info(f'New Request -->>> {request_new.name_seq}')
            # else:
            #         raise ValidationError(_('Guidelines have already been executed for the busses entered!'))
            if len(self.request_ids) > 0:
                self.state = 'progress'
        # return {
        #     'effect': {
        #         'fadeout': 'slow',
        #         'message': 'OT Master created... Thanks You',
        #         'type': 'rainbow_man',
        #     }
        # }

    @api.model
    def create(self, values):
        # Add code here
        if values.get('name', _('New')) == _('New'):
            name = self.env['ir.sequence'].next_by_code('ot.master.sequence')
            values.update(dict(name=name))
        return super(MaintenanceRequestMaster, self).create(values)

    # flag warning
    flag_ot_ok = fields.Boolean(compute='_compute_flag_ot_ok')

    @api.depends('request_ids')
    def _compute_flag_ot_ok(self):
        for otm in self:
            otm.flag_ot_ok = False
            if otm.request_ids:
                ots = otm.request_ids.filtered(lambda r: not (r.type_ot or r.schedule_date))
                if not ots:
                    otm.flag_ot_ok = True

    def action_dev(self):
        OBJ_MR = self.env['maintenance.request'].sudo()
        request_ids = OBJ_MR.search([('company_id', '=', self.env.company.id)], order='id asc')
        for request in request_ids:
            request.name_seq = self.env['ir.sequence'].next_by_code('mt.sequence')

    flag_request_completed = fields.Boolean(compute='_compute_flag_request_completed')

    @api.depends('request_ids')
    def _compute_flag_request_completed(self):
        for rec in self:
            flag_request_completed = True
            if rec.request_ids:
                requests = rec.request_ids.filtered(lambda r: not r.stage_id.done)
                if requests:
                    flag_request_completed = False
            rec.flag_request_completed = flag_request_completed

    def action_done(self):
        if not self.flag_request_completed:
            raise ValidationError(_('There are TOs that have not been completed'))
        self.state = 'done'
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        # message = {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': _('Information'),
        #         'message': _(f'master work {self.name} order completed'),
        #         'sticky': False,
        #     }
        # }
        # return message

    def action_close_all_request(self):
        view = self.env.ref('l10n_cl_maintenance.view_close_ots_massive_wizard', False)
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['default_ot_master_id'] = self.id
        return {
            'name': _("Cierre masivo de OT's o Tareas"),
            'type': 'ir.actions.act_window',
            'res_model': 'close.ots.massive',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    @api.model
    def action_close_all_request2(self, selected_ids):
        view = self.env.ref('l10n_cl_maintenance.view_close_ots_massive_wizard', False)
        view_id = view and view.id or False

        otm_sudo = self.env['maintenance.request'].sudo()
        ot_lines = otm_sudo.browse(selected_ids)

        context = dict(self._context or {})
        context['default_ot_master_id'] = 18
        context['default_select_all_request'] = [(6, 0, ot_lines.ids)]
        return {
            'name': _("Close Massive OT's"),
            'type': 'ir.actions.act_window',
            'res_model': 'close.ots.massive',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    refresh_alert_otm = fields.Boolean(string='Actualizar alerta ots', compute='_compute_refresh_alert_otm')

    # @api.depends('')
    def _compute_refresh_alert_otm(self):
        for otm in self:
            if otm.state != 'done':
                otm._update_alert(otm.request_ids)
            otm.refresh_alert_otm = True

    def _update_alert(self, request_ids):
        for ot in request_ids:
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

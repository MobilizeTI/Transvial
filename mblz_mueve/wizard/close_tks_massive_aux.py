# -*- coding: utf-8 -*-
import json

from odoo import api, models, tools, fields, _

import logging
import threading

from odoo.exceptions import ValidationError, Warning

_logger = logging.getLogger(__name__)


class CloseTKTMassive(models.TransientModel):
    _name = 'close.tkt.massive.aux'
    _description = 'Cierre de tickets sin ordenes de trabajo asociadas'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    closing_comment = fields.Text(string="Comentario", required=False)
    # TKT Maestra
    tkt_master_id = fields.Many2one('helpdesk.ticket.master', string='TKT Master',
                                    ondelete='cascade',
                                    required=False)

    select_all_ticket = fields.Many2many('helpdesk.ticket', string="Select TKT's")

    def _get_tickts(self, tkt_master):
        ticket_ids = self.env['helpdesk.ticket'].sudo().search([
            ('tkt_master_id', '=', tkt_master.id),
            ('stage_id', '!=', 3),
        ])
        return ticket_ids.ids

    @api.onchange('tkt_master_id')
    def onchange_tkt_master_id(self):
        for rec in self:
            ticket_ids = rec.env['helpdesk.ticket'].sudo().search([
                ('tkt_master_id', '=', rec.tkt_master_id.id),
                ('stage_id', '!=', 3),
            ])
            return {'domain': {'select_all_ticket': [('id', 'in', ticket_ids.ids)]}}

    option_tickets = fields.Selection(
        string='Seleccione',
        selection=[('one', "Ticket"), ('custom', "Tickets"), ('all', 'Todos')],
        required=False, default='all')

    tkt_select_id = fields.Many2one('helpdesk.ticket', string="Ticket", required=False)
    tkt_select_ids = fields.Many2many('helpdesk.ticket',
                                      'wz_close_tickts_massive_rel',
                                      'wz_tkt_select_id', 'request_id',
                                      string="Tickets")

    def action_close_tkt(self):
        # self.ensure_one()
        if self.option_tickets == 'one':
            self.tkt_select_id.sudo().write({
                'stage_id': 3,
                'closing_comment': self.closing_comment
            })
        elif self.option_tickets == 'custom':
            for ticket in self.tkt_select_ids:
                ticket.sudo().write({
                    'stage_id': 3,
                    'closing_comment': self.closing_comment
                })
        else:
            tickets = self.tkt_master_id.ticket_ids.filtered_domain([('stage_id', '!=', 3)])
            for ticket in tickets:
                ticket.sudo().write({
                    'stage_id': 3,
                    'closing_comment': self.closing_comment
                })


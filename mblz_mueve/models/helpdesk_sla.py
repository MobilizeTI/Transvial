# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import models, fields, api, _


# TICKET_PRIORITY = [
#     ('0', 'Todas'),
#     ('1', 'Baja'),
#     ('4', 'Medía'),
#     ('2', 'Alta'),
#     ('3', 'Urgente'),
# ]


class SLA(models.Model):
    _inherit = 'helpdesk.sla'

    # priority = fields.Selection(selection_add=[('4', 'DHL')])
    # priority = fields.Selection(
    #     TICKET_PRIORITY, string='Minimum Priority',
    #     default='1', required=True,
    #     help='Tickets under this priority will not be taken into account.')
    # Nivel de falla
    failure_level_id = fields.Many2one('helpdesk.failure.level', string='Failure Level', required=True)
    time_response = fields.Float(string='Tiempo de respuesta', required=True)

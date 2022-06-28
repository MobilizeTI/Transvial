import logging

from odoo import fields, api, models
from odoo.exceptions import ValidationError
from datetime import timedelta

_logger = logging.getLogger(__name__)


class StageSolutionWizard(models.TransientModel):
    _name = 'stage.solution.wizard'
    _description = "Stage solution Wizard"

    stage_id = fields.Many2one('maintenance.stage', string='Stage')
    request_id = fields.Many2one('maintenance.request', string='OT')

    msj_solution_close = fields.Text(string="Solución", required=True,
                                     help='Mensaje de solución de cierre de de OT para el ticket')

    def action_confirm(self):
        self.ensure_one()
        if self.request_id:
            self.request_id.sudo().write({
                'stage_id': self.stage_id.id,
                'msj_solution_close': self.msj_solution_close,
                'close_datetime': fields.datetime.now()
            })
            _logger.info(
                f'>>> ot: {self.request_id.id}, {self.request_id.name_seq}, {self.request_id.name}, stage: {self.request_id.stage_id.name}')
        else:
            raise ValidationError("Internal error contact the support area")

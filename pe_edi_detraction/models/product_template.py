# -*- coding: utf-8 -*-
from odoo import models, fields, api


class TableOptionDetraction(models.Model):
    _name = 'table.option.detraction'
    _description = 'TABLA ANEXO IV: Catálogo número 54.'
    _order = 'code'
    _rec_name = 'description'

    code = fields.Char(string=u'Código', required=True)
    description = fields.Char(string='Descripción', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda i: i.env.ref('base.PEN'))
    amount_min = fields.Monetary(string='Monto mínimo s/.')
    percentage = fields.Float(string='Porcentaje')
    comment = fields.Text(string='Comentario')
    active = fields.Boolean(default=True, string='Activo')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Detracción
    is_affect_detraction = fields.Boolean(string='¿Afecto a detracción?')
    option_detraction_id = fields.Many2one(
        'table.option.detraction',
        string='Bien o servicio',
        help="Número de catálogo 54 SUNAT, utilizado funcionalmente para documentar en el documento impreso en las "
             "facturas que necesitan tener el texto SPOT adecuado")
    amount_min_detraction = fields.Monetary(related='option_detraction_id.amount_min',
                                            string='Aplica mayor a')
    percentage_detraction = fields.Float(
        related='option_detraction_id.percentage',
        string='Porcentaje aplicado',
        help="Porcentajes de detracción informados en el Anexo I Resolución 183-2004/SUNAT, depende del código de "
             "Retención pero hay que leer la resolución")

    @api.onchange('is_affect_detraction')
    def onchange_is_affect_detraction(self):
        if not self.is_affect_detraction:
            self.option_detraction_id = False
            self.l10n_pe_withhold_code = False
            self.l10n_pe_withhold_percentage = 0.0

    @api.onchange('option_detraction_id')
    def onchange_option_detraction_id(self):
        if self.option_detraction_id:
            self.l10n_pe_withhold_code = self.option_detraction_id.code
            self.l10n_pe_withhold_percentage = self.option_detraction_id.percentage
        else:
            self.l10n_pe_withhold_code = False
            self.l10n_pe_withhold_percentage = 0.0

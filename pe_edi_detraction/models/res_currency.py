# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from datetime import datetime, timedelta
import requests
import bs4
import pytz

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, ValidationError, Warning


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def validate_rate(self, date):
        """Válida que exista ta tasa de tipo de cambio para la fecha"""
        if self.symbol != 'S/':
            rcr_date = self.env['res.currency.rate'].sudo().search([
                ('name', '=', date),
                ('currency_id', '=', self.id),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            if not rcr_date:
                raise ValidationError(
                    f'No existe el tipo de cambio {self.name} para la fecha {date}, compañía {self.env.company.name}')

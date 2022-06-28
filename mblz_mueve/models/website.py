# -*- coding: utf-8 -*-
import datetime

import pytz

from odoo import models, fields, api, SUPERUSER_ID
from odoo.addons.http_routing.models.ir_http import slug
from odoo.http import request


class Website(models.Model):
    _inherit = 'website'

    def get_failure_levels(self):
        failure_levels = self.env['helpdesk.ticket.type'].sudo().search([])
        data = [{
            'id': '0',
            'name': 'Todos',
        }]
        for failure in failure_levels:
            data.append({
                'id': failure.id,
                'name': failure.name,
            })
        return data

    def get_months(self):
        date = fields.Datetime.now()
        month_actual = date.month
        months = [('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'), ('4', 'Abril'), ('5', 'Mayo'),
                  ('6', 'Junio'), ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Setiembre'), ('10', 'Octubre'),
                  ('11', 'Noviembre'), ('12', 'Diciembre')]
        data = []
        for m in months:
            item = {'id': m[0], 'name': m[1], 'selected': False}
            if int(m[0]) == month_actual:
                item.update({'selected': True})
            data.append(item)
        return data

    def get_years(self):
        date = fields.Datetime.now()
        year_actual = date.year
        data = []
        for y in range(2022, year_actual + 1):
            item = {'id': y, 'name': str(y), 'selected': False}
            if y == year_actual:
                item.update({'selected': True})
            data.append(item)

        return data

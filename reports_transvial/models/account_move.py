# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import base64
from lxml import etree
from num2words import num2words

from odoo import api, fields, models, _
from odoo.tools.float_utils import float_repr, float_round
from odoo.exceptions import UserError


class AM(models.Model):
    _inherit = 'account.move'

    @api.model
    def amount_to_text(self, amount, currency_id):
        self.ensure_one()
        amount_i, amount_d = divmod(amount, 1)
        amount_d = int(round(amount_d * 100, 2))
        words = num2words(amount_i, lang='es')
        result = '%(words)s Y %(amount_d)02d/100 %(currency_name)s' % {
            'words': words,
            'amount_d': amount_d,
            'currency_name': currency_id.currency_unit_label,
        }
        return result.upper()

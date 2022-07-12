# -*- coding: utf-8 -*-

import re
from odoo import fields, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    required_serie = fields.Boolean(string='Utilizan serie', required=False)

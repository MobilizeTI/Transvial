# -*- coding: utf-8 -*-

import re
from odoo import fields, api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type',
                                                  string='Tipo de Documento',
                                                  domain=[('code', 'in', ('01', '03'))], required=False,
                                                  copy=False)
    edi_series_ids = fields.Many2many('edi.invoice.series', string='Series', check_company=True)

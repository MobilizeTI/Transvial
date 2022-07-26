# -*- coding: utf-8 -*-

import pprint
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby

from num2words import num2words
from odoo.tools import float_is_zero, float_compare, safe_eval, date_utils, email_split, email_escape_char, email_re

from datetime import date, timedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools.misc import formatLang, format_date, get_lang
from lxml import etree

import base64
import datetime
import pytz
import logging
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, format_date

_logger = logging.getLogger(__name__)


class AM(models.Model):
    _inherit = 'account.move'

    edi_series_id = fields.Many2one('edi.invoice.series', 'Serie')
    journal_edi_series_ids = fields.Many2many('edi.invoice.series', related='journal_id.edi_series_ids')

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        for record in self:
            if record.state == 'draft':
                record.name = '/'
            elif record.state == 'posted':
                sequence = record._get_sequence()
                if sequence:
                    record.name = sequence.next_by_id()
                else:
                    super(AM, record)._compute_name()

    def _get_sequence(self):
        sequence = self.edi_series_id.invoice_seq_id
        if self.l10n_latam_document_type_id.code == '07':
            sequence = self.edi_series_id.credit_note_seq_id
        elif self.l10n_latam_document_type_id.code == '08':
            sequence = self.edi_series_id.debit_note_seq_id
        return sequence

    @api.onchange('l10n_latam_document_number')
    def onchange_l10n_latam_document_number(self):
        if self.l10n_latam_document_number:
            self.ref = self.l10n_latam_document_number
        else:
            self.ref = False
        # self._action_reload_upd()

    @api.onchange('l10n_latam_document_type_id')
    def onchange_l10n_latam_document_type_id(self):
        if self.l10n_latam_document_type_id and \
                self.edi_series_id.l10n_latam_document_type_id.id != self.l10n_latam_document_type_id.id:
            self.edi_series_id = False
        else:
            self.edi_series_id = False
        # self._action_reload_upd()

    @api.model
    def default_get(self, fields_list):
        res = super(AM, self).default_get(fields_list)
        journal_id = self.env['account.journal'].browse(res.get('journal_id', False))
        if journal_id:
            res.update(dict(
                l10n_latam_document_type_id=journal_id.l10n_latam_document_type_id.id,
                # edi_series_id=journal_id.edi_series_id.id,
            ))
        return res

    def action_post(self):
        # se añade el apunte contable de la detracción (solo a facturas de proveedor)
        resp = super(AM, self).action_post()
        if self.edi_series_id:
            self._update_line_ids()
        return resp

    def _update_line_ids(self):
        for record in self.line_ids:
            try:
                serie_entry = record.move_id.name.split('-')[0]
                document_entry = record.move_id.name.split('-')[1]
            except Exception as e:
                _logger.error(str(e))
                serie_entry = False
                document_entry = False

            record.write({
                'code_type_document_entry': record.move_id.l10n_latam_document_type_id.code,
                'serie_entry': serie_entry,
                'document_entry': document_entry,
            })


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # @api.onchange('move_id', 'move_id.edi_series_id', 'move_id.l10n_latam_document_type_id')
    # def onchange_move_id(self):
    #     self.update({
    #         'edi_series_id': self.move_id.edi_series_id.id,
    #         'l10n_latam_document_type_code': self.move_id.l10n_latam_document_type_id.code
    #     })

    # ---------------- Campos a Asientos Contables ------------------- (inicio)
    # Tabla código libro 08
    code_book_sunat_id = fields.Many2one(
        comodel_name='pe_code_book_table_08',
        string='Código libro',
        help='Tabla 8: Código del libro o registro')
    voucher_entry = fields.Char(string='Voucher', required=False)
    code_type_document_entry = fields.Char(string='T/Documento', required=False)
    serie_entry = fields.Char(string='Serie', required=False)
    document_entry = fields.Char(string='Documento', required=False)

    # ---------------- Campos a Asientos Contables ------------------- (fin)

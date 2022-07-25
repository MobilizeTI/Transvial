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
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, format_date

TABLE_08 = [
    ('1 ', 'LIBRO CAJA Y BANCOS'),
    ('2 ', 'LIBRO DE INGRESOS Y GASTOS'),
    ('3 ', 'LIBRO DE INVENTARIOS Y BALANCES'),
    ('4 ', 'LEY DEL IMPUESTO A LA RENTA'),
    ('5 ', 'LIBRO DIARIO'),
    ('6 ', 'LIBRO MAYOR'),
    ('7 ', 'REGISTRO DE ACTIVOS FIJOS'),
    ('8 ', 'REGISTRO DE COMPRAS'),
    ('9 ', 'REGISTRO DE CONSIGNACIONES'),
    ('10', 'REGISTRO DE COSTOS'),
    ('11', 'REGISTRO DE HUÉSPEDES'),
    ('12', 'REGISTRO DE INVENTARIO PERMANENTE EN UNIDADES FÍSICAS'),
    ('13', 'REGISTRO DE INVENTARIO PERMANENTE VALORIZADO'),
    ('14', 'REGISTRO DE VENTAS E INGRESOS'),
    ('15', 'REGISTRO DE VENTAS E INGRESOS - ARTÍCULO 23° RESOLUCIÓN DE SUPERINTENDENCIA N° 266-2004/SUNAT'),
    ('16', 'REGISTRO DEL RÉGIMEN DE PERCEPCIONES'),
    ('17', 'REGISTRO DEL RÉGIMEN DE RETENCIONES'),
    ('18', 'REGISTRO IVAP'),
    ('19', 'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - ARTÍCULO 8° RESOLUCIÓN DE SUPERINTENDENCIA N° 022-98/SUNAT'),
    ('20',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 021-99/SUNAT'),
    ('21',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 142-2001/SUNAT'),
    ('22',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 256-2004/SUNAT'),
    ('23',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 257-2004/SUNAT'),
    ('24',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO C) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 258-2004/SUNAT'),
    ('25',
     'REGISTRO(S) AUXILIAR(ES) DE ADQUISICIONES - INCISO A) PRIMER PÁRRAFO ARTÍCULO 5° RESOLUCIÓN DE SUPERINTENDENCIA N° 259-2004/SUNAT'),
    ('26', 'REGISTRO DE RETENCIONES ARTÍCULO 77-A DE LA LEY DEL IMPUESTO A LA RENTA'),
    ('27', 'LIBRO DE ACTAS DE LA EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA'),
    ('28', 'LIBRO DE ACTAS DE LA JUNTA GENERAL DE ACCIONISTAS'),
    ('29', 'LIBRO DE ACTAS DEL DIRECTORIO'),
    ('30', 'LIBRO DE MATRÍCULA DE ACCIONES'),
    ('31', 'LIBRO DE PLANILLA'), ]


class AM(models.Model):
    _inherit = 'account.move'

    edi_series_id = fields.Many2one('edi.invoice.series', 'Serie')
    journal_edi_series_ids = fields.Many2many('edi.invoice.series', related='journal_id.edi_series_ids')

    @api.depends('posted_before', 'state', 'journal_id', 'date')
    def _compute_name(self):
        if self.state == 'draft':
            self.name = '/'
        elif self.state == 'posted':
            sequence = self._get_sequence()
            if sequence:
                self.name = sequence.next_by_id()
            else:
                super(AM, self)._compute_name()

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
    #
    # def _action_reload_upd(self):
    #     for line in self.line_ids:
    #         line.onchange_move_id()


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
    code_book_sunat = fields.Selection(string='Código de libro',
                                       selection=TABLE_08,
                                       required=False,
                                       help='Tabla 8: Código del libro o registro')
    voucher_entry = fields.Char(string='Voucher', required=False)
    code_type_document_entry = fields.Char(string='T/Documento', required=False)
    serie_entry = fields.Char(string='Serie', required=False)
    document_entry = fields.Char(string='Documento', required=False)

    # ---------------- Campos a Asientos Contables ------------------- (fin)

    # edi_series_id = fields.Many2one(comodel_name='edi.invoice.series',
    #                                 string='Serie', related='move_id.edi_series_id')
    #
    # l10n_latam_document_type_code = fields.Char(string="Código TD",
    #                                             related='move_id.l10n_latam_document_type_id.code',
    #                                             help='Código tipo documento utilizado por las diferentes '
    #                                                  'localizaciones')

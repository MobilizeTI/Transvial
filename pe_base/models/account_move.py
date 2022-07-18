# -*- coding: utf-8 -*-

import re
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError

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


class AccountMove(models.Model):
    _inherit = 'account.move'

    name_seq_system = fields.Char(
        'Correlativo', copy=False, readonly=True, default=lambda x: _('/'),
        help='Correlativo del sistema para facturas de proveedor')

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Número de serie',
                                       required=False)
    required_serie = fields.Boolean(string='Utilizan serie', related='journal_id.required_serie')

    # ---------------- Campos a Asientos Contables ------------------- (inicio)
    # Tabla código libro 08
    # code_book_sunat = fields.Selection(string='Código de libro',
    #                                    selection=TABLE_08,
    #                                    required=False,
    #                                    help='Tabla 8: Código del libro o registro')
    # voucher_entry = fields.Char(string='Voucher', required=False)
    # type_document_entry = fields.Char(string='T/Documento', required=False)
    # serie_entry = fields.Char(string='Serie', required=False)
    # document_entry = fields.Char(string='Documento', required=False)

    # ---------------- Campos a Asientos Contables ------------------- (fin)

    @api.model
    def create(self, values):
        move_new = super(AccountMove, self).create(values)
        if move_new.move_type == 'in_invoice' and move_new.name_seq_system == '/':
            move_new.name_seq_system = self.env['ir.sequence'].next_by_code('seq.supplier.invoice') or _('/')
        elif move_new.move_type == 'out_invoice' and move_new.name_seq_system == '/':
            move_new.name_seq_system = self.env['ir.sequence'].next_by_code('seq.customer.invoice') or _('/')
        return move_new


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    invoice_serie_id = fields.Many2one(comodel_name='invoice.series',
                                       string='Serie',
                                       related='move_id.invoice_serie_id', store=True)

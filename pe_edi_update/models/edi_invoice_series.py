import re
from odoo import fields, api, models
from odoo.exceptions import ValidationError

CPE_01_REGEX = re.compile('^(F)[A-Z0-9]{3}$')
CPE_20_REGEX = re.compile('^(R)[A-Z0-9]{3}$')
CPE_03_REGEX = re.compile('^([BE])[A-Z0-9]{3}$')


class EDIInvoiceSeries(models.Model):
    _name = 'edi.invoice.series'
    _inherit = 'mail.thread'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', string='Tipo de Documento',
                                                  domain=[('code', 'in', ('01', '03',))], required=True,
                                                  copy=False)

    edi_type_code = fields.Char(related='l10n_latam_document_type_id.code')
    name = fields.Char('Serie', size=4, required=True)
    name_nc = fields.Char('Nota de crédito', size=4, required=True, check_company=True)
    name_nd = fields.Char('Nota de débito', size=4, required=True, check_company=True)

    invoice_seq_id = fields.Many2one('ir.sequence',
                                     'Secuencia asociada',
                                     readonly=True)
    credit_note_seq_id = fields.Many2one('ir.sequence',
                                         string='Secuencia de nota de crédito',
                                         readonly=True)
    debit_note_seq_id = fields.Many2one('ir.sequence',
                                        'Secuencia de nota de débito',
                                        readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('publish', 'Publicado'),
        ('canceled', 'Anulado'),
    ], 'Estado', default='draft')

    @api.onchange('name')
    def onchange_name(self):
        if self.name is not False:
            if self.name_nc is False:
                self.name_nc = self.name.replace('E', 'N')
            if self.name_nd is False:
                self.name_nd = self.name.replace('E', 'N')

    def _create_sequence(self, name, edi_type):
        seq = {
            'name': f'CPE/{edi_type}/{name}',
            'implementation': 'no_gap',
            'prefix': f'{name}-',
            'padding': 8,
            'number_increment': 1,
            'use_date_range': False,
            'company_id': self.company_id.id
        }
        return self.env['ir.sequence'].sudo().create(seq)

    def action_cancel(self):
        self.write({
            'state': 'canceled'
        })

    def action_publish(self):
        for record in self:
            if not record.invoice_seq_id.exists():
                sequence = self._create_sequence(record.name, record.l10n_latam_document_type_id.code)
                if self.l10n_latam_document_type_id.code in ['01', '03']:
                    credit_note_sequence = self._create_sequence(record.name_nc, '07')
                    debit_note_sequence = self._create_sequence(record.name_nd, '08')

                    record.write({
                        'invoice_seq_id': sequence.id,
                        'credit_note_seq_id': credit_note_sequence.id,
                        'debit_note_seq_id': debit_note_sequence.id,
                    })

            record.write({
                'state': 'publish'
            })

    @api.constrains('name', 'name_nc', 'name_nd')
    def check_series(self):
        if self.l10n_latam_document_type_id.code == '01':
            regex = CPE_01_REGEX
        elif self.l10n_latam_document_type_id.code == '03':
            regex = CPE_03_REGEX
        else:
            regex = CPE_20_REGEX

        if not bool(regex.match(self.name)):
            raise ValidationError('La serie que ha definido es incorrecta para el tipo de documento')

        if self.l10n_latam_document_type_id.code in ['01', '03']:
            if not bool(regex.match(self.name_nc)):
                raise ValidationError('La serie para notas de crédito que ha definido es incorrecta '
                                      'para el tipo de documento')

            if not bool(regex.match(self.name_nd)):
                raise ValidationError('La serie para notas de débito que ha definido es incorrecta '
                                      'para el tipo de documento')

    def name_get(self, context=None):
        result = []
        for rec in self:
            name = rec.name
            if rec.l10n_latam_document_type_id.id == self.env.ref('l10n_pe_edi.document_type07').id:
                name = rec.name_nc
            if rec.l10n_latam_document_type_id.id == self.env.ref('l10n_pe_edi.document_type08').id:
                name = rec.name_nd
            result.append((rec.id, f'{name}'))
        return result



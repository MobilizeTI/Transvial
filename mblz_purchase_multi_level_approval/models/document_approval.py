# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DocumentApproval(models.Model):
    _name = 'document.approval'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = 'Document Approval -multi level'
    # _check_company_auto = True

    # company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    name = fields.Char('Name document')
    doc_approval_ids = fields.One2many(comodel_name='document.approval.line', inverse_name='doc_approval_id',
                                       string='Lines', required=True, copy=True)
    user_admin_ids = fields.Many2many('res.users',
                                      string='Users admin',
                                      domain=[('flag_approve_po', '=', True)])

    # partner_ids = fields.Many2many('res.partner', string='Partners', check_company=True)
    # product_ids = fields.Many2many('product.product', string='Products', check_company=True)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        try:
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
        except ValueError:
            default['name'] = self.name
        return super(DocumentApproval, self).copy(default)


class DocumentApprovalLine(models.Model):
    _name = 'document.approval.line'
    _description = 'Document Approval Line'

    sequence = fields.Integer(required=True, default=10)
    level = fields.Integer(
        help="Gives the sequence of this line when displaying the level document approval.",
        compute='_sequence_level',
        string="Level"
    )
    doc_approval_id = fields.Many2one('document.approval', string='Document reference', required=True,
                                      ondelete='cascade',
                                      index=True, copy=False)

    description = fields.Char(string='Description', required=False)

    @api.depends('doc_approval_id.doc_approval_ids', 'doc_approval_id.doc_approval_ids.amount')
    def _sequence_level(self):
        for line in self:
            count = 0
            line.sudo().level = count
            for da in line.doc_approval_id.doc_approval_ids:
                count += 1
                da.sudo().level = count

    # company_id = fields.Many2one('res.company', related='doc_approval_id.company_id')
    amount = fields.Float(string='Total greater than or equal', required=True, help='Total greater than or equal')
    user_ids = fields.Many2many('res.users', string='Approvers', required=True)

    def _valid_amount(self, amount):
        record = self.search([], order='amount desc', limit=1)
        if record and record.amount >= amount:
            raise ValidationError(
                f'El valor {amount} debe ser mayor a {record.amount}')

    @api.model
    def create(self, values):
        # Add code here
        if 'amount' in values:
            self._valid_amount(values['amount'])
        return super(DocumentApprovalLine, self).create(values)

    def write(self, values):
        # Add code here
        if 'amount' in values:
            self._valid_amount(values['amount'])
        return super(DocumentApprovalLine, self).write(values)

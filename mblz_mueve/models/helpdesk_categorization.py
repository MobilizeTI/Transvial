# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

TICKET_PRIORITY = [
    ('0', 'Todos'),
    ('1', 'Baja'),
    ('2', 'Alta'),
    ('3', 'Urgente'),
]


class HTT(models.Model):
    _inherit = 'helpdesk.ticket.type'
    priority = fields.Selection(TICKET_PRIORITY, string='Prioridad', default='1', required=True)


class HelpdeskElement(models.Model):
    _name = 'helpdesk.categ.element'
    _description = 'Elementos para las categorias de un ticket'

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Nombre', required=True, copy=True)
    code = fields.Char(string='Código', required=False, copy=False)
    categ_ids = fields.Many2many('maintenance.equipment.category', string='Categoría del vehículo')
    system_id = fields.Many2one('maintenance.system', 'Subsistema')

    maker = fields.Char(string='Fabricante', required=False, copy=False)
    freq_maker = fields.Char(string='Frec fabricante', required=False, copy=False)
    operator = fields.Char(string='Operador', required=False, copy=False)

    # _sql_constraints = [
    #     ('unique_name', 'unique (name)', 'The element name must be unique!')
    # ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        try:
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
        except ValueError:
            default['name'] = self.name
        return super(HelpdeskElement, self).copy(default)


class HelpdeskCateg(models.Model):
    _name = 'helpdesk.categ.category'
    _description = 'Categorias para la categorización de un ticket'

    active = fields.Boolean('Active', default=True)
    code = fields.Char(string='Código', required=True, copy=False)
    name = fields.Char(string='Nombre', required=True, copy=True)
    element_ids = fields.One2many(
        comodel_name='helpdesk.categ.category.line',
        inverse_name='helpdesk_categ_id',
        string='Elementos',
        required=True)

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'The category name must be unique!'),
        ('unique_code', 'unique (code)', 'The category code must be unique!'),
    ]

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        try:
            default.setdefault('name', _("%s (copy)") % (self.name or ''))
        except ValueError:
            default['name'] = self.name
        return super(HelpdeskCateg, self).copy(default)


class HelpdeskCategLines(models.Model):
    _name = 'helpdesk.categ.category.line'
    _description = 'Categorias para la categorización de un ticket -Líneas'

    helpdesk_categ_id = fields.Many2one('helpdesk.categ.category', string='Category', ondelete='cascade',
                                        required=True)
    element_id = fields.Many2one(
        comodel_name='helpdesk.categ.element',
        string='Elemento',
        required=True, ondelete='cascade')
    code = fields.Char(string='Código', related='element_id.code')
    system_id = fields.Many2one('maintenance.system', 'Subsistema', related='element_id.system_id')
    categ_ids = fields.Many2many('maintenance.equipment.category', 'Categoría del vehículo',
                                 related='element_id.categ_ids')

    maker = fields.Char(string='Fabricante', related='element_id.maker')
    freq_maker = fields.Char(string='Frec fabricante', related='element_id.freq_maker')
    operator = fields.Char(string='Operador', related='element_id.operator')

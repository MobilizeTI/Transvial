# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2019-TODAY OPeru.
#    Author      :  Grupo Odoo S.A.C. (<http://www.operu.pe>)
#
#    This program is copyright property of the author mentioned above.
#    You can`t redistribute it and/or modify it.
#
###############################################################################

from datetime import date, datetime, timedelta
from odoo.fields import Date, Datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, AccessError

DNI_VALIDATION = [
    ('api_net', 'Api Net'),
    ('api_peru', 'Api Perú'),
    ('jne', 'JNE'),
    ('facturacion_electronica', 'Facturación Electrónica DNI'),
    ('free_api', 'Free Api'),
]
RUC_VALIDATION = [
    ('api_net', 'Api Net'),
    ('api_peru', 'Api Perú'),
    ('sunat', 'Sunat'),
    ('sunat_multi', 'Sunat Multi')
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def create(self, vals):
        self = self.with_context({
            'avoid_company_default': True,
        })
        company = super(ResCompany, self).create(vals)
        return company

    l10n_pe_ruc_validation = fields.Boolean(string="RUC Validation")
    l10n_pe_dni_validation = fields.Boolean(string="DNI Validation")
    l10n_pe_api_dni_connection = fields.Selection(DNI_VALIDATION, string='Api DNI Connection', default='api_net')
    l10n_pe_api_ruc_connection = fields.Selection(RUC_VALIDATION, string='Api RUC Connection', default='api_peru')

    # l10n_pe_use_proxy = fields.Boolean(string="Use Proxy", default=False)
    # l10n_pe_proxy_ip = fields.Char(string="Proxy IP")
    # l10n_pe_proxy_port = fields.Char(string="Proxy Port")

    @api.onchange('country_id')
    def _onchange_country_id(self):
        super(ResCompany, self)._onchange_country_id()
        if self.country_id and self.country_id.code == 'PE':
            self.l10n_pe_ruc_validation = True
            self.l10n_pe_dni_validation = True
        else:
            self.l10n_pe_ruc_validation = False
            self.l10n_pe_dni_validation = False

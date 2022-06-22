# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime
import json

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'
    
    filter_contable_id = None

    @api.model
    def _init_filter_contable_id(self, options, previous_options=None):
        if not self.filter_contable_id:
            return

        options['contable_id'] = True
        options['contable_ids'] = previous_options and previous_options.get('contable_ids') or []
        selected_contable_ids = [int(contable) for contable in options['contable_ids']]
        selected_contables = selected_contable_ids and self.env['account.account'].browse(selected_contable_ids) or self.env['account.account'].search([('company_id','=',self.env.company.id)])
        options['selected_contable_ids'] = selected_contables.mapped('name')

    @api.model
    def _get_options_contable_domain(self, options):
        domain = []
        if options.get('contable_ids'):
            contable_ids = [int(contable) for contable in options['contable_ids']]
            domain.append(('account_id', 'in', contable_ids))
        return domain
    
    @api.model
    def _get_options_domain(self, options):
        domain = super(AccountReport,self)._get_options_domain(options)
        domain += self._get_options_contable_domain(options)
        return domain

class ReportCertificationReport(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report'

    filter_contable_id = True

    def _get_domain(self, options):
        common_domain = [('account_id', '!=', False),('partner_id', '!=', False), ('parent_state', 'not in', ('draft', 'cancel'))]
        if options.get('partner_id'):
            common_domain += [('partner_id.id', '=', options.get('partner_id'))]
        if options.get('date'):
            common_domain += [('date', '>=', options['date'].get('date_from')),
                              ('date', '<=', options['date'].get('date_to'))]
        if options.get('contable_ids'):
            common_domain += [('account_id.id', 'in', options.get('contable_ids'))]
        return common_domain

class ReportCertificationReportIca(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.ica'

    def _get_columns_name(self, options):
        return [
            {'name': 'Nombre'},
            {'name': 'Bimestre'},
            {'name': u'Concepto de retención'},
            {'name': u'% Importe'},
            {'name': u'Monto del pago sujeto a retención', 'class': 'number'},
            {'name': 'Retenido y consignado', 'class': 'number'},
            {'name': u'Código Cuenta'},
        ]

    def _get_values_for_columns(self, values):
        return [
            {'name': values['name'], 'field_name': 'name'},
            {'name': values['concepto'], 'field_name': 'concepto'},
            {'name': values['tax_amount'], 'field_name': 'tax_amount'},
            {'name': self.format_value(values['tax_base_amount']), 'field_name': 'tax_base_amount'},
            {'name': self.format_value(values['balance']), 'field_name': 'balance'},
            {'name': values['account_id'], 'field_name': 'account_id'}
        ]

    def _get_domain(self, options):
        res = super(ReportCertificationReportIca, self)._get_domain(options)
        res += [('account_id.code', '=like', '2368%')]
        return res

    def _handle_aml(self, aml, lines_per_bimonth):
        bimonth = self._get_bimonth_for_aml(aml)
        account_tax_line = self.env['account.tax.repartition.line'].search([('account_id','=',aml.account_id.id)]).tax_id
        tax_amount = abs(float(account_tax_line.mapped('amount')[0]))*10 if account_tax_line else 0.0
        if bimonth not in lines_per_bimonth:
            lines_per_bimonth[bimonth] = {
                'name': self._get_bimonth_name(bimonth),
                'concepto': aml.account_id.display_name,
                'tax_amount':str("{0:.2f}".format(tax_amount)),
                'tax_base_amount': 0,
                'balance': 0,
                'account_id': aml.account_id.code,
            }

        lines_per_bimonth[bimonth]['balance'] += aml.credit - aml.debit
        if aml.credit:
            lines_per_bimonth[bimonth]['tax_base_amount'] += aml.tax_base_amount
        else:
            lines_per_bimonth[bimonth]['tax_base_amount'] -= aml.tax_base_amount

class ReportCertificationReportIva(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.iva'

    def _get_columns_name(self, options):
        return [
            {'name': 'Nombre'},
            {'name': 'Bimestre'},
            {'name': u'Concepto de retención'},
            # {'name': u'% Importe'},
            {'name': u'Monto Total Operación', 'class': 'number'},
            {'name': u'Monto del Pago Sujeto Retención', 'class': 'number'},
            {'name': 'Retenido Consignado', 'class': 'number'},
            {'name': '%', 'class': 'number'},
            {'name': u'Código Cuenta'},
        ]

    def _get_values_for_columns(self, values):
        return [
            {'name': values['name'], 'field_name': 'name'},
            {'name': values['concepto'], 'field_name': 'concepto'},
            # {'name': values['tax_amount'], 'field_name': 'tax_amount'},
            {'name': self.format_value(values['tax_base_amount']), 'field_name': 'tax_base_amount'},
            {'name': self.format_value(values['balance_15_over_19']), 'field_name': 'balance_15_over_19'},
            {'name': self.format_value(values['balance']), 'field_name': 'balance'},
            {'name': 0.15 if values['balance'] else 0, 'field_name': 'percentage'},
            {'name': values['account_id'], 'field_name': 'account_id'}
        ]

    def _get_domain(self, options):
        res = super(ReportCertificationReportIva, self)._get_domain(options)
        res += ['|', ('account_id.code', '=like', '2367%'), ('account_id.code', '=like', '2408%')]
        return res

    def _handle_aml(self, aml, lines_per_bimonth):
        bimonth = self._get_bimonth_for_aml(aml)
        account_tax_line = self.env['account.tax.repartition.line'].search([('account_id','=',aml.account_id.id)]).tax_id
        tax_amount = abs(float(account_tax_line.mapped('amount')[0])) if account_tax_line else 0.0
        if bimonth not in lines_per_bimonth:
            lines_per_bimonth[bimonth] = {
                'name': self._get_bimonth_name(bimonth),
                'concepto': aml.account_id.display_name,
                'tax_base_amount': 0,
                # 'tax_amount':str(tax_amount),
                'balance': 0,
                'balance_15_over_19': 0,
                'account_id': aml.account_id.code,
            }

        if aml.account_id.code.startswith('2408'):
            lines_per_bimonth[bimonth]['balance_15_over_19'] += aml.credit - aml.debit
        else:
            lines_per_bimonth[bimonth]['balance'] += aml.credit - aml.debit
            if aml.credit:
                lines_per_bimonth[bimonth]['tax_base_amount'] += aml.tax_base_amount
            else:
                lines_per_bimonth[bimonth]['tax_base_amount'] -= aml.tax_base_amount

class ReportCertificationReportFuente(models.AbstractModel):
    _inherit = 'l10n_co_reports.certification_report.fuente'    

    def _get_columns_name(self, options):
        return [
            {'name': u'Nombre'},
            {'name': u'Concepto de retención'},
            {'name': u'% Importe'},
            {'name': u'Monto del Pago Sujeto Retención', 'class': 'number'},
            {'name': u'Retenido Consignado', 'class': 'number'},
            {'name': u'Código Cuenta'},
        ]

    def _get_values_for_columns(self, values):
        return [
            {'name': values['name'], 'field_name': 'name'},
            {'name': values['tax_amount'], 'field_name': 'tax_amount'},
            {'name': self.format_value(values['tax_base_amount']), 'field_name': 'tax_base_amount'},
            {'name': self.format_value(values['balance']), 'field_name': 'balance'},
            {'name': values['account_id'], 'field_name': 'account_id'}
        ]

    def _get_domain(self, options):
        res = super(ReportCertificationReportFuente, self)._get_domain(options)
        res += [('account_id.code', '=like', '2365%'), ('account_id.code', '!=', '236505')]
        return res

    def _handle_aml(self, aml, lines_per_account):
        account_code = aml.account_id.code
        account_tax_line = self.env['account.tax.repartition.line'].search([('account_id','=',aml.account_id.id)]).tax_id
        tax_amount = abs(float(account_tax_line.mapped('amount')[0])) if account_tax_line else 0.0
        
        if account_code not in lines_per_account:
            lines_per_account[account_code] = {
                'name': aml.account_id.display_name,
                'tax_amount':str(tax_amount),
                'tax_base_amount': 0,
                'balance': 0,
                'account_id': account_code,
            }

        lines_per_account[account_code]['balance'] += aml.credit - aml.debit
        if aml.credit:
            lines_per_account[account_code]['tax_base_amount'] += aml.tax_base_amount
        else:
            lines_per_account[account_code]['tax_base_amount'] -= aml.tax_base_amount

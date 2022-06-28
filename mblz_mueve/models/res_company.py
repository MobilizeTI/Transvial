# -*- coding: utf-8 -*-
from pprint import pprint

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_company_address_field_names(self):
        """ Return a list of fields coming from the address partner to match
        on company address fields. Fields are labeled same on both models. """
        return ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']

    def _compute_address(self):
        for company in self.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                dic_upd_address = company._get_company_address_update(partner)
                if 'stage_id' in dic_upd_address:
                    dic_upd_address.pop('stage_id')

                print(dic_upd_address)
                company.update(dic_upd_address)

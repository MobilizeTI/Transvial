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
from pprint import pprint

from odoo import _, api, fields, models
from odoo.addons.pe_ruc_validation.models import sunatconstants
import requests
import json
from zipfile import ZipFile
from bs4 import BeautifulSoup
from io import BytesIO
from odoo.exceptions import Warning, UserError, ValidationError
import re
import logging

from .request_khatu import get_data_api_peru

REGEX_CAPTCHA = re.compile('[A-Z]{4}')
REGEX_RUC = re.compile('(10|20|15|17)[0-9]{9}')
REGEX_DNI = re.compile('[0-9]{8}')

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_country(self):
        return self.env.company.country_id.id

    def _default_ref(self):
        return self.vat or False

    ref = fields.Char(string='Reference', index=True, default=_default_ref)

    country_id = fields.Many2one(default=_default_country)
    commercial_name = fields.Char(string="Commercial Name")
    sunat_condition = fields.Selection([('habido', 'Habido'),
                                        ('nhabido', 'No Habido')], string="State")
    sunat_active = fields.Selection([
        ('active', 'Activo'),
        ('not_active', 'No Activo')
    ], 'Estado')
    alert_warning_vat = fields.Boolean(string="Alert warning vat", default=False)

    def button_update_data(self):
        self.ensure_one()
        res = {}
        vat = self.vat.strip() if self.vat else ''
        if self.vat:
            if self.l10n_latam_identification_type_id.l10n_pe_vat_code == '6':
                if len(self.vat) != 11 and not bool(REGEX_RUC.match(vat)):
                    res['warning'] = {'title': _('Warning'),
                                      'message': _('The Ruc must be 11 characters long and start with 10,20,15 or 17.')}
                else:
                    company = self.env['res.company'].browse(self.env.company.id)
                    if company.l10n_pe_ruc_validation == True:
                        self.get_data_ruc()
            elif self.l10n_latam_identification_type_id.l10n_pe_vat_code == '1':
                if len(self.vat) != 8 and not bool(REGEX_DNI.match(vat)):
                    res['warning'] = {'title': _('Warning'), 'message': _('The Dni must be 8 characters long.')}
                else:
                    company = self.env['res.company'].browse(self.env.company.id)
                    if company.l10n_pe_dni_validation == True:
                        self.get_data_dni()
        if res:
            return res

    @api.onchange('vat', 'l10n_latam_identification_type_id')
    def onchange_vat(self):
        if self.env.company.l10n_pe_ruc_validation or self.env.company.l10n_pe_dni_validation:
            res = {}
            # self.name = False
            # self.commercial_name = False
            # self.street = False
            vat = self.vat.strip() if self.vat else ''
            if self.vat:
                if self.l10n_latam_identification_type_id.l10n_pe_vat_code == '6':
                    if len(self.vat) != 11 and not bool(REGEX_RUC.match(vat)):
                        res['warning'] = {'title': _('Warning'),
                                          'message': _(
                                              'The Ruc must be 11 characters long and start with 10,20,15 or 17.')}
                    else:
                        company = self.env['res.company'].browse(self.env.company.id)
                        if company.l10n_pe_ruc_validation == True:
                            self.get_data_ruc()
                elif self.l10n_latam_identification_type_id.l10n_pe_vat_code == '1':
                    if len(self.vat) != 8 and not bool(REGEX_DNI.match(vat)):
                        res['warning'] = {'title': _('Warning'), 'message': _('The Dni must be 8 characters long.')}
                    else:
                        company = self.env['res.company'].browse(self.env.company.id)
                        if company.l10n_pe_dni_validation == True:
                            self.get_data_dni()
            if res:
                return res

    def get_data_ruc(self):
        result = self.l10n_pe_ruc_connection(self.vat)
        if result:
            if self.env.company.l10n_pe_api_ruc_connection != 'api_peru':
                self.alert_warning_vat = False
                self.ref = self.vat

                avoid_company_default = self._context.get('avoid_company_default', False)
                if not avoid_company_default:
                    self.company_id = self.env.company

                self.company_type = 'company'
                self.name = str(result['business_name']).strip()
                self.commercial_name = str(result['commercial_name'] or result['business_name']).strip()
                self.street = str(result['residence']).strip()
                if 'street_number' and 'street_number2' in result:
                    self.street_number = str(result['street_number']).strip()
                    self.street_number2 = str(result['street_number2']).strip()

                if result['contributing_condition'] == 'HABIDO':
                    self.sunat_condition = 'habido'
                else:
                    self.sunat_condition = 'nhabido'
                if 'sunat_active' in result:
                    if result['sunat_active'] == 'ACTIVO':
                        self.sunat_active = 'active'
                    else:
                        self.sunat_active = 'not_active'

                if result['value']:
                    self.l10n_pe_district = result['value']['district_id']
                    self.city_id = result['value']['city_id']
                    self.state_id = result['value']['state_id']
                    if 'zip' in result:
                        self.zip = result['value']['zip']
            else:
                if not result["success"]:
                    return result
                data = result["data"]
                vals = self.assign_values_from_sunat_ruc(data)
                self.update(vals)

    def get_data_dni(self):
        result = self.l10n_pe_dni_connection(self.vat)
        if result:
            if self.env.company.l10n_pe_api_ruc_connection == 'api_peru':
                self.alert_warning_vat = False
                self.ref = self.vat
                avoid_company_default = self._context.get('avoid_company_default', False)
                if not avoid_company_default:
                    self.company_id = self.env.company
                self.name = str(result['nombre'] or '').strip()
                self.company_type = 'person'
            else:
                if not result["success"]:
                    return result
                data = result["data"]
                vals = self.assign_values_from_sunat_dni(data)
                self.update(vals)

    @api.model
    def api_net_ruc_connection(self, ruc):
        url = 'https://api.apis.net.pe/v1/ruc?numero={ruc}'.format(ruc=ruc)
        data = {}
        try:
            r = requests.get(url, timeout=(15))
            result = r.json()
            sunat_cons = None
            if ruc[0] == '1':
                sunat_cons = sunatconstants.PersonaNaturalConstant
            elif ruc[0] == '2':
                sunat_cons = sunatconstants.PersonaJuridicaConstant

            data['ruc'] = result['numeroDocumento']
            data['business_name'] = result['nombre']
            data['type_of_taxpayer'] = sunat_cons.type_of_taxpayer.value
            data['estado'] = result['estado']
            data['condicion'] = result['condicion']
            data['contributing_condition'] = result['condicion']
            data['sunat_active'] = result['estado']
            data['commercial_name'] = ''

            district = result['distrito']
            province = result['provincia']
            address = result['direccion']
            prov_ids = self.env['res.city'].search([('name', '=ilike', province), ('state_id', '!=', False)])
            dist_id = self.env['l10n_pe.res.city.district'].search(
                [('name', '=ilike', district), ('city_id', 'in', [x.id for x in prov_ids])], limit=1)
            dist_short_id = self.env['l10n_pe.res.city.district'].search([('name', '=', district)], limit=1)
            if dist_id:
                l10n_pe_district = dist_id
            else:
                l10n_pe_district = dist_short_id

            vals = {}
            if l10n_pe_district:
                vals['district_id'] = l10n_pe_district.id
                vals['city_id'] = l10n_pe_district.city_id.id
                vals['state_id'] = l10n_pe_district.city_id.state_id.id
                vals['country_id'] = l10n_pe_district.city_id.state_id.country_id.id
                vals['zip'] = result['ubigeo'] or l10n_pe_district.city_id.zipcode
            data['value'] = vals
            data['residence'] = address
            data['street_number'] = result['numero']
            data['street_number2'] = result['interior']

        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    # --------------------- API PERÚ inicio------------------------------
    def get_values_consultation(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        _url = get_param("api.dev.ruc.dni.url", '')
        _token = get_param("api.dev.ruc.dni.token", '')
        if _url == '':
            raise ValidationError(_("URL not found"))
        if _token == '' or _token == 'paste your token':
            raise ValidationError(_("Token not found"))
        return _url, _token

    @api.model
    def api_peru_ruc_connection(self, ruc):
        url, token = self.get_values_consultation()
        url = url + '/ruc/' + ruc
        data = get_data_api_peru(url, token)
        pprint(data)
        return data

    @api.model
    def api_peru_dni_connection(self, dni):
        url, token = self.get_values_consultation()
        url = url + '/dni/' + dni
        data = get_data_api_peru(url, token)
        pprint(data)
        return data

    @api.model
    def assign_values_from_sunat_ruc(self, data):
        vals = self.get_match_address(data)
        vals["name"] = data.get('nombre_o_razon_social', self.name)
        vals["street"] = data.get('direccion_completa', self.street)

        if data["estado"]:
            if data["estado"] == "ACTIVO":
                vals['sunat_active'] = 'active'
            else:
                vals['sunat_active'] = 'not_active'
        if data["condicion"]:
            if data["condicion"] == "HABIDO":
                vals['sunat_condition'] = 'habido'
                # vals["condition_color"] = COLOR_CONDITION["active"]
            else:
                vals['sunat_condition'] = 'nhabido'
                # vals["condition_color"] = COLOR_CONDITION["inactive"]
        return vals

    @api.model
    def get_match_address(self, data):
        l10n_pe_district = self.env["l10n_pe.res.city.district"].search([("code", "=", data["ubigeo"][2])], limit=1)
        vals = {
            "country_id": False,
            "state_id": False,
            "city_id": False,
            "l10n_pe_district": False,
            "street": False,
        }
        if l10n_pe_district.id:
            vals["l10n_pe_district"] = l10n_pe_district.id
            vals["city_id"] = l10n_pe_district.city_id.id
            vals["state_id"] = l10n_pe_district.city_id.state_id.id
            vals["country_id"] = l10n_pe_district.city_id.state_id.country_id.id
        if data["ubigeo"][2]:
            vals["zip"] = data["ubigeo"][2]
        vals["street"] = data["direccion"]
        return vals

    @api.model
    def assign_values_from_sunat_dni(self, data):
        vals = {}
        if data["nombre_completo"]:
            vals["name"] = data["nombre_completo"]
        return vals

    # --------------------- API PERÚ fin------------------------------

    @api.model
    def sunat_connection(self, ruc):
        session = requests.Session()
        url_sunat = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
        headers = requests.utils.default_headers()
        headers[
            'User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        data = {}
        try:
            url_numRnd = session.get(
                'https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias?accion=consPorRazonSoc&razSoc=BVA%20FOODS',
                headers=headers, timeout=12).content
            html_content = BeautifulSoup(url_numRnd, 'html.parser')
            content_form = html_content.find_all('form')
            numRnd = content_form[0].find_all('input')[3].get('value')
            data_ruc = {'accion': 'consPorRuc', 'nroRuc': ruc, 'numRnd': numRnd, 'actReturn': '1', 'modo': '1'}
            html_doc = session.post(url=url_sunat, data=data_ruc, headers=headers, timeout=(15, 20))
            html_info = BeautifulSoup(html_doc.content, 'html.parser')
            div_info = html_info.find_all("div", {"class": "list-group"})
            div_p_info = div_info[0].find_all("p", {"class": "list-group-item-text"})
            div_h4_info = div_info[0].find_all("h4", {"class": "list-group-item-heading"})
            sunat_cons = None
            if ruc[0] == '1':
                sunat_cons = sunatconstants.PersonaNaturalConstant

            elif ruc[0] == '2':
                sunat_cons = sunatconstants.PersonaJuridicaConstant

            number_ruc = (div_h4_info[sunat_cons.number_ruc.value].contents[0])
            data['ruc'] = number_ruc.split(' - ')[0]
            data['business_name'] = number_ruc.split(' - ')[1]
            data['type_of_taxpayer'] = (div_p_info[sunat_cons.type_of_taxpayer.value].contents[0])
            data['sunat_condition'] = (div_p_info[sunat_cons.taxpayer_state.value].contents[0])
            data['contributing_condition'] = (div_p_info[sunat_cons.contributing_condition.value].contents[0]).replace(
                '\r', '') \
                .replace('\n', '').strip()
            data['commercial_name'] = (div_p_info[sunat_cons.commercial_name.value].contents[0]).replace('-',
                                                                                                         '').strip()

            residence = (div_p_info[sunat_cons.tax_residence.value].contents[0])
            district = (" ".join(residence.split("-")[-1].split())).title()
            province = (" ".join(residence.split("-")[-2].split())).title()
            address = " ".join(residence.split())
            address = " ".join(residence.split("-")[0:-2])
            prov_ids = self.env['res.city'].search([('name', '=', province), ('state_id', '!=', False)])
            dist_id = self.env['l10n_pe.res.city.district'].search(
                [('name', '=', district), ('city_id', 'in', [x.id for x in prov_ids])], limit=1)
            dist_short_id = self.env['l10n_pe.res.city.district'].search([('name', '=', district)], limit=1)
            if dist_id:
                l10n_pe_district = dist_id
            else:
                l10n_pe_district = dist_short_id

            vals = {}
            if l10n_pe_district:
                vals['district_id'] = l10n_pe_district.id
                vals['city_id'] = l10n_pe_district.city_id.id
                vals['state_id'] = l10n_pe_district.city_id.state_id.id
                vals['country_id'] = l10n_pe_district.city_id.state_id.country_id.id
            data['value'] = vals
            data['residence'] = str(address).strip()

        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def l10n_pe_ruc_connection(self, ruc):
        data = {}
        if self.env.user.company_id.l10n_pe_api_ruc_connection == 'sunat':
            data = self.sunat_connection(ruc)
        elif self.env.user.company_id.l10n_pe_api_ruc_connection == 'sunat_multi':
            data = self.sunat_connection_multi(ruc)
        elif self.env.user.company_id.l10n_pe_api_ruc_connection == 'api_net':
            data = self.api_net_ruc_connection(ruc)
        elif self.env.user.company_id.l10n_pe_api_ruc_connection == 'api_peru':
            data = self.api_peru_ruc_connection(ruc)
        return data

    def _extract_csv_from_zip(self, url_zip, name_zip):
        nombre_txt = name_zip.replace('.zip', '.txt')
        res = requests.get(url_zip)
        zipfile = ZipFile(BytesIO(res.content))
        lineas = list()
        for linea in zipfile.open(nombre_txt).readlines():
            lineas.append(linea.decode('utf-8'))
        json_datos = dict()
        cabeceras = lineas[0].split('|')
        valores = lineas[1].split('|')
        for indice, cabecera in enumerate(cabeceras):
            if indice != len(cabeceras) - 1:
                json_datos[cabecera.strip().lower().replace('-', '').replace('ó', '').replace(' ', '_')] = valores[
                    indice].strip()
        return json_datos

    def sunat_connection_multi(self, ruc):
        session = requests.Session()
        # if self.env.company.l10n_pe_use_proxy:
        #     url_proxy = "http://%s:%s" % (self.env.company.l10n_pe_proxy_ip, self.env.company.l10n_pe_proxy_port)
        #     session.proxies = {
        #         "http": url_proxy,
        #         "https": url_proxy,
        #     }
        url_sunat = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsmulruc/jrmS00Alias"
        headers = requests.utils.default_headers()
        headers[
            'User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        data = {}
        try:
            captcha = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsmulruc/captcha"
            text_captcha = session.post(url=captcha, data={'accion': 'random'}, headers=headers)
            data_ruc = {'accion': 'consManual', 'selRuc': ruc, 'numRnd': text_captcha}
            html_doc = session.post(url=url_sunat, data=data_ruc, headers=headers, timeout=(15, 20))
            html_info = BeautifulSoup(html_doc.content, 'html.parser')
            table_info = html_info.find_all('a', href=True)
            url_zip = table_info[0]['href']
            name_zip = table_info[0].contents[0]
            json_datos = self._extract_csv_from_zip(url_zip, name_zip)
            data['ruc'] = json_datos['numeroruc']
            data['business_name'] = json_datos['nombre__razonsocial']
            data['type_of_taxpayer'] = json_datos['tipo_de_contribuyente']
            data['sunat_condition'] = json_datos['estado_del_contribuyente']
            data['contributing_condition'] = json_datos['condicion_del_contribuyente']
            data['commercial_name'] = json_datos['nombre_comercial']
            provincia = json_datos['provincia'].title()
            distrito = json_datos['distrito'].title()
            prov_ids = self.env['res.city'].search([('name', '=', provincia), ('state_id', '!=', False)])
            dist_id = self.env['l10n_pe.res.city.district'].search(
                [('name', '=', distrito), ('city_id', 'in', [x.id for x in prov_ids])], limit=1)
            dist_short_id = self.env['l10n_pe.res.city.district'].search([('name', '=', json_datos['distrito'])],
                                                                         limit=1)
            if dist_id:
                l10n_pe_district = dist_id
            else:
                l10n_pe_district = dist_short_id

            vals = {}
            if l10n_pe_district:
                vals['district_id'] = l10n_pe_district.id
                vals['city_id'] = l10n_pe_district.city_id.id
                vals['state_id'] = l10n_pe_district.city_id.state_id.id
                vals['country_id'] = l10n_pe_district.city_id.state_id.country_id.id
            data['value'] = vals
            data['residence'] = json_datos['direccion']
        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def reniec_connection(self, dni):
        session = requests.Session()
        headers = requests.utils.default_headers()
        headers[
            'User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        url_reniec = 'https://api.reniec.cloud/dni/{dni}'
        data = {}
        try:
            response = session.get(url=url_reniec.format(dni=dni), verify=False, headers=headers).text
            values_response = response.replace('&Ntilde;', 'Ñ')
            result = json.loads(values_response)
            data['nombre'] = (result['nombres'] + " " + result['apellido_paterno'] + " " + result['apellido_materno'])
        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def api_net_connection(self, dni, return_3_names=False):
        """ si return_3_names==False -> Retorna data con 1 item: nombre, si return_3_names==True -> Retorna data con 3 items: apellidoPaterno, apellidoMaterno, nombres
        """
        url = 'https://api.apis.net.pe/v1/dni?numero={dni}'.format(dni=dni)
        # headers = {'authorization': 'token apis-token-327.4f4I2qnVL8UUxziuy4dW5oxNBUeAvkCW'}
        data = {}
        try:
            r = requests.get(url, timeout=(15))
            result = r.json()
            if return_3_names:
                apellido_paterno = result.get('apellidoPaterno')
                apellido_materno = result.get('apellidoMaterno')
                nombres = result.get('nombres')
                data['apellidoPaterno'] = apellido_paterno or ''
                data['apellidoMaterno'] = apellido_materno or ''
                data['nombres'] = nombres or ''
                return data

            name = result.get('nombre')
            data['nombre'] = name
        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def jne_connection(self, dni):
        session = requests.Session()
        headers = requests.utils.default_headers()
        headers[
            'User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
        headers['Content-Type'] = 'application/json;chartset=utf-8'
        headers[
            'Requestverificationtoken'] = 'Dmfiv1Unnsv8I9EoXEzbyQExSD8Q1UY7viyyf_347vRCfO-1xGFvDddaxDAlvm0cZ8XgAKTaWclVFnnsGgoy4aLlBGB5m-E8rGw_ymEcCig1:eq4At-H2zqgXPrPnoiDGFZH0Fdx5a-1UiyVaR4nQlCvYZzAhzmvWxLwkUk6-yORYrBBxEnoG5sm-Hkiyc91so6-nHHxIeLee5p700KE47Cw1'
        url_reniec = 'https://aplicaciones007.jne.gob.pe/srop_publico/Consulta/api/AfiliadoApi/GetNombresCiudadano'
        dni_value = {"CODDNI": dni}
        data = {}
        try:
            response = session.post(url=url_reniec, json=dni_value, headers=headers, timeout=(15)).text
            values_response = response.replace('|', ' ')
            result = json.loads(values_response)
            data['nombre'] = result['data']
        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def free_api_connection(self, dni):
        url = 'https://dni.optimizeperu.com/api/prod/persons/{dni}'.format(dni=dni)
        headers = {'authorization': 'token 48b5594ab9a37a8c3581e5e71ed89c7538a36f11'}
        data = {}
        try:
            r = requests.get(url, headers=headers, timeout=(15))
            result = r.json()
            name = result.get('first_name') + " " + result.get('last_name') + " " + result.get('name')
            data['nombre'] = name
        except Exception:
            self.alert_warning_vat = True
            data = False
        return data

    @api.model
    def facturacion_electronica_dni_connection(self, dni):
        url = 'https://www.facturacionelectronica.us/facturacion/controller/ws_consulta_rucdni_v2.php'
        params = {
            'usuario': '10447915125',
            'password': '985511933',
            'documento': 'DNI',
            'nro_documento': dni
        }
        data = {}
        try:
            r = requests.get(url, params, timeout=(15))
            result = r.json()
            name = result.get('result').get('Paterno') + " " + result.get('result').get('Materno') + " " + result.get(
                'result').get('Nombre')
            data['nombre'] = name
        except Exception:
            self.alert_warning_vat = True
            data = False

        return data

    @api.model
    def l10n_pe_dni_connection(self, dni):
        data = {}
        company = self.env.company
        if company.l10n_pe_api_dni_connection == 'api_net':
            data = self.api_net_connection(dni)
        elif company.l10n_pe_api_dni_connection == 'api_peru':
            data = self.api_peru_dni_connection(dni)
        elif company.l10n_pe_api_dni_connection == 'jne':
            data = self.jne_connection(dni)
        elif company.l10n_pe_api_dni_connection == 'facturacion_electronica':
            data = self.facturacion_electronica_dni_connection(dni)
        elif company.l10n_pe_api_dni_connection == 'free_api':
            data = self.free_api_connection(dni)
        elif not data:
            data = False
        return data

    @api.onchange('l10n_pe_district')
    def _onchange_l10n_pe_district(self):
        if self.l10n_pe_district and self.l10n_pe_district.city_id:
            self.city_id = self.l10n_pe_district.city_id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id and self.city_id.state_id:
            self.state_id = self.city_id.state_id
        res = {}
        res['domain'] = {}
        res['domain']['l10n_pe_district'] = []
        if self.city_id:
            res['domain']['l10n_pe_district'] += [('city_id', '=', self.city_id.id)]
        return res

    @api.onchange('state_id')
    def _onchange_state_id(self):
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id
        res = {}
        res['domain'] = {}
        res['domain']['city_id'] = []
        if self.state_id:
            res['domain']['city_id'] += [('state_id', '=', self.state_id.id)]
        return res

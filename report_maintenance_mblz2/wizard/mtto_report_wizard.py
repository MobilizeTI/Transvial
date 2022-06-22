# coding=utf-8
import io

from odoo import fields, api, models, _, tools
from datetime import datetime
import pytz
import calendar
import re

from datetime import date, datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, format_date

from pprint import pprint
from io import BytesIO

import logging
import base64
import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning, CacheMiss
from odoo.tools.misc import formatLang

import xlsxwriter

YEAR_REGEX = re.compile("^[0-9]{4}$")
DATE_FORMAT = '%Y-%m-%d'
fmt = '%Y-%m-%d %H:%M:%S'

MONTH_SELECTION = [('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'), ('4', 'Abril'), ('5', 'Mayo'),
                   ('6', 'Junio'), ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Setiembre'), ('10', 'Octubre'),
                   ('11', 'Noviembre'), ('12', 'Diciembre')]


class MTTOReportWz(models.TransientModel):
    _name = 'mtto.report.wz'
    _description = "Asistente para gestionar los filtros de la fecha"

    rpt_type_id = fields.Many2one('report.mtto.type', string='Reporte', required=True)
    code_rpt_type = fields.Char(string='Code', related='rpt_type_id.code')

    @api.onchange('code_rpt_type')
    def onchange_rpt_type_id(self):
        OBJ_TEMP = self.env['template.report.typeot'].sudo()
        if self.code_rpt_type == '51':
            self.range = 'all'
        self.report_temp_id = OBJ_TEMP.search([('code_rpt_type', '=', self.code_rpt_type)], limit=1)

    def _default_month(self):
        user_tz = self.env.user.tz or 'America/Bogotá'
        timezone = pytz.timezone(user_tz)
        current = datetime.now(timezone)
        return str(current.month)

    def _default_year(self):
        user_tz = self.env.user.tz or 'America/Bogotá'
        timezone = pytz.timezone(user_tz)
        current = datetime.now(timezone)
        return str(current.year)

    range = fields.Selection([
        ('month', 'Por mes'),
        ('dates', 'Fechas'),
        ('date', 'Por día'),
        ('all', 'Todos'),
    ], 'Fecha', default='month', required=True)

    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company.id)

    month = fields.Selection(MONTH_SELECTION, string='Mes', default=_default_month)
    year = fields.Char('Año', default=_default_year)
    date_start = fields.Date('Desde')
    date_end = fields.Date('Hasta')

    def _get_current_date(self):
        """ :return current date """
        return datetime.now(pytz.timezone(self.env.user.tz or 'America/Bogotá'))

    date_def = fields.Date('Día', default=lambda self: self._get_current_date())
    hour_def = fields.Float('Hora')

    hour_start = fields.Float('Hora inicio')
    hour_end = fields.Float('Hora fin')

    km_value = fields.Integer(string='kilometraje', default=10000)

    report_temp_id = fields.Many2one('template.report.typeot',
                                     string='Plantilla', required=False)

    # @api.model
    # def default_get(self, fields_list):
    #     res = super().default_get(fields_list)
    #     res['rpt_type_id'] = self.env.ref('report_maintenance_mblz2.rpt_type_13').id
    #     return res

    @api.onchange('year')
    def onchange_year(self):
        if self.year is False or not bool(YEAR_REGEX.match(self.year)):
            raise ValidationError('Debe especificar un año correcto')

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        if self.date_start is not False and \
                self.date_end is not False:
            if self.date_end < self.date_start:
                raise ValidationError('La fecha de inicio debe ser menor o igual que la fecha de fin')

    @api.onchange('range', 'month')
    def onchange_range(self):
        if self.range == 'month':
            w, days = calendar.monthrange(int(self.year), int(self.month))
            self.date_start = datetime.strptime('{}-{}-{}'.format(self.year, self.month, 1), DATE_FORMAT).date()
            self.date_end = datetime.strptime('{}-{}-{}'.format(self.year, self.month, days), DATE_FORMAT).date()
        # print(self.date_start, self.date_end)

    # ----------------------------------------
    @api.constrains('date_start', 'date_end')
    def check_parameters(self):
        for record in self:
            if record.date_start and record.date_end:
                start = record.date_start.strftime(DEFAULT_SERVER_DATE_FORMAT)
                end = record.date_end.strftime(DEFAULT_SERVER_DATE_FORMAT)
                if start > end:
                    raise ValidationError('La fecha de fin debe ser mayor que la de inicio')

    # ----------------------------------------

    def _get_name_rpt(self):
        if self.range == 'month':
            month_label = dict(self.fields_get("month", "selection")["month"]["selection"])
            return f'{self.rpt_type_id.name} ({month_label[self.month]}/{self.year})'
        elif self.range == 'dates':
            return f'{self.rpt_type_id.name} ({self.date_start} AL {self.date_end})'
        elif self.range == 'date':
            return f'{self.rpt_type_id.name} ({self.date_start})'
        else:
            return f'{self.rpt_type_id.name} (Todos)'

    def _get_parameter(self):
        dates = (self.date_start, self.date_end)
        data = dict(name=self._get_name_rpt(),
                    opc=False,
                    dates=False,
                    date=False,
                    code_rpt_type=self.code_rpt_type,
                    km_value=self.km_value,
                    report_temp_id=self.report_temp_id)
        if self.range != 'all':
            data.update(dict(
                opc='dates' if self.range != 'date' else 'date',
                dates=dates,
                date=self.date_def,
            ))
        return data

    def _get_action_rpt_51(self):
        # action = self.env["ir.actions.actions"]._for_xml_id("report_maintenance_mblz2.mblz_action_view_quants")
        action = self.env['stock.quant'].with_context(
            search_default_internal_loc=1,
            search_default_productgroup=1,
            search_default_locationgroup=1,
        ).action_view_quants_mtto(parameters=self._get_parameter())
        return action

    def _get_action_rpt_73(self, parameters):
        domain = [('state', '=', 'purchase'), ('display_type', '=', False)]
        if parameters['opc'] == 'dates':
            date_start, date_end = parameters['dates']
            domain += [('date_order', '>=', date_start), ('date_order', '<=', date_end)]
        elif parameters['opc'] == 'date':
            domain += [('date_order', '=', parameters['date'])]

        view_tree = self.env.ref('report_maintenance_mblz2.purchase_order_line_tree')
        view_calendar = self.env.ref('report_maintenance_mblz2.purchase_order__line_calendar')
        view_pivot = self.env.ref('report_maintenance_mblz2.purchase_order_line_pivot')
        return {
            'name': parameters['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,pivot,calendar',
            'views': [(view_tree.id, 'tree'), (view_pivot.id, 'pivot'), (view_calendar.id, 'calendar')],
            'view_id': view_tree.id,
            'target': 'current',
            'domain': domain,
            'context': {
                "search_default_todo": True,
                "show_purchase": True,
            }
        }

    def action_view_screen(self):
        if self.rpt_type_id.code == '01':
            return self.create_rpt_01(parameter=self._get_parameter())
        elif self.rpt_type_id.code == '10':
            return self.env['report.buses.stopped'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '12':
            return self.env['fechas.de.vencimiento.de.mtto'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code in ('13', '14'):
            return self.env['report.fleet.technical.unreliability'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '19':
            return self.env['report.material.consumption.cost'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '21':
            return self.env['costo.por.kilometraje.detalle'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '24':
            return self.env['maintenance.request.preventive.details'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '25':
            return self.env['maintenance.request.details'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '26':
            return self.env['cumplimiento.mtto.preventivo.details'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '28':
            return self.env['report.buses.overhaul'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '32':
            return self.env['productividad.mantenimiento'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '35':
            return self.env['report.deferred.work'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '36':
            return self.env['report.reiterative.technical.failures'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '42':
            return self.env['report.buses.operational.failure'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '43':
            return self.env['inhabilitacion.tecnica'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '51':
            return self._get_action_rpt_51()
        elif self.rpt_type_id.code == '55':
            return self.env['report.equipment.its.failures'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '64':
            return self.env['report.sirci.system.failures'].get_act_window(data=self._get_parameter())
        elif self.rpt_type_id.code == '73':
            # return self.env["ir.actions.actions"]._for_xml_id("report_maintenance_mblz2.purchase_line_form_action")
            return self._get_action_rpt_73(parameters=self._get_parameter())

    # --------------------------------------- REPORTE 01 INICIO---------------------------------------
    def get_query_rpt_01(self, dates=False, date=False):
        sql = f"""select * from maintenance_request as mr 
                 where mr.company_id = {self.env.company.id}
              """
        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += " AND mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        elif date:
            sql_where += " AND mr.request_date = '{0}'".format(date)
        if sql_where != "":
            sql += sql_where
        return sql

    def create_rpt_01(self, parameter):
        OBJ_MR = self.env['report.search.ot'].sudo()
        data = []

        if parameter['opc'] == 'dates':
            query = OBJ_MR.get_query(dates=parameter['dates'])
        elif parameter['opc'] == 'date':
            query = OBJ_MR.get_query(date=parameter['date'])
        else:
            query = OBJ_MR.get_query()
        tools.drop_view_if_exists(self._cr, 'report_search_ot')
        self._cr.execute(query)
        data = OBJ_MR.search([])
        print(f'len data: {len(data)}')
        if len(data) == 0 and parameter['opc']:
            raise Warning('!No existe datos, para el filtro ingresado!')

        file_xlsx = self.generate_xlsx_report(data)
        # Se crea el xlsx
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        attachment_id = attachment_obj.sudo().create(
            {'name': self.rpt_type_id.name, 'store_fname': 'name.file_ext', 'datas': file_xlsx})
        # prepare download url
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        # download
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }

    def generate_xlsx_report(self, objects):
        excel = io.BytesIO()
        workbook = xlsxwriter.Workbook(excel, {'in_memory': True, 'default_date_format': 'yy-mm-dd hh:mm'})
        workbook.set_properties(
            {"comments": "Created with Python and XlsxWriter from Odoo 14.0"}
        )
        sheet = workbook.add_worksheet(_("RPT_01"))

        sheet.set_landscape()
        sheet.fit_to_pages(1, 0)
        sheet.set_zoom(80)
        style_cell_title = workbook.add_format({'font': 'Wheelbarrow',
                                                'font_size': 10,
                                                'bold': 1,
                                                'border': 0,
                                                'align': 'center',
                                                'valign': 'vcenter',
                                                'italic': False,
                                                'font_color': 'black'
                                                })

        style_cell_border = workbook.add_format({'font': 'Wheelbarrow',
                                                 'font_size': 8,
                                                 'bold': 1,
                                                 'border': 1,
                                                 'align': 'left',
                                                 'italic': False,
                                                 'valign': 'vcenter',
                                                 'text_wrap': True,
                                                 'bg_color': '#26de81',
                                                 })

        style_cell_bottom_text = workbook.add_format({'font': 'Wheelbarrow',
                                                      'font_size': 8,
                                                      'bold': 0,
                                                      'border': 1,
                                                      'align': 'left',
                                                      'valign': 'top',
                                                      'text_wrap': True,
                                                      'bg_color': '#dfe4ea',
                                                      })

        style_cell_bottom_text2 = workbook.add_format({'font': 'Wheelbarrow',
                                                       'font_size': 8,
                                                       'bold': 0,
                                                       'bottom': 0,
                                                       'align': 'left',
                                                       'valign': 'vcenter',
                                                       'text_wrap': True
                                                       })
        sheet_title = [
            _("SEQ"),
            _("EQUIPO"),
            _("CATEGORIA"),
            _("FECHA DE SOLICITUD"),
            _("FECHA ULT. MODIFICACIÓN"),
            _("FECHA DE CIERRE"),
            _("ETAPA ACTUAL"),
            _("NOMBRE DE OT"),
            _("RESPONSABLE"),

            _("TECNICO DE MTTO"),
            _("ESPECIALIDADES"),
            _("DESCRIPCION"),
            _("SISTEMA"),
            _("COMPONENTE"),

            _("PARTE DE HORAS / DESCRIPCION"),

        ]
        sheet.set_column(0, 6, 20)
        sheet.set_column(7, 7, 40)
        sheet.set_column(8, 9, 30)
        sheet.set_column(10, 11, 40)
        sheet.set_column(12, 13, 30)
        sheet.set_column(14, 14, 90)
        #
        sheet.set_row(0, None, None, {"collapsed": 1})
        sheet.freeze_panes(2, 0)
        sheet.set_tab_color('yellow')

        img_data = base64.b64decode(self.env.company.logo)
        image = io.BytesIO(img_data)

        cell_width = 300.0
        image_width = 22000.0
        cols_wide = 90.0
        scale = cell_width * cols_wide / image_width
        sheet.insert_image('A1', 'logo.png', {'image_data': image, 'x_scale': scale, 'y_scale': scale})
        row = 0
        sheet.set_row(row, 20)
        sheet.merge_range(row, 0, row + 1, 14, self.env.company.name, style_cell_title)

        row = 2
        sheet.write_row(row, 0, sheet_title, style_cell_border)
        row += 1
        for record in objects:
            ot = record.request_id
            name_ot = ot.name
            if ot.ot_master_id:
                task_description = self.env['ir.fields.converter'].text_from_html(ot.ot_master_id.description)
                name_ot += f" {task_description}"
            sheet.write_row(row, 0, [ot.name_seq, ot.equipment_id.name or '',
                                     ot.equipment_id.category_id.name or '',
                                     ot.request_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                     ot.write_date.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                     ot.close_date.strftime(DEFAULT_SERVER_DATE_FORMAT) if ot.close_date else '',
                                     ot.stage_id.name,
                                     name_ot,
                                     ot.user_id.name or ''
                                     ], style_cell_bottom_text)

            for idx, task in enumerate(ot.task_ids):
                if task.timesheet_ids:
                    sheet.set_row(row, len(task.timesheet_ids) * 15)
                sheet.write_row(row, 9, self._get_aux_data(task),
                                style_cell_bottom_text if idx == 0 else style_cell_bottom_text2)
                row += 1
            if not ot.task_ids:
                sheet.merge_range(row, 9, row, 14, '', style_cell_bottom_text)
                row += 1
        workbook.close()
        excel.seek(0)
        xls_data = excel.getvalue()

        excel.close()
        result = base64.b64encode(xls_data)
        return result

    def _get_aux_data(self, task):
        task_description = ''
        if task.description:
            task_description = self.env['ir.fields.converter'].text_from_html(task.description)

        data = [task.employee_id.name or '',
                ', '.join(map(str, task.activity_speciality_ids.mapped('name'))).upper(),
                task_description or '']
        # SISTEMA
        system = ''
        for sis in task.activity_id.system_class_id.parent_ids:
            system += f"{sis.parent_id.name.upper() if sis.parent_id else ''}\n"
        data.append(system.strip())

        # COMPONENTE
        if task.activity_id.system_class_id and task.activity_id.system_class_id.name:
            data.append(
                task.activity_id.system_class_id.name.upper().strip() if task.activity_id.system_class_id else '')
        else:
            data.append('')

        # ACTIVIDADES EJECUTADAS
        tt = ''
        for ts_line in task.timesheet_ids:
            tt += f"{ts_line.name.upper().strip() if ts_line.name else ''}\n"
        data.append(tt)

        return data

    # --------------------------------------- REPORTE 01 FIN---------------------------------------

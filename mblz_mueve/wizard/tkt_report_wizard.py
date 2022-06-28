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


class TktReportWz(models.TransientModel):
    _name = 'tkt.report.wz'
    _description = "Asistente para gestionar los filtros de la fecha"

    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Nivel de falla")
    flag_all = fields.Boolean(string='Todos', required=False)

    # rpt_type_id = fields.Many2one('report.mtto.type', string='Reporte', required=True)
    # code_rpt_type = fields.Char(string='Code', related='rpt_type_id.code')

    # @api.onchange('code_rpt_type')
    # def onchange_rpt_type_id(self):
    #     OBJ_TEMP = self.env['template.report.typeot'].sudo()
    #     if self.code_rpt_type == '51':
    #         self.range = 'all'
    #     self.report_temp_id = OBJ_TEMP.search([('code_rpt_type', '=', self.code_rpt_type)], limit=1)

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
        return datetime.now(pytz.timezone(self.env.user.tz or 'America/Bogotá'))

    date_def = fields.Date('Día', default=lambda self: self._get_current_date())
    hour_def = fields.Float('Hora')

    hour_start = fields.Float('Hora inicio')
    hour_end = fields.Float('Hora fin')

    # report_temp_id = fields.Many2one('template.report.typeot',
    #                                  string='Plantilla', required=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['ticket_type_id'] = self.env.ref('helpdesk.type_question').id
        return res

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
            return f'Reporte de tickets ({month_label[self.month]}/{self.year})'
        elif self.range == 'dates':
            return f'Reporte de tickets ({self.date_start} AL {self.date_end})'
        elif self.range == 'date':
            return f'Reporte de tickets ({self.date_start})'
        else:
            return f'Reporte de tickets (Todos)'

    def _get_parameter(self):
        dates = (self.date_start, self.date_end)
        data = dict(name=self._get_name_rpt(),
                    ticket_type_id=self.ticket_type_id.id if not self.flag_all else False,
                    opc=False,
                    dates=False,
                    date=False)
        if self.range != 'all':
            data.update(dict(
                opc='dates' if self.range != 'date' else 'date',
                dates=dates,
                date=self.date_def,
            ))
        return data

    def action_view_screen(self, web_site=False):
        return self.create_rpt_tkt(web_site, parameter=self._get_parameter())

    # --------------------------------------- REPORTE 01 INICIO---------------------------------------
    def create_rpt_tkt(self, web_site, parameter):
        OBJ_MR = self.env['report.search.tkt'].sudo()
        data = []

        if parameter['opc'] == 'dates':
            query = OBJ_MR.get_query(ticket_type_id=parameter['ticket_type_id'], dates=parameter['dates'])
        elif parameter['opc'] == 'date':
            query = OBJ_MR.get_query(ticket_type_id=parameter['ticket_type_id'], date=parameter['date'])
        else:
            query = OBJ_MR.get_query(ticket_type_id=parameter['ticket_type_id'])
        tools.drop_view_if_exists(self._cr, 'report_search_tkt')
        self._cr.execute(query)
        data = OBJ_MR.search([])
        # print(f'len data: {len(data)}')
        if len(data) == 0 and parameter['opc']:
            raise Warning('!No existe datos, para el filtro ingresado!')

        file_xlsx = self.generate_xlsx_report(data)
        if web_site:
            return file_xlsx
        # Se crea el xlsx
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        attachment_id = attachment_obj.sudo().create(
            {'name': parameter.get('name', 'Reporte tkt'), 'store_fname': 'name.file_ext', 'datas': file_xlsx})
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
        sheet = workbook.add_worksheet(_("Tickets"))

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
                                                 'bg_color': '#fdcb6e',
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
            _("SEQ TKT"),
            _("NOMBRE TKT"),
            _("SEQ OT"),
            _("NOMBRE OT"),
            _("OPERADOR"),
            _("EQUIPO"),
            _("CATEGORIZACION"),
            _("COD_COM"),
            _("FRECUENCIA"),
            _("FREC_FABR"),
            _("FABRICANTE"),
            _("TIPO DE MTM"),
            _("ESTADO"),
            _("NIVEL DE FALLA"),
            _("DESCRIPCION"),
            _("SOLUCION"),
            _("FECHA DE CONTACTO"),
            _("FECHA DE CREACION"),
            _("FECHA DE ASIGNACION"),
            _("FECHA DE CIERRE"),

        ]
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 25)
        sheet.set_column(2, 2, 15)
        sheet.set_column(3, 3, 25)
        sheet.set_column(4, 5, 15)
        sheet.set_column(6, 6, 30)

        sheet.set_column(7, 13, 15)
        sheet.set_column(14, 14, 45)
        sheet.set_column(15, 15, 30)
        sheet.set_column(16, 19, 20)

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
        sheet.merge_range(row, 0, row + 1, 19, f'REPORTE DE TICKETS - {self.env.company.name}', style_cell_title)

        row = 2
        sheet.write_row(row, 0, sheet_title, style_cell_border)
        row += 1

        user_tz = self.env.user.tz or 'America/Bogotá'
        timezone_user = pytz.timezone(user_tz)

        for record in objects:
            tkt = record.ticket_id
            maintenance_type = 'Preventivo' if tkt.nature_type == 'preventive' else 'Correctivo'
            task_description = ''
            if tkt.description:
                task_description = self.env['ir.fields.converter'].text_from_html(tkt.description)
            ot_close_datetime_tz = tkt.ot_close_datetime + timedelta(hours=-5) if tkt.ot_close_datetime else False
            close_datetime = ot_close_datetime_tz.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT) if ot_close_datetime_tz else ''

            frequency = 'NA'
            if tkt.nature_type == 'preventive':
                if tkt.mtm_request_id and tkt.mtm_request_id.guide_line_ids:
                    frequency = ', '.join(map(str, tkt.mtm_request_id.maintenance_guideline_ids.mapped('uom_id.name')))

            tkt_create_date_tz = tkt.create_date + timedelta(hours=-5)
            sheet.write_row(row, 0, [tkt.name_seq,
                                     tkt.name or '',
                                     tkt.mtm_request_id.name_seq or '',
                                     tkt.mtm_request_id.name or '',

                                     tkt.element_id.operator or '',

                                     tkt.equipment_id.name or '',
                                     tkt.categ_id.name or '',
                                     tkt.element_id.code or '',
                                     frequency,

                                     tkt.element_id.freq_maker or '',
                                     tkt.element_id.maker or '',

                                     maintenance_type,
                                     tkt.stage_id.name,
                                     tkt.ticket_type_id.name or '',
                                     task_description,
                                     tkt.mtm_request_id.msj_solution_close or '',
                                     tkt_create_date_tz.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                     tkt_create_date_tz.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                     tkt_create_date_tz.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                                     close_datetime,
                                     ], style_cell_bottom_text)

            # for idx, task in enumerate(ot.task_ids):
            #     if task.timesheet_ids:
            #         sheet.set_row(row, len(task.timesheet_ids) * 15)
            #     sheet.write_row(row, 9, self._get_aux_data(task),
            #                     style_cell_bottom_text if idx == 0 else style_cell_bottom_text2)
            #     row += 1
            # if not ot.task_ids:
            #     sheet.merge_range(row, 9, row, 14, '', style_cell_bottom_text)
            row += 1
        workbook.close()
        excel.seek(0)
        xls_data = excel.getvalue()

        excel.close()
        result = base64.b64encode(xls_data)
        return result

    # def _get_aux_data(self, task):
    #     task_description = ''
    #     if task.description:
    #         task_description = self.env['ir.fields.converter'].text_from_html(task.description)
    #
    #     data = [task.employee_id.name or '',
    #             ', '.join(map(str, task.activity_speciality_ids.mapped('name'))).upper(),
    #             task_description or '']
    #     # SISTEMA
    #     system = ''
    #     for sis in task.activity_id.system_class_id.parent_ids:
    #         system += f"{sis.parent_id.name.upper() if sis.parent_id else ''}\n"
    #     data.append(system.strip())
    #
    #     # COMPONENTE
    #     if task.activity_id.system_class_id and task.activity_id.system_class_id.name:
    #         data.append(
    #             task.activity_id.system_class_id.name.upper().strip() if task.activity_id.system_class_id else '')
    #     else:
    #         data.append('')
    #
    #     # ACTIVIDADES EJECUTADAS
    #     tt = ''
    #     for ts_line in task.timesheet_ids:
    #         tt += f"{ts_line.name.upper().strip() if ts_line.name else ''}\n"
    #     data.append(tt)
    #
    #     return data

    # --------------------------------------- REPORTE 01 FIN---------------------------------------

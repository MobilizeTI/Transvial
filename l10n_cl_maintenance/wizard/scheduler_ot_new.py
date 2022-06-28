# -*- coding: utf-8 -*-
import base64
import io

from odoo import api, models, tools, fields

import logging
import threading
import xlsxwriter
from io import BytesIO
from os.path import expanduser

_logger = logging.getLogger(__name__)


class SchedulerOTNew(models.TransientModel):
    _name = 'scheduler.ot.new'
    _description = 'Run Scheduler OT Manually'

    name_file = fields.Char(string='Nombre del archivo log', readonly=True)
    file_log = fields.Binary(string="Descargar reporte: ", readonly=True)

    def _create_report_xlsx(self):
        OBJ_MR = self.env['maintenance.request'].sudo()
        data_log = OBJ_MR.run_scheduler(get_log=True)
        excel = BytesIO()
        workbook = xlsxwriter.Workbook(excel, {'in_memory': True})
        sheet = workbook.add_worksheet('Log')
        # sheet.set_default_row(20)
        sheet.set_column(0, 1, 15)
        sheet.set_column(2, 2, 60)
        sheet.set_column(3, 3, 10)

        format_title = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'font_name': 'Arial Narrow',
            'text_wrap': True,
            'fg_color': '#4cd137'
        })
        format_cell = workbook.add_format(
            {'border': 1, 'font_name': 'Arial Narrow', 'text_wrap': True, 'font_size': 10, 'bold': 0,
             'font_color': 'black', 'align': 'left'})

        img_data = base64.b64decode(self.env.company.logo)
        image = io.BytesIO(img_data)

        cell_width = 300.0
        image_width = 22000.0
        cols_wide = 90.0
        scale = cell_width * cols_wide / image_width
        sheet.insert_image('A1', 'logo.png', {'image_data': image, 'x_scale': scale, 'y_scale': scale})
        row = 0
        sheet.set_row(row, 20)
        merge_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
            'fg_color': 'white'})
        sheet.merge_range('A1:D3', "RESULTADO DE LA PLANIFICACIÓN AUTOMÁTICA", merge_format)
        row = 3
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        format_link = workbook.add_format(
            {'border': 1, 'font_name': 'Arial Narrow', 'text_wrap': True, 'font_size': 10, 'bold': 1,
             'font_color': 'green', 'align': 'center', 'valign': 'vcenter'})
        sheet.write_row(row, 0, ['BUS', 'TIPO', 'MENSAJE', 'PAUTA'], format_title)
        row += 1
        for i, log in enumerate(data_log):
            bus = log['bus']
            pauta = log['pauta']
            link_bus = f'{base_url}/web#id={bus.id}&action=351&model=maintenance.equipment&view_type=form'
            link_pauta = f'{base_url}/web#id={pauta.id}&action=362&model=maintenance.guideline&view_type=form'

            sheet.write_url(row=row, col=0, url=link_bus, cell_format=format_link, string=bus.name,
                            tip='Enlace al formulario del equipo')
            sheet.write(row, 1, log['result'], format_cell)
            sheet.write(row, 2, log['msj'], format_cell)
            sheet.write_url(row=row, col=3, url=link_pauta, cell_format=format_link, string="clic aquí",
                            tip='Enlace al formulario de la pauta general')
            row += 1

        workbook.close()
        excel.seek(0)
        return base64.b64encode(excel.getvalue())

    def button_run_cron(self):
        file_log = self._create_report_xlsx()
        self.write({"file_log": file_log, "name_file": 'Archivo_log_resultante.xlsx'})
        return {
            'name': 'Ejecutar el planificador de OT',
            "type": "ir.actions.act_window",
            "res_model": "scheduler.ot.new",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }

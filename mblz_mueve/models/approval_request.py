import base64
import difflib
import io
import json

from xlsxwriter import Workbook

from odoo import api, fields, models, tools, _
import datetime

from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    rpt_approver_ids = fields.Text(string='Aprobadores', compute='_compute_rpt_approver_ids')

    @api.depends('approver_ids')
    def _compute_rpt_approver_ids(self):
        for record in self:
            rpt_approver_ids = ''
            if record.approver_ids:
                for approver in record.approver_ids:
                    if approver.date_approved:
                        date_approved = approver.date_approved.strftime(
                            DEFAULT_SERVER_DATETIME_FORMAT)
                        rpt_approver_ids += f"{approver.user_id.name} - {approver._get_str_status(approver.status)} - {date_approved}\n"
                    else:
                        rpt_approver_ids += f"{approver.user_id.name} - {approver._get_str_status(approver.status)}\n"
            record.rpt_approver_ids = rpt_approver_ids

    def _date_to_datetime(self, value, h=0, m=0, s=0):
        date_convert = datetime(
            year=value.year,
            month=value.month,
            day=value.day,
        )
        return date_convert

    def action_update_approved_datetime(self):
        for rec in self.search([('request_status', '=', 'approved')]):
            date_approved = False
            for mjs in rec.message_ids:
                if mjs.tracking_value_ids:
                    tracking_value = mjs.tracking_value_ids[0]
                    if tracking_value.new_value_char and tracking_value.new_value_char == 'Aprobado':
                        date_approved = mjs.date
            rec.date_approved = date_approved

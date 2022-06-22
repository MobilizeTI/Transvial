from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class RptSearchOT(models.Model):
    _name = 'report.search.ot'
    _description = '01 - Reporte de seguimiento de OT'
    _auto = False

    request_id = fields.Many2one(
        'maintenance.request',
        string='Referencia OT',
        readonly=True,
    )

    def get_query(self, dates=False, date=False):
        sql = """select row_number() OVER () as id,
                       mr.id as request_id
                 from maintenance_request as mr """
        sql_where = f"where mr.company_id = {self.env.company.id}"
        if dates:
            date_start, date_end = dates
            sql_where += " AND mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        elif date:
            sql_where += " AND mr.request_date = '{0}'".format(date)
        sql += sql_where
        query = f"create or replace view report_search_ot as ({sql})"
        return query

    def execute_init(self):
        tools.drop_view_if_exists(self._cr, 'report_search_ot')
        query = self.get_query()
        self._cr.execute(query)

    def init(self):
        self.execute_init()

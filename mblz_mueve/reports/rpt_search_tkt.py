from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class RptSearchTkt(models.Model):
    _name = 'report.search.tkt'
    _description = 'Reporte de tickets - con ordenes de trabajo asociadas'
    _auto = False

    ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Ticket',
        readonly=True,
    )

    def get_query(self, ticket_type_id=False, dates=False, date=False):
        sql = """select row_number() OVER () as id,
                       ht.id as ticket_id
                 from helpdesk_ticket as ht """
        if ticket_type_id:
            sql_where = f"where ht.ticket_type_id = {ticket_type_id} and ht.company_id = {self.env.company.id}"
        else:
            sql_where = f"where ht.company_id = {self.env.company.id}"
        if dates:
            date_start, date_end = dates
            sql_where += " AND DATE(ht.create_date) BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        elif date:
            sql_where += " AND DATE(ht.create_date) = '{0}'".format(date)
        sql += sql_where
        query = f"create or replace view report_search_tkt as ({sql})"
        return query

    def execute_init(self):
        tools.drop_view_if_exists(self._cr, 'report_search_tkt')
        query = self.get_query()
        self._cr.execute(query)

    def init(self):
        self.execute_init()

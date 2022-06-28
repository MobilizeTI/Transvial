# -*- coding: utf-8 -*-
import base64
from pprint import pprint

from odoo import http
from odoo.addons.website_helpdesk.controllers.main import WebsiteHelpdesk
from odoo.http import request
from odoo.addons.web.controllers.main import content_disposition


class WebsiteHelpdesk2(WebsiteHelpdesk):

    @http.route(['/helpdesk/', '/helpdesk/<model("helpdesk.team"):team>'], type='http', auth="user", website=True,
                sitemap=True)
    def website_helpdesk_teams(self, team=None, **kwargs):
        user = request.env.user
        if not user.flag_crete_tkt_portal:
            OBJ_CFG = request.env['ir.config_parameter'].sudo()
            email_portal = OBJ_CFG.get_param('mblz_mueve.email_portal')
            # print(email_portal)
            return request.render("mblz_mueve.heldesk_error", {'email_portal': email_portal})

        search = kwargs.get('search')
        # For breadcrumb index: get all team
        teams = request.env['helpdesk.team'].search(
            ['|', '|', ('use_website_helpdesk_form', '=', True), ('use_website_helpdesk_forum', '=', True),
             ('use_website_helpdesk_slides', '=', True)], order="id asc")
        if not request.env.user.has_group('helpdesk.group_helpdesk_manager'):
            teams = teams.filtered(lambda team: team.website_published)
        if not teams:
            return request.render("website_helpdesk.not_published_any_team")
        result = self.get_helpdesk_team_data(team or teams[0], search=search)
        # For breadcrumb index: get all team
        result['teams'] = teams
        result['default_partner_values'] = self._get_partner_data()
        return request.render("website_helpdesk.team", result)

    @http.route(['/ticket/report'], type='http', auth='user', website=True)
    def create_report_mtto(self, redirect=None, **post):
        domain_date = post.get('domain_date', False)
        ticket_type_id = int(post['failure_level_id'])
        if ticket_type_id != 0:
            wz_rpt_vals = {
                'ticket_type_id': ticket_type_id
            }
        else:
            wz_rpt_vals = {}
        if domain_date:
            if domain_date == 'rb_month':  # por mes
                wz_rpt_vals.update({
                    'range': 'month',
                    'month': post['month_in'],
                    'year': post['in_year'],
                })

            elif domain_date == 'rb_dates':  # por fechas
                wz_rpt_vals.update({
                    'range': 'dates',
                    'date_start': post['in_date_start'],
                    'date_end': post['in_date_end'],
                })
            elif domain_date == 'rb_day':  # por día
                wz_rpt_vals.update({
                    'range': 'date',
                    'date_def': post['in_day'],
                })
            else:
                # todos (all)
                wz_rpt_vals.update({
                    'range': 'all',
                })

        # pprint(wz_rpt_vals)
        try:
            wz_rpt_new = request.env['tkt.report.wz'].sudo().create(wz_rpt_vals)
            wz_rpt_new.onchange_range()
            if ticket_type_id == 0:
                wz_rpt_new.ticket_type_id = False
                wz_rpt_new.flag_all = True
            file_xlsx = wz_rpt_new.action_view_screen(web_site=True)
            filename = f'{wz_rpt_new._get_name_rpt()}.xlsx'

            return request.make_response(base64.b64decode(file_xlsx),
                                         [('Content-Type', 'application/octet-stream'),
                                          ('Content-Disposition', content_disposition(filename))])
        except Exception as e:
            print(e)
            return request.render("mblz_mueve.temp_result_wz_report", {'message': str(e)})

# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.web.controllers.main import Home, ensure_db, redirect_with_hash
from odoo.http import request


class MblzHome(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        if kw.get('debug') == "assets" or kw.get('debug') == '1':
            user = request.env.user.browse(request.session.uid)
            # aux = user._is_admin()
            if user and not user.hide_debug_assets_permission and user.id != request.env.ref('base.user_admin').id:
                return redirect_with_hash('/web?debug=0')
        return super(MblzHome, self).web_client(s_action=s_action, **kw)

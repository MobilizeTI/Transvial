# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class WZApprove(models.TransientModel):
    _name = 'wz.approve'
    _description = 'Wizard Approve'

    order_id = fields.Many2one('purchase.order', string='Order reference', required=True)
    comment = fields.Text(string="Comment", required=False)
    flag_approve = fields.Boolean(string='flag_approve', required=False)

    def action_confirm(self):
        line_user = self.order_id.approval_user_ids.filtered(
            lambda l: l.user_id.id == self.env.user.id and l.level == self.order_id.level_actual_approve)
        line_user.comment = self.comment
        if self.flag_approve and line_user:
            line_user.approve = True
            line_user.rejected = False
            self.order_id.update_level_actual_approve()
        else:
            if line_user:
                line_user.approve = False
                line_user.rejected = True
                line_user.active_level = True
                self.order_id.update_level_actual_approve()

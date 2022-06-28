# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    document_approval_id = fields.Many2one('document.approval', string='Document approval default')
    flag_approval_multi = fields.Boolean(string='Is approval multi level', compute='_compute_flag_approval_multi')
    flag_user_approval = fields.Boolean(string='My orders to approve', compute='_compute_flag_approval_multi')

    # flag_admin_approval = fields.Boolean(string='Is user admin', compute='_compute_flag_approval_multi')

    @api.depends('document_approval_id')
    def _compute_flag_approval_multi(self):
        for po in self:
            OBJ_CFG = po.env['ir.config_parameter'].sudo()
            flag_approval_multi = OBJ_CFG.get_param('mblz_purchase_multi_level_approval.po_multi_level_approval')
            po.sudo().flag_approval_multi = flag_approval_multi

            line_user = po.approval_user_ids.filtered(lambda l: l.user_id.id == po.env.user.id and l.level == self.level_actual_approve)
            if line_user:
                flag_user_approval = not line_user.approve
            else:
                flag_user_approval = False
            po.sudo().flag_user_approval = flag_user_approval

    approval_user_ids = fields.One2many('purchase.approval.line', 'order_id',
                                        string='Approvals', readonly=True, copy=True)
    users_approvals = fields.Many2many('res.users', string='users_approvals')

    @api.onchange('amount_total')
    def onchange_amount_total_approvals(self):
        self._set_approvals()

    def _set_approvals(self):
        doc_users = set()
        lines = self.document_approval_id.doc_approval_ids.filtered(lambda l: self.amount_total >= l.amount)
        for record in lines:
            for user in record.user_ids:
                doc_users.add((record.level, user.id))
        data_approvals = []
        self.users_approvals = [(6, 0, [rec[1] for rec in list(doc_users)])]
        for rec in doc_users:
            data_approvals.append(
                (0, 0, {'order_id': self.id, 'level': rec[0], 'user_id': rec[1], 'active_level': rec[0] == 1}))
        self.sudo().update(dict(approval_user_ids=[(6, 0, [])]))
        self.sudo().update(dict(approval_user_ids=data_approvals))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        OBJ_CFG = self.env['ir.config_parameter'].sudo()
        po_multi_level_approval = OBJ_CFG.get_param('mblz_purchase_multi_level_approval.po_multi_level_approval')
        document_approval_id = int(OBJ_CFG.get_param('mblz_purchase_multi_level_approval.document_approval_id'))
        if po_multi_level_approval and document_approval_id:
            res['document_approval_id'] = document_approval_id
        return res

    def action_approve_rfq(self):
        return self.action_down_approve_rfq(approve=True)

    def action_down_approve_rfq(self, approve=False):
        view = self.env.ref('mblz_purchase_multi_level_approval.wz_approve_view_form', False)
        view_id = view and view.id or False
        context = dict(self._context or {})
        context['default_order_id'] = self.id
        context['default_flag_approve'] = approve
        return {
            # 'name': _('Info'),
            'type': 'ir.actions.act_window',
            'res_model': 'wz.approve',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    flag_approve_admin = fields.Boolean(string='Approve for user admin', required=False, copy=False)

    def button_confirm(self):
        if self.flag_approval_multi and not self.is_complete_approve:
            if self.env.user.id in self.document_approval_id.user_admin_ids.ids:
                for line in self.approval_user_ids:
                    line.approve_admin = True
                    self.flag_approve_admin = True
            elif not self.is_complete_approve:
                raise ValidationError(_('The purchase order is pending validation!'))
        return super().button_confirm()

    # barra de programación
    user_approve_percent = fields.Float('Approve percentage', compute='_compute_user_approve_percent',
                                        help='Percentage of users approve')

    @api.depends('approval_user_ids')
    def _compute_user_approve_percent(self):
        for rec in self:
            user_approve_percent = 0
            if rec.approval_user_ids:
                cant_users = len(rec.approval_user_ids)
                count_user_approve = len(rec.approval_user_ids.filtered(lambda l: l.approve))
                value = (count_user_approve / cant_users) * 100
                user_approve_percent = value
            rec.sudo().user_approve_percent = user_approve_percent

    is_complete_approve = fields.Boolean(string='Complete approval', compute='_compute_is_complete_approve')

    # Nivel actual de aprobación
    level_actual_approve = fields.Integer(string='Level actual approve', default=1, copy=False)

    @api.depends('approval_user_ids')
    def _compute_is_complete_approve(self):
        for record in self:
            record.sudo().is_complete_approve = all(record.approval_user_ids.mapped('approve'))

    @api.onchange('level_actual_approve')
    def onchange_level_actual_approve(self):
        if self.level_actual_approve:
            lines_new_level = self.approval_user_ids.filtered(lambda l: l.level == self.level_actual_approve)
            for line in lines_new_level:
                line.active_level = True

    def update_level_actual_approve(self):
        level_actual = self.level_actual_approve
        lines_level_actual = self.approval_user_ids.filtered(lambda l: l.level == level_actual)
        total_lines_level_actual = len(lines_level_actual)

        aux_process = 0

        for line in lines_level_actual:
            if line.approve or line.approve_admin and not line.rejected:
                aux_process += 1
                line.active_level = False
        if total_lines_level_actual == aux_process:
            # listo para el siguiente nivel
            max_level = max(self.approval_user_ids.mapped('level'))
            if level_actual + 1 <= max_level:
                self.level_actual_approve = level_actual + 1
                lines_new_level = self.approval_user_ids.filtered(lambda l: l.level == self.level_actual_approve)
                for line in lines_new_level:
                    line.active_level = True
            else:
                self.level_actual_approve = -1  # significa que ya no hay más niveles que asignar
            # notifica a los usuarios
            self.notify_user_approve()

    # notificar a los usuarios que no han aprobado aún la RFQ
    def notify_user_approve(self):
        # notificar al usuario
        link = f"""
                                <a href="/web#id={self.id}&action=583&model=purchase.order&view_type=form" role="button" target="_blank">{self.name}</a>
                                """
        message = f'Orden de compra ({link}) para su aprobación!'

        users_notify = self.approval_user_ids.filtered(
            lambda
                l: not l.approve and l.user_id.id != self.env.user.id and l.level == self.level_actual_approve and l.active_level)
        print(f'len user notify: {len(users_notify)} users: {users_notify.mapped("user_id.name")}')
        for line in users_notify:
            line.user_id.notify_info(message=message, title=_('Info'), sticky=True)
            self._send_email_approve(user=line.user_id)

    def _send_email_approve(self, user):
        mail_template = self.env.ref('mblz_purchase_multi_level_approval.email_approve_template_edi_purchase', False)
        if mail_template:
            email_values = {
                'email_to': user.email,
            }
            context = dict(self._context or {})
            context.update({
                'email_to': user.email,
                'partner_to': user.partner_id.id,
                'user_id': user.id,
                'user_name': user.name,
            })
            mail_template.with_context(context).send_mail(self.id, force_send=True, email_values=email_values)

    # def copy_data(self, default=None):
    #     return super(PurchaseOrder, self).copy_data(default)

    @api.model
    def create(self, values):
        # Add code here
        po_new = super(PurchaseOrder, self).create(values)
        po_new.onchange_amount_total_approvals()
        po_new.notify_user_approve()
        return po_new


class PurchaseApprovalLine(models.Model):
    _name = 'purchase.approval.line'
    _description = 'Purchase Approval Line'

    level = fields.Integer(string='Level', required=True)
    order_id = fields.Many2one('purchase.order', string='Order reference', required=True,
                               ondelete='cascade',
                               index=True, copy=False)
    user_id = fields.Many2one(comodel_name='res.users', string='Approver', required=True)
    approve = fields.Boolean(string='Approve user', required=False, copy=False)
    approve_admin = fields.Boolean(string='Approve Admin', required=False, copy=False)
    rejected = fields.Boolean(string='Rejected', required=False, copy=False)
    comment = fields.Text(string="Comment user", required=False, copy=False)
    active_level = fields.Boolean(string='Active', required=False, copy=False)

    @api.onchange('approve', 'approve_admin')
    def onchange_method(self):
        if self.approve or self.approve_admin:
            self.rejected = False

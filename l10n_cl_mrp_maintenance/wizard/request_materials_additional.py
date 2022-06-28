# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RequestMaterialsAdditional(models.Model):
    _name = 'request.materials.additional'
    _description = 'Request Materials Additional'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)

    # Lista de materiales adicionales
    task_id = fields.Many2one('maintenance.request.task', string='Task', required=False)
    product_line_ids = fields.One2many('task.line.materials',
                                       'wz_material_add_id', 'Product Lines', copy=True)

    approval_reason = fields.Text(string='Approval reason', required=True)

    def action_create(self):
        def _get_category_approve(amount):
            code_categ = 'RMA1'
            if amount >= 150000 and amount < 400000:
                code_categ = 'RMA2'
            elif amount >= 400000 and amount < 1000000:
                code_categ = 'RMA3'
            elif amount >= 1000000 and amount < 10000000:
                code_categ = 'RMA4'
            elif amount >= 10000000:
                code_categ = 'RMA5'

            category_id = self.env['approval.category'].sudo().search(
                [('sequence_code', '=', code_categ), ('company_id', '=', self.company_id.id)],
                limit=1)
            if not category_id:
                raise ValidationError(
                    f'No exíste la categoría de aprobación Materiales Adicionales ({code_categ}) con código RMA para la companía {self.company_id.name}')
            return category_id

        if len(self.product_line_ids) > 0:
            amount = sum(self.product_line_ids.mapped('price_total'))
            category_id = _get_category_approve(amount)

            approval_request = self.env['approval.request'].sudo()
            current_date = fields.Datetime.now()
            partner_id = self.task_id.user_id.partner_id.id
            name_seq = self.task_id.name_seq
            if not name_seq:
                name_seq = f"({self.task_id.name.split('(')[1]}"
            else:
                name_seq = f'({self.task_id.name_seq})'
            approval_vals = {
                'name': f'Solicitud de materiales {name_seq}',
                'category_id': category_id.id,
                'date': current_date,
                'partner_id': partner_id,
                'request_task_id': self.task_id.id,
                'wz_material_add_id': self.id,
                'reason': self.approval_reason,
                'company_id': self.company_id.id,
                'amount': amount
            }
            try:
                approval_request_new = approval_request.create(approval_vals)
                approval_request_new.sudo()._onchange_category_id()
                approval_request_new.sudo().action_confirm()
                self.sudo().task_id.approval_ids = [(4, approval_request_new.id)]
            except Exception as e:
                lines_material_additional = self.env['task.line.materials'].search(
                    [('task_id', '=', self.task_id.id), ('approval_request_id', '=', False)])
                lines_material_additional.unlink()
                self._cr.commit()
                raise ValidationError(str(e))
            # self.state_approval = 'to approve'
            # return True
        else:
            raise ValidationError(_('Material requested list empty!'))

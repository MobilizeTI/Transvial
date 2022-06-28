import base64
import difflib
import io
import json

from xlsxwriter import Workbook

from odoo import api, fields, models, tools, _
import datetime

from odoo.exceptions import UserError, ValidationError


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    group_ids = fields.Many2many('res.groups', string='Groups')


class ApprovalApprover(models.Model):
    _inherit = 'approval.approver'

    date_approved = fields.Datetime(string="Fecha de aprobación", readonly=True)

    def _get_str_status(self, status):
        str_status = 'A enviar'
        if status == 'approved':
            str_status = 'Aprobado'
        elif status == 'pending':
            str_status = 'Por aprobar'
        elif status == 'refused':
            str_status = 'Rechazado'
        elif status == 'cancel':
            str_status = 'Cancelado'
        return str_status

    def name_get(self):
        return [
            (record.id, f"{record.user_id.name} {record._get_str_status(record.status)} {record.date_approved or ''}")
            for record in self]


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    request_task_id = fields.Many2one('maintenance.request.task', 'Task request')
    request_task_equipment_id = fields.Many2one('maintenance.equipment', 'Bus',
                                                related='request_task_id.request_id.equipment_id')
    wz_material_add_id = fields.Many2one('request.materials.additional', 'Wz Materials Additional')
    product_line_task_ids = fields.Many2many('task.line.materials', compute='_compute_product_line_task_ids')
    product_line_task_txt = fields.Text('Componentes', compute='_compute_product_line_task_ids')
    picking_task_mtto_id = fields.Many2one('stock.picking', string='Picking de tarea MTTO', required=False)
    date_approved = fields.Datetime(string="Fecha de aprobación", readonly=True)

    @api.depends('request_task_id', 'wz_material_add_id')
    def _compute_product_line_task_ids(self):
        for rec in self:
            if rec.request_task_id and rec.wz_material_add_id:
                materials = rec.request_task_id.product_line_ids.filtered(
                    lambda l: l.wz_material_add_id.id == rec.wz_material_add_id.id)
                if materials:
                    rec.product_line_task_ids = [(6, 0, materials.ids)]
                    product_line_task_txt = ''
                    for m in materials:
                        product_line_task_txt += f"{m.product_id.name}\n"
                    rec.product_line_task_txt = product_line_task_txt

                else:
                    rec.product_line_task_ids = [(6, 0, [])]
                    rec.product_line_task_txt = False
            else:
                rec.product_line_task_ids = [(6, 0, [])]
                rec.product_line_task_txt = False

    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.mapped('approver_ids').filtered(
                lambda approver: approver.user_id == self.env.user
            )
        approver.write({'status': 'approved', 'date_approved': fields.Datetime.now()})
        self.sudo()._get_user_approval_activities(user=self.env.user).action_feedback()
        self.date_approved = fields.Datetime.now()
        if self.request_status == 'approved' and self.request_task_id:
            self.create_picking()

    def action_cancel(self):
        super(ApprovalRequest, self).action_cancel()
        self._validate_picking_task_mtto()

    def action_refuse(self):
        super(ApprovalRequest, self).action_refuse()
        self._validate_picking_task_mtto()

    def _validate_picking_task_mtto(self):
        if self.picking_task_mtto_id and self.picking_task_mtto_id.state not in ('done', 'cancel'):
            raise ValidationError(
                f'Tiene un picking ({self.picking_task_mtto_id.name}) abierto asociado a esta solicitud de aprobación')

    def action_withdraw(self):
        super(ApprovalRequest, self).action_withdraw()
        self._validate_picking_task_mtto()

    def create_picking(self):
        # se crea el picking con la solicitud aprovada
        obj_stock_picking = self.env['stock.picking'].sudo()

        # Se crea una transferencia salida de sl-tienda ->OUT
        wh_default = self.env.ref('stock.warehouse0')

        picking_type_id = self.env['stock.picking.type'].sudo().search(
            [('code', '=', 'outgoing'),
             ('sequence_code', '=', 'OUT'),
             ('company_id', '=', self.company_id.id),
             ('warehouse_id', '=', wh_default.id)], limit=1)
        location_id = self.env.ref('stock.stock_location_stock').id
        location_dest_id = self.request_task_id.request_maintenance_location_id.id

        moves = []
        for line in self.product_line_task_ids:
            moves.append((0, 0, {
                'name': line.product_id.name,
                'product_uom': line.product_uom_id.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'system_class_id': line.system_class_id.id,
                'company_id': self.company_id.id,
                'picking_type_id': picking_type_id.id,
            }))

        # fixme:// No se se añade el el partner por el requerimiento Exclusivo para mueve -> [MUEV-381] Asociado en OUT inventarios / Contabilidad
        values = {
            'partner_id_aux': self.request_task_id.user_id.partner_id.id,
            'picking_type_id': picking_type_id.id,
            'flag_from_mtto': 'not-process',
            'origin': self.request_task_id.request_id.name_seq,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_ids_without_package': moves,
        }

        stock_picking = obj_stock_picking.create(values)

        if stock_picking.exists():
            stock_picking.action_confirm()
            stock_picking.action_assign()
        #     wiz = self.env['stock.immediate.transfer'].create({'pick_ids': [(4, stock_picking.id)]})
        #     wiz.process()
        self.request_task_id.picking_ids = [(4, stock_picking.id)]
        self.request_task_id.request_id.picking_ids = [(4, stock_picking.id)]
        self.picking_task_mtto_id = stock_picking.id

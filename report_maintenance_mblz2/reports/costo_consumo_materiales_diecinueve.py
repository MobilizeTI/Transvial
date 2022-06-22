from odoo import fields, models, api, _, tools
from datetime import timedelta

from odoo.exceptions import Warning


class ReportMaterialConsumptionCost(models.Model):
    _name = 'report.material.consumption.cost'
    _description = 'Costo consumo materiales'
    _auto = False

    request_id = fields.Many2one(
        'maintenance.request',
        string='Referencia OT',
        readonly=True,
    )
    equipment_id = fields.Many2one(
        'maintenance.equipment',
        string='Equipo',
        readonly=True,
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        readonly=True,
    )

    license_plate = fields.Char(
        string='Matrícula',
        related='vehicle_id.license_plate',
    )

    category_id = fields.Many2one(
        'maintenance.equipment.category',
        string='Tipología',
        readonly=True,
    )

    request_date = fields.Date(
        string='Fecha detención', readonly=True
    )

    close_date = fields.Date(
        string='Fecha liberación',
        readonly=True
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking', readonly=True
    )

    pk_state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Esperando otra operación'),
        ('confirmed', 'En espera'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Estado del Pk.', related='picking_id.state')

    stock_move_id = fields.Many2one(
        'stock.move',
        string='Move', readonly=True
    )
    sm_product_id = fields.Many2one(
        'product.product',
        string='Producto', readonly=True
    )

    sm_product_name = fields.Char(
        string='Producto',
        related='sm_product_id.name',
    )

    sm_product_default_code = fields.Char(
        string='Código',
        related='sm_product_id.default_code',
    )

    sm_product_uom_qty = fields.Float(
        string='Cantidad',
        related='stock_move_id.product_uom_qty')

    sm_uom_id = fields.Many2one(
        'uom.uom',
        string='UoM', related='sm_product_id.uom_id'
    )

    sm_product_account = fields.Char(
        string='Cuenta', related='sm_product_id.categ_id.property_stock_valuation_account_id.code'
    )

    amount = fields.Float(string='Costo de material', compute='_compute_amount')

    @api.depends('stock_move_id', 'sm_product_id')
    def _compute_amount(self):
        for record in self:
            if record.stock_move_id:
                record.amount = record.sm_product_id.standard_price * record.stock_move_id.quantity_done
            else:
                record.amount = 0

    company_id = fields.Many2one(
        'res.company',
        string='Unidad de negocio', readonly=True
    )

    company_name = fields.Char(
        string='Unidad de negocio',
        related='company_id.name',
    )

    def get_query(self, dates=False, date=False):
        sql = """
            select row_number() OVER ()    as id,
                   mr.id                   as request_id,
                   mr.close_date           as close_date,
                   mr.equipment_id         as equipment_id,
                   me.vehicle_id           as vehicle_id,
                   me.category_id          as category_id,
                   mr.request_date         as request_date,
                   sp.id                   as picking_id,
                   sm.id                   as stock_move_id,
                   sm.product_id           as sm_product_id,
                   mr.company_id           as company_id
            from maintenance_request as mr
                     inner join maintenance_equipment as me on me.id = mr.equipment_id
                     inner join fleet_vehicle as fv on fv.id = me.vehicle_id
                     inner join maintenance_request_type as mrtype on mrtype.id = mr.type_ot
                     inner join stock_picking as sp on sp.maintenance_id = mr.id
                     inner join stock_move sm on sp.id = sm.picking_id
        """

        sql_where = "where sm.state in ('done')"
        if dates:
            date_start, date_end = dates
            sql_where += " and mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += " and mr.request_date = '{0}'".format(date)
        sql += sql_where

        query = f"create or replace view report_material_consumption_cost as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_material_consumption_cost')
        query = self.get_query()
        self._cr.execute(query)

    def get_act_window(self, data):
        if data['opc'] == 'dates':
            query = self.get_query(dates=data['dates'])
        elif data['opc'] == 'date':
            query = self.get_query(date=data['date'])
        else:
            query = self.get_query()
        self.env.cr.execute(query)
        if self.search_count([]) == 0:
            raise Warning('!No existe datos, para el filtro ingresado!')
        view_tree = self.env.ref('report_maintenance_mblz2.report_material_consumption_cost_tree')
        view_pivot = self.env.ref('report_maintenance_mblz2.report_material_consumption_cost_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.report_material_consumption_cost_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'report.material.consumption.cost',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard'),
                      ],
            'view_id': view_tree.id,
            'target': 'current',
            'context': {
                "search_default_groupby_request": True,
                "search_default_groupby_picking": True,
            }
        }

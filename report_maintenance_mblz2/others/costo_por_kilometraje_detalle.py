# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _, tools
from datetime import timedelta
from odoo.exceptions import Warning


class CostoPorKilometraje(models.Model):
    _name = 'costo.por.kilometraje.detalle'
    _description = '1-21 costo por kilometraje'
    _auto = False

    equipo = fields.Many2one('maintenance.equipment', string='Equipo', readonly=True, )
    license_plate = fields.Char(string='Matricula', readonly=True, )
    category_id = fields.Many2one('maintenance.equipment.category', string='Tipología', readonly=True, )
    odometer_actual = fields.Float(string='Kilometraje', readonly=True, )
    unit = fields.Char(string='Unidad', readonly=True, )
    costo_total = fields.Float(string='Costo', readonly=True, )
    costo_km = fields.Float(compute='_costo_km', string='Costo por KM', readonly=True, )
    fecha_registro = fields.Date(string='Fecha registro', readonly=True, )
    company_id = fields.Many2one('res.company', string='Unidad de negocio', readonly=True, )

    @api.depends('odometer_actual')
    def _costo_km(self):
        for rec in self:
            res = 0
            if rec.odometer_actual > 0:
                res = (rec.costo_total / rec.odometer_actual)
            rec.costo_km = res

    def get_query(self, dates=False, date=False):
        sql_where = ""
        if dates:
            date_start, date_end = dates
            sql_where += "WHERE mr.request_date BETWEEN '{0}' AND '{1}'".format(date_start, date_end)
        if date:
            sql_where += "WHERE mr.request_date = '{0}'".format(date)

        sql = """
                SELECT row_number() OVER() as id, 
                    me.id AS equipo, 
                    me.category_id,
                    fv.license_plate, 
                    fv.company_id,
                    --ABS(svl.value) AS costo_total,
                    ABS(SUM(svl.value)) AS costo_total,
                    T1.value AS odometer_actual,
                    (CASE fv.odometer_unit WHEN 'kilometers' THEN 'KM' END) AS unit,
                    T1.date AS fecha_registro
                FROM maintenance_request AS mr 
                    INNER JOIN stock_picking AS sp ON sp.maintenance_id=mr.id
                    INNER JOIN stock_move AS sm ON sm.picking_id=sp.id
                    INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id=sm.id
                    INNER JOIN maintenance_equipment AS me ON me.id=mr.equipment_id
                    INNER JOIN fleet_vehicle AS fv ON fv.id=me.vehicle_id
                    INNER JOIN (SELECT vehicle_id, MAX(value) AS value, MAX(date) AS date FROM fleet_vehicle_odometer GROUP BY vehicle_id) AS T1 ON T1.vehicle_id=fv.id                        
                    {0}
                GROUP BY me.id, me.category_id, fv.license_plate, fv.company_id, odometer_actual, fecha_registro, unit, fv.id
            """.format(sql_where)

        query = f"create or replace view costo_por_kilometraje_detalle as ({sql})"

        return query

    def init(self):
        tools.drop_view_if_exists(self._cr, 'costo_por_kilometraje_detalle')
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
        view_tree = self.env.ref('report_maintenance_mblz2.costo_por_kilometraje_detalle_tree')
        view_graph = self.env.ref('report_maintenance_mblz2.costo_por_kilometraje_detalle_graph')
        view_pivot = self.env.ref('report_maintenance_mblz2.costo_por_kilometraje_detalle_pivot')
        view_dashboard = self.env.ref('report_maintenance_mblz2.costo_por_kilometraje_detalle_dashboard')

        return {
            'name': data['name'],
            'type': 'ir.actions.act_window',
            'res_model': 'costo.por.kilometraje.detalle',
            'view_mode': 'tree,dashboard',
            'views': [(view_tree.id, 'tree'),
                      (view_graph.id, 'graph'),
                      (view_pivot.id, 'pivot'),
                      (view_dashboard.id, 'dashboard')],
            'view_id': view_tree.id,
            # 'domain': [],
            'target': 'current',
            'context': {}
        }

# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _
from datetime import timedelta
from odoo.exceptions import Warning


class CostoPorKilometraje(models.Model):
    _name = 'costo.por.kilometraje'
    _auto = False

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipo', readonly=True, )
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

    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW costo_por_kilometraje AS (
            SELECT row_number() OVER() as id, 
            me.id AS equipment_id, me.category_id,
            fv.license_plate, fv.company_id,
            ABS(SUM(svl.value)) AS costo_total,
            (SELECT value FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id ORDER BY fvo.date DESC LIMIT 1) AS odometer_actual,
            (CASE fv.odometer_unit WHEN 'kilometers' THEN 'KM' END) AS unit, 
            (SELECT date FROM fleet_vehicle_odometer fvo WHERE fvo.vehicle_id=fv.id ORDER BY fvo.date DESC LIMIT 1) AS fecha_registro
            FROM maintenance_request AS mr 
            INNER JOIN stock_picking AS sp ON sp.maintenance_id=mr.id
            INNER JOIN stock_move AS sm ON sm.picking_id=sp.id
            INNER JOIN stock_valuation_layer AS svl ON svl.stock_move_id=sm.id
            INNER JOIN maintenance_equipment AS me ON me.id=mr.equipment_id
            INNER JOIN fleet_vehicle AS fv ON fv.id=me.vehicle_id
            --WHERE sp.state = 'done' AND mr.equipment_id = 1108
            GROUP BY me.id, me.category_id, fv.license_plate, fv.company_id, odometer_actual, fecha_registro, unit

            )""")

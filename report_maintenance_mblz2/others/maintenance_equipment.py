# Copyright YEAR(S), AUTHOR(S)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models, api, _
from datetime import timedelta
from odoo.exceptions import Warning


class MaintenanceEquipmentDetails(models.Model):
    _name = 'maintenance.equipment.details'
    _description = '1-3'
    _auto = False

    name = fields.Char(
        string='Equipo',
        readonly=True,
    )
    license_plate = fields.Char(
        string='Matricula',
        readonly=True,
    )
    category_id = fields.Many2one(
        'maintenance.equipment.category',
        string='Tipología',
        readonly=True,
    )
    value = fields.Float(
        string='Odómetro',
        readonly=True,
    )
    unit = fields.Char(
        string='Unidad',
        readonly=True,
    )
    date = fields.Date(
        string='Fecha Registro',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Unidad de negocio',
        readonly=True,
    )

    def init(self):
        self._cr.execute("""
            CREATE OR REPLACE VIEW maintenance_equipment_details AS (
            SELECT row_number() OVER() as id,
            me.name,me.category_id,fv.license_plate,fv.company_id, fv.odometer_unit AS unit, 
            (SELECT date FROM fleet_vehicle_odometer AS fvo WHERE fvo.vehicle_id=me.vehicle_id ORDER BY fvo.date DESC LIMIT 1) AS date,
            (SELECT value FROM fleet_vehicle_odometer AS fvo WHERE fvo.vehicle_id=me.vehicle_id ORDER BY fvo.date DESC LIMIT 1) AS value
            FROM maintenance_equipment me 
            INNER JOIN fleet_vehicle AS fv ON fv.id=me.vehicle_id
            )""")

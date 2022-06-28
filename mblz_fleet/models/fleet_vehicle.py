from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    def open_fuel_logs(self):
        action = self.env.ref('mblz_fleet.mblz_fleet_vehicle_fuel_log2_act_window').read()[0]
        logs = self.env['vehicle.fuel.log'].sudo().search([('vehicle_id', '=', self.id)])
        context = dict(self._context, create=True)
        context.update({'default_vehicle_id': self.id})
        action['context'] = context
        if len(logs) > 1:
            action['domain'] = [('id', 'in', logs.ids)]

        else:
            form_view = [(self.env.ref('mblz_fleet.mblz_fleet_vehicle_fuel_log_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            if logs:
                action['res_id'] = logs.id
        return action
        # self.ensure_one()
        # return {
        #     'type': 'ir.actions.act_window',
        #     'name': 'Vehicle fuel log',
        #     'view_mode': 'tree',
        #     'res_model': 'vehicle.fuel.log',
        #     'domain': [('vehicle_id', '=', self.id)],
        #     'context': {'default_vehicle_id': self.id}
        # }

    def get_odoo_dates(self, date_start, date_end):
        sql = """
            SELECT sum(fvo.value_dif) as value_odoo
                FROM fleet_vehicle_odometer as fvo 
            WHERE  fvo.date BETWEEN '{0}' AND '{1}' AND fvo.vehicle_id = {2}
        """.format(date_start, date_end, self.id)
        # print(sql)
        self._cr.execute(sql)
        sum_odoo = self._cr.dictfetchone()
        # print(sum_odoo)
        # odometers = self.env['fleet.vehicle.odometer'].sudo().search([('vehicle_id', '=', self.id)])
        # odoo_total = sum(odometers.filtered(lambda l: date_start <= l.date <= date_end).mapped('value_dif'))
        return sum_odoo.get('value_odoo', 0)

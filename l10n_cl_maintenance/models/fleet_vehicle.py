from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, Warning


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipment',
                                   ondelete='cascade', index=True, check_company=True, copy=False)

    maintenance_count = fields.Integer(related='equipment_id.maintenance_count')

    assigned_equipment_id = fields.Boolean(
        string=' assigned_equipment_id',
        compute='_compute_assigned_equipment_id')

    def _compute_assigned_equipment_id(self):
        for record in self:
            if not record.equipment_id:
                equipment = record.env['maintenance.equipment'].sudo().search(
                    [('vehicle_id', '=', record.id), ('company_id', '=', record.env.company.id)], limit=1)
                if equipment:
                    record.equipment_id = equipment.id
            record.assigned_equipment_id = True

    def return_action_to_open(self):
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        opc_maintenance = self.env.context.get('opc_maintenance', False)
        if opc_maintenance:
            if xml_id:
                res = self.env['ir.actions.act_window']._for_xml_id('maintenance.%s' % xml_id)
                res.update(
                    context=dict(self.env.context, default_equipment_id=self.equipment_id.id, group_by=False),
                    domain=[('equipment_id', '=', self.equipment_id.id)]
                )
                return res
            return False
        else:
            return super(FleetVehicle, self).return_action_to_open()
    #
    # @api.onchange('odometer')
    # def onchange_odometer(self):
    #     if self.equipment_id:
    #         self.equipment_id.action_is_reiterative()

    def get_dates_ot_reiteratives(self):
        """
            Devuelve la fecha de inicio y fín de un rango de 15000 km acumulados
        @return:date_start: fecha de inicio
                date_end: fecha de fin
        """
        odometers = self.env['fleet.vehicle.odometer'].sudo().search([('vehicle_id', '=', self.id)], order='date desc')
        odoo_filter = []
        sum_odoo = 0
        max_odoo = self.odometer
        for odoo in odometers:
            if sum_odoo < 15000:
                # sum_odoo += max_odoo - odoo.value
                # max_odoo = odoo.value
                sum_odoo += odoo.value_dif  # value_dif -> registrado en el módulo mblz_fleet
                odoo_filter.append(odoo)
            else:
                break

        date_start = False
        date_end = False
        if len(odoo_filter) >= 2 and sum_odoo >= 15000:
            date_start = odometers[-1].date
            date_end = odometers[0].date
        # print(date_start, date_end)
        return date_start, date_end

# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MTMRequestTaskWZ(models.TransientModel):
    _name = 'mtm.request.task.wz'
    _description = 'Add multiple task employee'

    option = fields.Selection(
        string='Seleccione',
        selection=[('assign', 'Asignación Masiva'),
                   ('close', 'Cierre Masivo'), ],
        required=True, default='assign')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Empleado responsable')

    # empleados adicionales
    employee_additional_ids = fields.Many2many('hr.employee', string='Empleados adicionales')

    task_ids = fields.Many2many('maintenance.request.task', string='Tasks')
    task_close_ids = fields.Many2many('maintenance.request.task',
                                      'wz_close_task', 'activity_id',
                                      compute='_compute_task_close_ids')

    description = fields.Text('Descripción', help='Descripción para cierre')

    @api.depends('task_ids')
    def _compute_task_close_ids(self):
        for record in self:
            if record.task_ids:
                record.task_close_ids = [
                    (6, 0, record.task_ids.filtered(lambda t: t.alert_close_task == False and t.stage_id.id != 2).ids)]
            else:
                record.task_close_ids = [(6, 0, [])]

    count_task_ids = fields.Integer(string='Quantity of tasks', compute='_compute_count_task_ids')

    @api.depends('task_ids')
    def _compute_count_task_ids(self):
        for rec in self:
            rec.count_task_ids = len(rec.task_ids) if rec.task_ids else 0

    specialty_tag_ids = fields.Many2many("hr.specialty.tag", string="Specialities",
                                         compute='_compute_specialty_tag_ids')

    @api.depends('task_ids')
    def _compute_specialty_tag_ids(self):
        for rec in self:
            if rec.task_ids:
                specialty_tag_ids = []
                for task in rec.task_ids:
                    specialty_tag_ids += task.activity_speciality_ids.ids
                rec.specialty_tag_ids = [(6, 0, list(set(specialty_tag_ids)))]
            else:
                rec.specialty_tag_ids = [(6, 0, [])]

    @api.onchange('specialty_tag_ids')
    def onchange_partner_id(self):
        for rec in self:
            employee_ids = []
            if rec.specialty_tag_ids:
                domain = [('speciality_ids', '!=', []), ('company_id', '=', self.company_id.id),
                          ('user_id', '!=', False)]
                employees = self.env['hr.employee'].sudo().search(domain)
                for employee in employees:
                    if set(rec.specialty_tag_ids.ids).issubset(set(employee.speciality_ids.ids)):
                        employee_ids.append(employee.id)
            if employee_ids:
                return {'domain': {'employee_id': [('id', '=', employee_ids)]}}
            else:
                raise ValidationError(
                    f"No existe un empleado con usuario asignado que tenga las especialidades: {', '.join(map(str, rec.specialty_tag_ids.mapped('name')))} para la compañía {rec.company_id.name}")

    def btn_confirm(self):
        self.ensure_one()
        if self.option == 'assign':
            for task in self.task_ids:
                task.write({
                    'employee_id': self.employee_id.id,
                    'employee_additional_ids': [(6, 0, self.employee_additional_ids.ids)]
                })
                task.update_is_complete_task()

        else:
            if self.task_close_ids:
                self.task_close_ids.write({'stage_id': 2, 'description': self.description})
            else:
                raise ValidationError('¡No existe ninguna tarea seleccionada que se pueda cerrar!')

from odoo import _, api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    code = fields.Char(string='Código', required=False)

    _sql_constraints = [
        ('unique_code', 'unique (code)', 'El código del departamento debe ser unico'),
    ]


class HrJob(models.Model):
    _inherit = 'hr.job'

    can_create_ot = fields.Boolean(string='Puede crear OT', required=False,
                                   help='Valor para filtrar los empleados que pueden crear OT')


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # code_dep_emp = fields.Char(string='Código del departamento', related='department_id.code')
    can_create_ot = fields.Boolean(string='Puede crear OT', related='job_id.can_create_ot',
                                   help='Valor para filtrar los empleados que pueden crear OT')

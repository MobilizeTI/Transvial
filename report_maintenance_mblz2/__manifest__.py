# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Maintenance Details Report MBLZ (v2)',
    'sequence': 10,
    'description': """
        Maintenance Details Report
    """,
    'website': "https://www.mobilize.cl",
    'category': 'Mobilize/Apps',
    'version': '1.1',
    'depends': ['fleet', 'maintenance',
                'l10n_cl_maintenance', 'l10n_cl_mrp_maintenance', 'web_group_expand',
                'maintenance_request_stage_transition', 'mblz_mueve' , 'maintenance_request_stage_transition',
                'purchase', 'purchase_open_qty'],
    'data': [
        'security/ir.model.access.csv',
        'views/templates.xml',

        'wizard/mtto_report_wizard.xml',
        'wizard/show_message_mtto.xml',

        'views/mblz_stock_quant_views.xml',
        'views/template_report_typeot.xml',

        'reports/buses_overhaul_veintiocho.xml',
        'reports/buses_detenidos_dies.xml',
        'reports/costo_consumo_materiales_dicinueve.xml',
        'reports/trabajos_diferidos_o_reprogramado_treinta_y_ocho.xml',
        'reports/q_fallas_sistema_SIRCI.xml',
        'reports/fallas_tecnicas_reiterativas_treinta_y_seis.xml',
        'reports/buses_con_falla_operacionales_cuatenta_y_dos.xml',
        'reports/inconfiabilidad_tecnica_de_la_flota.xml',
        'reports/fallas_ITS_por_equipos.xml',

        'others/maintenance_view.xml',  # 1-25
        'others/maintenance_equipment_view.xml',  # 1-3
        'others/maintenance_request_preventive_view.xml',  # 1-24
        'others/cumplimiento_mtto_preventivo_view.xml',  # 1-26 1-27 1-41
        'others/inhabilitacion_tecnica_view.xml',  # 1-43

        'others/productividad_mantenimiento_view.xml',  # 1-32 1-33
        'others/vencimiento_mtto_programado_view.xml',  # 1-12
        'others/costo_por_kilometraje_detalle_view.xml',  # 1-21

        # reporte 73
        'views/purchase.xml',

        'data/report.mtto.type.csv'

    ],
    'demo': [],
    'qweb': [
        "static/src/xml/tree_view_button.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

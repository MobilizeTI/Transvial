# -*- coding: utf-8 -*-
{
    'name': "MBLZ: Mueve",

    'description': """
       Customizaciones Mueve by MBLZ
   """,
    'summary': 'Customizaciones Mueve by MBLZ',
    'website': "https://www.mobilize.cl",
    'category': 'Mobilize/Apps',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['helpdesk',
                'website_helpdesk_form',
                'helpdesk_timesheet',
                'website',
                'fleet',
                'maintenance',
                'l10n_cl_maintenance',
                'mail',
                'purchase',
                'account',
                'project',
                'hr_timesheet',
                'product_code_unique',
                'report_xlsx',
                'html_text',
                'partner_vat_unique',
                'maintenance_request_stage_transition',
                'mblz_access_control',
                'l10n_cl_mrp_maintenance',
                'stock_account',
                'api_simple_layer'
                ],

    # always loaded
    'data': [
        'security/security.xml',
        'security/purchase_security.xml',
        'security/inventory_security.xml',

        'security/ir.model.access.csv',
        'data/ir.model.access.csv',

        'data/sequences.xml',
        'data/mail_data.xml',

        'views/assets.xml',  # para el portal

        'views/helpdesk_ticket.xml',
        'views/helpdesk_sla.xml',
        'views/helpdesk_failure_level.xml',
        # 'views/helpdesk_support_activity.xml',
        'views/helpdesk_support_level.xml',
        'views/maintenance_request.xml',
        'views/res_users.xml',

        'views/helpdesk_categorization.xml',
        'views/helpdesk_ticket_master.xml',
        'views/res_partner.xml',

        'wizard/close_tks_massive.xml',
        'wizard/close_tks_massive_aux.xml',
        'wizard/tkt_report_wizard.xml',
        'wizard/stage_solution_wizard.xml',

        'data/system_its_default.xml',
        # 'data/helpdesk.categ.element.csv',
        # 'data/helpdesk_categ_category.xml',

        # 'data/helpdesk.failure.level.csv',
        # 'data/helpdesk.ticket.type.csv',
        # 'data/helpdesk.sla.csv',
        # 'data/helpdesk.stage.csv',
        'data/helpdesk.tag.csv',

        'reports/helpdesk_ticket.xml',

        'views/template_helpdesk.xml',

        'views/settings.xml',
        # 'reports/monthly_tickets_pdf.xml',
        # 'views/views.xml',
        # 'views/templates.xml',
        # 'reports/assets.xml',
        'reports/templates/ot_header.xml',
        'reports/templates/ot_body.xml',
        'reports/mtn_request_ot.xml',

        'reports/all/rpt_01.xml',

        # update report purchase
        'reports/purchase/purchase_order_template_mueve.xml',
        'reports/purchase/report_purchaseorder_document.xml',
        # 'data/functions.xml',

        # control de accesso
        'views/purchase.xml',
        'views/inventory.xml',
        'views/inventoty_templates.xml',
        'views/approval.xml',
        'views/hr.xml',

        # 'data/hr.department.csv',
        'data/hr.job.csv',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],

    'images': ['static/description/icon.png'],

    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'AGPL-3',
}

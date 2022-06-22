odoo.define('report_maintenance_mblz2.tree_view_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var rpc = require('web.rpc');

    var includeDict = {
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.modelName == 'report.fleet.technical.unreliability') {
                var btn_view_kpi = this.$buttons.find('button.o_list_button_custom_print');
                btn_view_kpi.on('click', this.proxy('btn_view_kpi_13_14'));
            }
            if (this.modelName == 'report.equipment.its.failures') {
                var btn_view_kpi = this.$buttons.find('button.o_list_button_custom_print2');
                btn_view_kpi.on('click', this.proxy('btn_view_kpi_55'));
            }
        },
        btn_view_kpi_13_14: function () {
            rpc.query({
                model: 'report.fleet.technical.unreliability',
                method: 'action_view_kpi',
                args: [false, true],
            });
        },
        btn_view_kpi_55: function () {
            rpc.query({
                model: 'report.equipment.its.failures',
                method: 'action_view_kpi',
                args: ['55', true],
            });
        }
    };

    ListController.include(includeDict);
});

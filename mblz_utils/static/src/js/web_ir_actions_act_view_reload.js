odoo.define("mblz_utils.ir_actions_act_view_reload", function (
    require
) {
    "use strict";

    var ActionManager = require("web.ActionManager");

    ActionManager.include({
        /**
         * Intercept action handling to detect extra action type
         * @override
         */
        _handleAction: function (action, options) {
            if (action.type === "ir.actions.act_view_reload") {
                return this._executeReloadAction(action, options);
            }

            return this._super.apply(this, arguments);
        },

        /**
         * Handle 'ir.actions.act_view_reload' action
         * @returns {Promise} Resolved promise
         */
        _executeReloadAction: function () {
            var controller = this.getCurrentController();
            if (controller && controller.widget) {
                controller.widget.reload();
            }

            return Promise.resolve();
        },
    });
});

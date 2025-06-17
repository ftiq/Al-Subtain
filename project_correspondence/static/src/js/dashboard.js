odoo.define('correspondence.dashboard', function (require) {
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var rpc = require('web.rpc');
    var registry = require('web.action_registry');

    var Dashboard = AbstractAction.extend({
        template: 'project_correspondence.DashboardTemplate',
        init: function (parent, action) {
            this._super(parent, action);
            this.cards = [
              { state: 'internal', label: 'صادر داخلي' },
              { state: 'external', label: 'صادر خارجي' },
              { state: 'tech',     label: 'صادر فني'   },
              { state: 'incoming', label: 'وارد'       },
            ];
        },
        start: function () {
            var self = this;
            return Promise.all(this.cards.map(function(card) {
                return rpc.query({
                    model: 'project.correspondence',
                    method: 'search_count',
                    args: [[['state','=',card.state]]],
                }).then(function(count) {
                    card.count = count;
                });
            })).then(function() {
                self.renderElement();
            });
        },
        events: {
            'click .o_dashboard_card': '_onCardClick',
        },
        _onCardClick: function (ev) {
            var state = ev.currentTarget.dataset.state;
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'project.correspondence',
                view_mode: 'list,form',
                domain: [['state','=',state]],
            });
        },
    });

    registry.add('correspondence.dashboard', Dashboard);
    return Dashboard;
});

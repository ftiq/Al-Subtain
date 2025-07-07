/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { patch } from "@web/core/utils/patch";



patch(KanbanRecord.prototype, {
    name: "lab_sample_kanban_record",
    

    onMounted() {
        this._super();
        this.updateCardAppearance();
    },
    

    updateCardAppearance() {
        if (!this.el) return;
        
        const state = this.props.record.data.state;
        const overallResult = this.props.record.data.overall_result;
        const priority = this.props.record.data.priority;
        
        if (state) {
            this.el.classList.add(`o_kanban_record_state_${state}`);
        }
        
        if (overallResult) {
            this.el.classList.add(`o_kanban_record_result_${overallResult}`);
        }
        
        if (priority === '1') {
            this.el.classList.add('o_kanban_record_high_priority');
        }
    },
    

    async onActionClick(actionName, ev) {
        ev.stopPropagation();
        ev.preventDefault();
        
        const recordId = this.props.record.resId;
        
        try {
            let result;
            
            switch (actionName) {
                case 'start_testing':
                    result = await this.env.services.orm.call(
                        'lab.sample',
                        'action_start_testing',
                        [recordId]
                    );
                    break;
                    
                case 'complete':
                    result = await this.env.services.orm.call(
                        'lab.sample',
                        'action_complete',
                        [recordId]
                    );
                    break;
                    
                case 'view_results':
                    result = await this.env.services.orm.call(
                        'lab.sample',
                        'action_view_result_sets',
                        [recordId]
                    );
                    break;
                    
                default:
                    return;
            }
            
            if (result && result.type) {
                await this.env.services.action.doAction(result);
            } else {
                location.reload();
            }
            
        } catch (error) {
            this.env.services.notification.add(
                error.message || 'حدث خطأ أثناء تنفيذ العملية',
                { type: 'danger' }
            );
        }
    }
});


patch(KanbanRenderer.prototype, {
    name: "lab_sample_kanban_renderer",
    

    getGroupByTooltip(group) {
        const stateDescriptions = {
            'draft': 'العينات في حالة المسودة',
            'received': 'العينات المستلمة وجاهزة للفحص',
            'testing': 'العينات قيد الفحص حالياً',
            'completed': 'العينات المكتملة',
            'rejected': 'العينات المرفوضة'
        };
        
        return stateDescriptions[group.value] || this._super(group);
    }
});


document.addEventListener('DOMContentLoaded', function() {

    document.addEventListener('click', function(event) {
        const actionButton = event.target.closest('[data-action]');
        if (actionButton && actionButton.closest('.o_lab_sample_kanban')) {
            const action = actionButton.dataset.action;
            const kanbanRecord = actionButton.closest('.o_kanban_record');
            
            if (kanbanRecord && kanbanRecord.__owl__) {
                const recordComponent = kanbanRecord.__owl__.component;
                if (recordComponent && recordComponent.onActionClick) {
                    recordComponent.onActionClick(action, event);
                }
            }
        }
    });
}); 
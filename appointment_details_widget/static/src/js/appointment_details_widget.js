/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { formatDateTime } from "@web/core/l10n/dates";

class AppointmentDetailsPopover extends Component {
    static template = "appointment_details_widget.AppointmentDetailsPopover";
    static props = ["*"];

    get appointmentData() {
        const record = this.props.record.data;
        return {
            customer_name: record.partner_id && record.partner_id[1] ? record.partner_id[1] : 'غير محدد',
            customer_phone: record.partner_phone || 'غير محدد',
            customer_email: record.partner_email || 'غير محدد',
            project_name: record.project_name || 'غير محدد',
            appointment_datetime: record.appointment_datetime ? 
                formatDateTime(record.appointment_datetime) : 'غير محدد',
            appointment_status: this.getStatusText(record.appointment_status),
            products: this.getProductsFromInfo(record.products_info),
            total_amount: record.amount_total || 0,
            state: this.getStateText(record.state),
            salesperson: record.user_id && record.user_id[1] ? record.user_id[1] : 'غير محدد',
            currency_symbol: record.currency_symbol || '',
            currency_name: record.currency_name || '',
            fsm_tasks: this.getFsmTasksFromInfo(record.fsm_tasks_info),
            fsm_tasks_count: record.fsm_tasks_count || 0,
            lab_samples: this.getLabSamplesFromInfo(record.lab_samples_info),
            lab_samples_count: record.lab_samples_count || 0
        };
    }

    getStatusText(status) {
        const statusMap = {
            'future': 'قادم',
            'overdue': 'متجاوز',
            'confirmed': 'مؤكد'
        };
        return statusMap[status] || 'غير محدد';
    }

    getStateText(state) {
        const stateMap = {
            'draft': 'مسودة',
            'sent': 'مُرسل',
            'sale': 'مؤكد',
            'done': 'مُنجز',
            'cancel': 'ملغي'
        };
        return stateMap[state] || state;
    }

    getProductsFromInfo(productsInfo) {
        if (!productsInfo || productsInfo.length === 0) {
            return [];
        }
        return productsInfo.map(product => ({
            name: product.name,
            qty: product.qty,
            uom: product.uom,
            price_unit: product.price_unit,
            price_subtotal: product.price_subtotal,
            currency_symbol: product.currency_symbol
        }));
    }
    
    getFsmTasksFromInfo(tasksInfo) {
        if (!tasksInfo || tasksInfo.length === 0) {
            return [];
        }
        return tasksInfo.map(task => ({
            id: task.id,
            name: task.name,
            state: task.state,
            state_text: task.state_text,
            user_id: task.user_id,
            partner_id: task.partner_id,
            project_name: task.project_name,
            planned_date_begin: task.planned_date_begin,
            date_deadline: task.date_deadline,
            fsm_done: task.fsm_done,
            priority: task.priority,
            description: task.description,
            helpdesk_ticket: task.helpdesk_ticket || null
        }));
    }
    
    getLabSamplesFromInfo(samplesInfo) {
        if (!samplesInfo || samplesInfo.length === 0) {
            return [];
        }
        return samplesInfo.map(sample => ({
            id: sample.id,
            name: sample.name,
            state: sample.state,
            state_text: sample.state_text,
            product_name: sample.product_name,
            sample_subtype: sample.sample_subtype,
            collection_date: sample.collection_date,
            received_date: sample.received_date,
            quantity: sample.quantity,
            overall_result: sample.overall_result,
            overall_result_text: sample.overall_result_text,
            task_name: sample.task_name,
            result_sets: sample.result_sets || [],
            result_sets_count: sample.result_sets_count || 0
        }));
    }
}

export class AppointmentDetailsWidget extends Component {
    static template = "appointment_details_widget.AppointmentDetailsWidget";
    static props = ["*"];
    
    setup() {
        this.popover = usePopover(AppointmentDetailsPopover);
    }
    
    get isVisible() {
        const record = this.props.record;
        return record.data.appointment_datetime && record.data.appointment_datetime !== false;
    }

    onButtonClick(ev) {
        const record = this.props.record;
        if (!record.data.appointment_datetime) {
            return;
        }
        
        this.popover.open(ev.currentTarget, {
            record: this.props.record,
        });
    }
}

registry.category("view_widgets").add("appointment_details_widget", {
    component: AppointmentDetailsWidget,
}); 
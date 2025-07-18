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
            salesperson: record.user_id && record.user_id[1] ? record.user_id[1] : 'غير محدد'
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
            price_subtotal: product.price_subtotal
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
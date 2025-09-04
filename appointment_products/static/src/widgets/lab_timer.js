/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState, onWillUpdateProps, onWillStart, onWillDestroy } from "@odoo/owl";

function formatTimeRemaining(seconds) {
    if (seconds <= 0) {
        return "00:00:00";
    }
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export class LabTimer extends Component {
    static template = "appointment_products.LabTimer";

    static props = {
        startTime: { type: [String, Boolean, Object], optional: true },
        endTime:   { type: [String, Boolean, Object], optional: true },
        isActive: { type: Boolean, optional: true },
        label: { type: String, optional: true },
    };
    static defaultProps = { 
        isActive: false,
        label: "المؤقت"
    };

    setup() {
        this.state = useState({
            timeRemaining: 0,
            isExpired: false,
            displayTime: "00:00:00"
        });
        
        onWillStart(() => {
            this._updateTimer();
            if (this.props.isActive && this.props.endTime) {
                this._runTimer();
            }
        });
        
        onWillUpdateProps((nextProps) => {
            const shouldStart = !this.props.isActive && nextProps.isActive && nextProps.endTime;
            if (shouldStart) {
                this._updateTimer(nextProps);
                this._runTimer();
            }
        });
        
        onWillDestroy(() => {
            if (this.timer) {
                clearTimeout(this.timer);
            }
        });
    }

    _updateTimer(props = this.props) {

        const toDate = (val) => {
            if (!val) return null;
            if (val instanceof Date) return val;
            if (typeof val === 'string') return new Date(val);

            if (val.toJSDate) return val.toJSDate();

            try {
                return new Date(val);
            } catch (e) {
                return null;
            }
        };

        const endDateObj = toDate(props.endTime);

        if (!endDateObj) {
            this.state.timeRemaining = 0;
            this.state.isExpired = false;
            this.state.displayTime = "00:00:00";
            return;
        }
        const now = new Date();
        const endTime = endDateObj;
        const diffMs = endTime.getTime() - now.getTime();
        const diffSeconds = Math.floor(diffMs / 1000);

        if (diffSeconds <= 0) {
            this.state.timeRemaining = 0;
            this.state.isExpired = true;
            this.state.displayTime = "انتهى الوقت";
        } else {
            this.state.timeRemaining = diffSeconds;
            this.state.isExpired = false;
            this.state.displayTime = formatTimeRemaining(diffSeconds);
        }
    }

    _runTimer() {
        this.timer = setTimeout(() => {
            this._updateTimer();
            if (this.state.timeRemaining > 0) {
                this._runTimer();
            }
        }, 1000);
    }

    get statusClass() {
        if (this.state.isExpired) {
            return "text-success";
        } else if (this.state.timeRemaining < 3600) { 
            return "text-warning";
        } else if (this.state.timeRemaining < 300) {
            return "text-danger";
        }
        return "text-primary";
    }

    get iconClass() {
        if (this.state.isExpired) {
            return "fa-check-circle";
        } else {
            return "fa-clock-o";
        }
    }
}

class LabTimerField extends Component {
    static template = "appointment_products.LabTimerField";
    static components = { LabTimer };
    static props = standardFieldProps;

    setup() {
        this.orm = useService("orm");
    }

    get startTime() {
        return this.props.record.data.timer_start || this.props.record.data.line_timer_start;
    }

    get endTime() {
        return this.props.record.data.timer_ready || this.props.record.data.line_timer_ready;
    }

    get isActive() {
        return Boolean(this.startTime && this.endTime);
    }

    get label() {
        return this.props.string || "المؤقت";
    }
}

export const labTimerField = {
    component: LabTimerField,
    supportedTypes: ["datetime"],
};

registry.category("fields").add("lab_timer", labTimerField); 
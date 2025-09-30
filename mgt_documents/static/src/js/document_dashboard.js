/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class DocumentDashboard extends Component {
    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            stats: {
                total_documents: 0,
                incoming_total: 0,
                incoming_normal: 0,
                incoming_urgent: 0,
                incoming_very_urgent: 0,
                outgoing_total: 0,
                internal_total: 0,
                circular_total: 0,
                archived_total: 0,
                draft_documents: 0,
                pending_approvals: 0
            },
            recent_documents: [],
            pending_approvals: [],
            company_info: {
                id: 1,
                name: '',
                logo: false,
                street: '',
                phone: ''
            },
            loading: true
        });

        onMounted(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            const result = await rpc('/web/dataset/call_kw', {
                model: 'document.dashboard.data',
                method: 'get_dashboard_data',
                args: [],
                kwargs: {},
            });
            
            this.state.stats = result.stats || {};
            this.state.recent_documents = result.recent_documents || [];
            this.state.pending_approvals = result.pending_approvals || [];
            this.state.company_info = result.company_info || this.state.company_info;
            
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            
            this.state.stats = {
                total_documents: 0,
                incoming_total: 0,
                outgoing_total: 0,
                internal_total: 0,
                circular_total: 0,
                archived_total: 0,
                draft_documents: 0,
                pending_approvals: 0
            };
            this.state.recent_documents = [];
            this.state.pending_approvals = [];
            this.state.company_info = {
                id: 1,
                name: '',
                logo: false,
                street: '',
                phone: ''
            };
            
            this.notification.add(
                'Error loading dashboard data',
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    async refreshData() {
        const refreshBtn = document.querySelector('.refresh_btn');
        if (refreshBtn) {
            refreshBtn.classList.add('spinning');
        }
        
        await this.loadDashboardData();
        
        setTimeout(() => {
            if (refreshBtn) {
                refreshBtn.classList.remove('spinning');
            }
        }, 1000);
        
        this.notification.add("Data refreshed successfully", { type: "success" });
    }

    async openDocuments(documentType, domain = []) {
        const baseAction = {
            name: "Documents",
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current"
        };

        const typeNames = {
            'incoming': 'Incoming Documents',
            'outgoing': 'Outgoing Documents', 
            'internal': 'Internal Documents',
            'circular': 'Circulars',
            'archived': 'Archived',
            'all': 'All Documents'
        };

        const typeDomains = {
            'incoming': [["document_type", "=", "incoming"]],
            'outgoing': [["document_type", "=", "outgoing"]],
            'internal': [["document_type", "=", "internal"]], 
            'circular': [["document_type", "=", "circular"]],
            'archived': [["state", "=", "archived"]],
            'all': []
        };

        baseAction.name = typeNames[documentType] || "Documents";
        baseAction.domain = domain.length > 0 ? domain : typeDomains[documentType] || [];

        this.action.doAction(baseAction);
    }

    async createDocument(documentType = 'incoming') {
        this.action.doAction({
            name: "New Document",
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_document_type: documentType
            }
        });
    }

    async openPendingApprovals() {

        this.action.doAction('mgt_documents.action_my_pending_approvals');
    }

    async openAllPendingApprovals() {

        this.action.doAction({
            name: "All Pending Approvals",
            type: "ir.actions.act_window", 
            res_model: "approval.request",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['request_status', 'in', ['new', 'pending', 'under_approval']]],
            target: "current"
        });
    }

    async openByPriority(priority) {
        const priorityNames = {
            '0': 'Normal Documents',
            '1': 'Urgent Documents', 
            '2': 'Very Urgent Documents'
        };

        this.action.doAction({
            name: priorityNames[priority] || "Documents",
            type: "ir.actions.act_window",
            res_model: "document.document", 
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [['priority', '=', priority]],
            target: "current"
        });
    }

    openDocumentsByImportance(docType, importance) {
        const importanceNames = {
            'normal': 'Normal',
            'urgent': 'Urgent',
            'very_urgent': 'Very Urgent'
        };
        
        const typeNames = {
            'incoming': 'Incoming',
            'outgoing': 'Outgoing', 
            'internal': 'Internal'
        };
        
        this.action.doAction({
            name: `${typeNames[docType] || docType} - ${importanceNames[importance]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "list,kanban,form", 
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [
                ['document_type', '=', docType],
                ['importance', '=', importance]
            ],
            target: "current"
        });
    }

    openDocumentsByState(state) {
        const stateNames = {
            'draft': 'Draft',
            'submitted': 'Submitted',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'archived': 'Archived'
        };
        
        this.action.doAction({
            name: `Documents ${stateNames[state]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current"
        });
    }

    formatNumber(num) {
        return Number(num || 0).toLocaleString('ar-EG');
    }
    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString('ar-EG', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    getStatusClass(state) {
        const statusClasses = {
            'draft': 'status_draft',
            'submitted': 'status_submitted',
            'approved': 'status_approved', 
            'rejected': 'status_rejected'
        };
        return statusClasses[state] || 'status_draft';
    }

    getStatusName(state) {
        const statusNames = {
            'draft': 'Draft',
            'submitted': 'Submitted',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'archived': 'Archived'
        };
        return statusNames[state] || state;
    }

    openDocumentsByType(docType) {
        const typeNames = {
            'incoming': 'Incoming',
            'outgoing': 'Outgoing',
            'internal': 'Internal',
            'report': 'Report',
            'memo': 'Memo',
            'circular': 'Circular',
            'letter': 'Letter',
            'contract': 'Contract',
            'invoice': 'Invoice',
            'other': 'Other'
        };
        
        this.action.doAction({
            name: `Documents ${typeNames[docType] || docType}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["document_type", "=", docType]],
            target: "current",
            context: {
                'default_document_type': docType,
                'group_by': ['state']
            }
        });
    }

    openDocumentsByPriority(docType, priority) {
        const priorityNames = {
            '0': 'Normal',
            '1': 'Urgent',
            '2': 'Very Urgent',
            '3': 'Critical'
        };
        
        const typeNames = {
            'incoming': 'Incoming',
            'outgoing': 'Outgoing',
            'internal': 'Internal',
            'report': 'Report',
            'memo': 'Memo',
            'circular': 'Circular',
            'letter': 'Letter',
            'contract': 'Contract',
            'invoice': 'Invoice',
            'other': 'Other'
        };
        
        this.action.doAction({
            name: `${typeNames[docType]} - ${priorityNames[priority]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [
                ["document_type", "=", docType],
                ["priority", "=", priority]
            ],
            target: "current",
            context: {
                'default_document_type': docType,
                'default_priority': priority
            }
        });
    }

    openDocumentsByState(docType, state) {
        const stateNames = {
            'draft': 'Draft',
            'submitted': 'Submitted',
            'approved': 'Approved',
            'archived': 'Archived'
        };
        
        const typeNames = {
            'incoming': 'Incoming',
            'outgoing': 'Outgoing',
            'internal': 'Internal',
            'report': 'Report',
            'memo': 'Memo',
            'circular': 'Circular',
            'letter': 'Letter',
            'contract': 'Contract',
            'invoice': 'Invoice',
            'other': 'Other'
        };
        
        this.action.doAction({
            name: `${typeNames[docType]} - ${stateNames[state]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [
                ["document_type", "=", docType],
                ["state", "=", state]
            ],
            target: "current",
            context: {
                'default_document_type': docType,
                'default_state': state
            }
        });
    }
}

DocumentDashboard.props = {
    action: { type: Object, optional: true },
    actionId: { type: [String, Number], optional: true },
    updateActionState: { type: Function, optional: true },
    className: { type: String, optional: true },
    "*": true,
};

DocumentDashboard.template = "mgt_documents.DocumentDashboard";

registry.category("actions").add("mgt_documents_dashboard", DocumentDashboard);

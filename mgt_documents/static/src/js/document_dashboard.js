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
            console.error('خطأ في تحميل بيانات الداشبورد:', error);
            
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
                name: 'شبكة السلطين الهندسية',
                logo: false,
                street: '',
                phone: ''
            };
            
            this.notification.add(
                'حدث خطأ أثناء تحميل بيانات الداشبورد',
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
        
        this.notification.add("تم تحديث البيانات بنجاح", { type: "success" });
    }

    async openDocuments(documentType, domain = []) {
        const baseAction = {
            name: "الوثائق",
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current"
        };

        const typeNames = {
            'incoming': 'المخاطبات الواردة',
            'outgoing': 'المخاطبات الصادرة', 
            'internal': 'المخاطبات الداخلية',
            'circular': 'التعاميم',
            'archived': 'الأرشيف',
            'all': 'جميع الوثائق'
        };

        const typeDomains = {
            'incoming': [["document_type", "=", "incoming"]],
            'outgoing': [["document_type", "=", "outgoing"]],
            'internal': [["document_type", "=", "internal"]], 
            'circular': [["document_type", "=", "circular"]],
            'archived': [["processing_state", "=", "archived"]],
            'all': []
        };

        baseAction.name = typeNames[documentType] || "الوثائق";
        baseAction.domain = domain.length > 0 ? domain : typeDomains[documentType] || [];

        this.action.doAction(baseAction);
    }

    async createDocument(documentType = 'incoming') {
        this.action.doAction({
            name: "وثيقة جديدة",
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
            name: "جميع طلبات الموافقة المعلقة",
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
            '0': 'الوثائق العادية',
            '1': 'الوثائق العاجلة', 
            '2': 'الوثائق العاجلة جداً'
        };

        this.action.doAction({
            name: priorityNames[priority] || "الوثائق",
            type: "ir.actions.act_window",
            res_model: "document.document", 
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [['priority', '=', priority]],
            target: "current"
        });
    }

    // removed importance-based filtering; use priority instead

    openAllDocumentsByState(state) {
        const stateNames = {
            'draft': 'مسودات',
            'submitted': 'مقدمة',
            'approved': 'معتمدة',
            'rejected': 'مرفوضة',
            'archived': 'مؤرشفة'
        };
        
        this.action.doAction({
            name: `الوثائق ${stateNames[state]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "list,kanban,form",
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            domain: [["processing_state", "=", state]],
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
            'draft': 'مسودة',
            'submitted': 'مُقدمة',
            'approved': 'معتمدة',
            'rejected': 'مرفوضة',
            'archived': 'مؤرشفة'
        };
        return statusNames[state] || state;
    }

    openDocumentsByType(docType) {
        const typeNames = {
            'incoming': 'وارد',
            'outgoing': 'صادر',
            'internal': 'داخلي',
            'report': 'تقرير',
            'memo': 'مذكرة',
            'circular': 'تعميم',
            'letter': 'رسالة',
            'contract': 'عقد',
            'invoice': 'فاتورة',
            'other': 'أخرى'
        };
        
        this.action.doAction({
            name: `وثائق ${typeNames[docType] || docType}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["document_type", "=", docType]],
            target: "current",
            context: {
                'default_document_type': docType,
                'group_by': ['processing_state']
            }
        });
    }

    openDocumentsByPriority(docType, priority) {
        const priorityNames = {
            '0': 'عادي',
            '1': 'مهم',
            '2': 'عاجل',
            '3': 'عاجل جداً'
        };
        
        const typeNames = {
            'incoming': 'وارد',
            'outgoing': 'صادر',
            'internal': 'داخلي',
            'report': 'تقرير',
            'memo': 'مذكرة',
            'circular': 'تعميم',
            'letter': 'رسالة',
            'contract': 'عقد',
            'invoice': 'فاتورة',
            'other': 'أخرى'
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
            'draft': 'مسودة',
            'submitted': 'مقدمة',
            'approved': 'معتمدة',
            'archived': 'مؤرشفة'
        };
        
        const typeNames = {
            'incoming': 'وارد',
            'outgoing': 'صادر',
            'internal': 'داخلي',
            'report': 'تقرير',
            'memo': 'مذكرة',
            'circular': 'تعميم',
            'letter': 'رسالة',
            'contract': 'عقد',
            'invoice': 'فاتورة',
            'other': 'أخرى'
        };
        
        this.action.doAction({
            name: `${typeNames[docType]} - ${stateNames[state]}`,
            type: "ir.actions.act_window",
            res_model: "document.document",
            view_mode: "kanban,list,form",
            view_type: "kanban",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            domain: [["document_type", "=", docType], ["processing_state", "=", state]],
            target: "current",
            context: {
                'default_document_type': docType,
                'default_processing_state': state
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

/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";


export class DocumentDashboard extends Component {
    static template = "mgt_documents.DocumentDashboard";
    
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            stats: {},
            recentDocuments: [],
            pendingApprovals: [],
            loading: true,
            chartData: {},
        });
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }


    
    async loadDashboardData() {
        try {
            this.state.loading = true;
            

            const stats = await this.orm.call(
                'document.document',
                'get_dashboard_statistics',
                []
            );
            

            const recentDocuments = await this.orm.searchRead(
                'document.document',
                [],
                ['name', 'reference_number', 'document_type_id', 'state', 'date'],
                {
                    order: 'create_date desc',
                    limit: 10
                }
            );
            

            const pendingApprovals = await this.orm.searchRead(
                'approval.request',
                [['approval_status', '=', 'pending'], ['approver_id', '=', this.env.uid]],
                ['document_id', 'request_date', 'priority'],
                {
                    order: 'request_date desc',
                    limit: 5
                }
            );
            

            const chartData = await this.orm.call(
                'document.document',
                'get_chart_data',
                []
            );
            
            this.state.stats = stats;
            this.state.recentDocuments = recentDocuments;
            this.state.pendingApprovals = pendingApprovals;
            this.state.chartData = chartData;
            
        } catch (error) {
            this.notification.add(
                this.env._t("حدث خطأ أثناء تحميل بيانات لوحة التحكم"),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }


    async openDocumentsList(filterType) {
        let domain = [];
        let context = {};
        
        switch (filterType) {
            case 'all':
                domain = [];
                break;
            case 'draft':
                domain = [['state', '=', 'draft']];
                break;
            case 'review':
                domain = [['state', '=', 'review']];
                break;
            case 'approved':
                domain = [['state', '=', 'approved']];
                break;
            case 'archived':
                domain = [['state', '=', 'archived']];
                break;
            case 'my_documents':
                domain = [['create_uid', '=', this.env.uid]];
                break;
            case 'incoming':
                domain = [['document_type_id.name', 'ilike', 'وارد']];
                break;
            case 'outgoing':
                domain = [['document_type_id.name', 'ilike', 'صادر']];
                break;
        }
        
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t('الوثائق'),
            res_model: 'document.document',
            view_mode: 'tree,kanban,form',
            views: [
                [false, 'tree'],
                [false, 'kanban'],
                [false, 'form']
            ],
            domain: domain,
            context: context,
            target: 'current',
        };
        
        await this.actionService.doAction(action);
    }


    async openApprovalRequests() {
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t('طلبات الموافقة'),
            res_model: 'approval.request',
            view_mode: 'tree,form',
            domain: [['approver_id', '=', this.env.uid], ['approval_status', '=', 'pending']],
            target: 'current',
        };
        
        await this.actionService.doAction(action);
    }


    async openDocument(documentId) {
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t('تفاصيل الوثيقة'),
            res_model: 'document.document',
            res_id: documentId,
            view_mode: 'form',
            target: 'current',
        };
        
        await this.actionService.doAction(action);
    }


    async createNewDocument() {
        const action = {
            type: 'ir.actions.act_window',
            name: this.env._t('وثيقة جديدة'),
            res_model: 'document.document',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
            context: {
                'default_state': 'draft',
            },
        };
        
        await this.actionService.doAction(action);
    }


    async refreshData() {
        await this.loadDashboardData();
        this.notification.add(
            this.env._t("تم تحديث البيانات بنجاح"),
            { type: "success" }
        );
    }


    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('ar-SA');
    }


    formatNumber(number) {
        return new Intl.NumberFormat('ar-SA').format(number);
    }


    getStateColor(state) {
        const colors = {
            'draft': 'secondary',
            'review': 'primary',
            'approved': 'success',
            'rejected': 'danger',
            'archived': 'info',
        };
        return colors[state] || 'secondary';
    }


    getStateName(state) {
        const states = {
            'draft': 'مسودة',
            'review': 'قيد المراجعة',
            'approved': 'معتمدة',
            'rejected': 'مرفوضة',
            'archived': 'مؤرشفة',
        };
        return states[state] || state;
    }


    
    getDocumentTypeIcon(documentType) {
        if (!documentType) return 'fa-file-o';
        
        if (documentType.includes('وارد')) return 'fa-inbox';
        if (documentType.includes('صادر')) return 'fa-paper-plane';
        if (documentType.includes('داخلي')) return 'fa-building';
        if (documentType.includes('تعميم')) return 'fa-bullhorn';
        if (documentType.includes('كتاب')) return 'fa-book';
        
        return 'fa-file-text-o';
    }
}


export class DocumentChart extends Component {
    static template = "mgt_documents.DocumentChart";
    static props = {
        chartData: Object,
        chartType: { type: String, optional: true },
        title: { type: String, optional: true },
    };

    setup() {
        this.chartRef = useRef("chart");
        
        onMounted(() => {
            this.renderChart();
        });
        
        onPatched(() => {
            this.renderChart();
        });
    }

    
    renderChart() {
        if (!this.chartRef.el || !this.props.chartData) return;
        

        const ctx = this.chartRef.el.getContext('2d');
        
        new Chart(ctx, {
            type: this.props.chartType || 'doughnut',
            data: this.props.chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        rtl: true,
                    },
                    title: {
                        display: !!this.props.title,
                        text: this.props.title,
                    }
                }
            }
        });
    }
}


registry.category("actions").add("mgt_documents.dashboard", DocumentDashboard);
registry.category("components").add("DocumentDashboard", DocumentDashboard);
registry.category("components").add("DocumentChart", DocumentChart); 
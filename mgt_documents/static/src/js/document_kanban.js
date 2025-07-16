/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";


patch(KanbanController.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    },


    async _onRecordDrop(record, group, targetGroup) {
        if (this.props.resModel === 'document.document') {
            const recordId = record.resId;
            const newState = targetGroup.value;
            
            try {
                await this.model.root.records.find(r => r.resId === recordId).update({
                    state: newState
                });
                
                this.notification.add(
                    this.env._t("تم تحديث حالة الوثيقة بنجاح"),
                    { type: "success" }
                );
            } catch (error) {
                this.notification.add(
                    this.env._t("حدث خطأ أثناء تحديث حالة الوثيقة"),
                    { type: "danger" }
                );
            }
        }
        return super._onRecordDrop(...arguments);
    },


    _getActionMenuItems() {
        const items = super._getActionMenuItems(...arguments);
        
        if (this.props.resModel === 'document.document') {
            items.push({
                key: 'archive_documents',
                description: this.env._t("أرشفة الوثائق المحددة"),
                callback: () => this._archiveSelectedDocuments(),
            });
            
            items.push({
                key: 'export_documents',
                description: this.env._t("تصدير الوثائق المحددة"),
                callback: () => this._exportSelectedDocuments(),
            });
        }
        
        return items;
    },


    async _archiveSelectedDocuments() {
        const selectedRecords = this.model.root.selection;
        if (selectedRecords.length === 0) {
            this.notification.add(
                this.env._t("يرجى تحديد وثائق للأرشفة"),
                { type: "warning" }
            );
            return;
        }

        this.dialog.add(ConfirmationDialog, {
            title: this.env._t("تأكيد الأرشفة"),
            body: this.env._t(`هل أنت متأكد من أرشفة ${selectedRecords.length} وثيقة؟`),
            confirm: async () => {
                try {
                    await this.orm.call(
                        'document.document',
                        'action_archive_documents',
                        [selectedRecords.map(r => r.resId)]
                    );
                    
                    this.notification.add(
                        this.env._t("تم أرشفة الوثائق بنجاح"),
                        { type: "success" }
                    );
                    
                    await this.model.root.load();
                } catch (error) {
                    this.notification.add(
                        this.env._t("حدث خطأ أثناء أرشفة الوثائق"),
                        { type: "danger" }
                    );
                }
            },
            cancel: () => {},
        });
    },


    async _exportSelectedDocuments() {
        const selectedRecords = this.model.root.selection;
        if (selectedRecords.length === 0) {
            this.notification.add(
                this.env._t("يرجى تحديد وثائق للتصدير"),
                { type: "warning" }
            );
            return;
        }

        try {
            const action = await this.orm.call(
                'document.document',
                'action_export_documents',
                [selectedRecords.map(r => r.resId)]
            );
            
            this.actionService.doAction(action);
        } catch (error) {
            this.notification.add(
                this.env._t("حدث خطأ أثناء تصدير الوثائق"),
                { type: "danger" }
            );
        }
    }
});


patch(KanbanRecord.prototype, {

    _getRecordClasses() {
        let classes = super._getRecordClasses(...arguments);
        
        if (this.props.record.resModel === 'document.document') {
            const state = this.props.record.data.state;
            classes += ` o_document_state_${state}`;
            

            const dueDate = this.props.record.data.due_date;
            if (dueDate && new Date(dueDate) < new Date()) {
                classes += ' o_document_overdue';
            }
            

            const priority = this.props.record.data.priority;
            if (priority === 'high') {
                classes += ' o_document_high_priority';
            }
        }
        
        return classes;
    },


    _getTooltipInfo() {
        const tooltipInfo = super._getTooltipInfo(...arguments);
        
        if (this.props.record.resModel === 'document.document') {
            const record = this.props.record.data;
            return {
                ...tooltipInfo,
                template: 'mgt_documents.DocumentTooltip',
                info: {
                    name: record.name,
                    reference_number: record.reference_number,
                    document_type: record.document_type_id && record.document_type_id[1],
                    state: record.state,
                    sender: record.sender_id && record.sender_id[1],
                    recipient: record.recipient_id && record.recipient_id[1],
                    date: record.date,
                    summary: record.summary,
                }
            };
        }
        
        return tooltipInfo;
    }
});


export class DocumentKanbanController extends KanbanController {
    static template = "mgt_documents.DocumentKanbanView";
    

    get quickFilters() {
        return [
            {
                key: 'my_documents',
                label: this.env._t("وثائقي"),
                domain: [['create_uid', '=', this.env.uid]],
            },
            {
                key: 'pending_approval',
                label: this.env._t("في انتظار الموافقة"),
                domain: [['state', '=', 'review']],
            },
            {
                key: 'urgent_documents',
                label: this.env._t("وثائق عاجلة"),
                domain: [['priority', '=', 'high']],
            },
            {
                key: 'recent_documents',
                label: this.env._t("وثائق حديثة"),
                domain: [['create_date', '>=', moment().subtract(7, 'days').format('YYYY-MM-DD')]],
            }
        ];
    }


    async applyQuickFilter(filterKey) {
        const filter = this.quickFilters.find(f => f.key === filterKey);
        if (filter) {
            await this.env.searchModel.setDomainParts({
                quick_filter: filter.domain
            });
        }
    }


    async getDocumentStats() {
        const stats = await this.orm.call(
            'document.document',
            'get_document_statistics',
            []
        );
        
        return stats;
    }
}


import { registry } from "@web/core/registry";

registry.category("views").add("document_kanban", {
    ...registry.category("views").get("kanban"),
    Controller: DocumentKanbanController,
}); 
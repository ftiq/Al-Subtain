/** @odoo-module **/

import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { patch } from "@web/core/utils/patch";



patch(KanbanRecord.prototype, {

    setup() {
        super.setup(...arguments);
        this._setupLabTestFlowEnhancements();
    },

    _setupLabTestFlowEnhancements() {
        if (this.props.record.resModel === 'lab.test.flow.template') {
            this._addCardHoverEffects();
            this._addProgressAnimations();
            this._enhanceButtonInteractions();
        }
    },

    _addCardHoverEffects() {
        const card = this.el?.querySelector('.o_kanban_record');
        if (card) {

            card.setAttribute('data-lab-template', 'true');
            
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-2px)';
                card.style.boxShadow = '0 4px 15px rgba(74, 144, 226, 0.15)';
                card.style.transition = 'all 0.2s ease';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0)';
                card.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
            });
        }
    },

    _addProgressAnimations() {
        const progressBars = this.el?.querySelectorAll('.progress-bar');
        if (progressBars) {
            progressBars.forEach(bar => {
                const originalWidth = bar.style.width || '100%';
                bar.style.width = '0%';
                bar.style.transition = 'width 1.2s ease-out';
                
                setTimeout(() => {
                    bar.style.width = originalWidth;
                }, 200);
            });
        }
    },

    _enhanceButtonInteractions() {
        const buttons = this.el?.querySelectorAll('.btn-outline-primary');
        if (buttons) {
            buttons.forEach(button => {
                
                button.addEventListener('mouseenter', () => {
                    button.style.backgroundColor = '#4a90e2';
                    button.style.color = 'white';
                    button.style.transition = 'all 0.2s ease';
                });

                button.addEventListener('mouseleave', () => {
                    button.style.backgroundColor = '';
                    button.style.color = '';
                });
            });
        }
    }
});


if (typeof document !== 'undefined') {
    const style = document.createElement('style');
    style.textContent = `

        .o_lab_test_flow_template_kanban .o_kanban_record {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .o_lab_test_flow_template_kanban .badge {
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .o_lab_test_flow_template_kanban .badge:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
        }
        
        .o_lab_test_flow_template_kanban .btn {
            transition: all 0.2s ease;
        }
    `;
    document.head.appendChild(style);
}

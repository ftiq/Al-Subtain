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
                card.style.transform = 'translateY(-3px) scale(1.02)';
                card.style.boxShadow = '0 8px 25px rgba(74, 144, 226, 0.2)';
                card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                
                const progressBar = card.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.background = 'linear-gradient(90deg, #20c997, #17a2b8)';
                    progressBar.style.boxShadow = '0 0 10px rgba(32, 201, 151, 0.5)';
                }
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
                card.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
                
                const progressBar = card.querySelector('.progress-bar');
                if (progressBar) {
                    progressBar.style.background = 'linear-gradient(90deg, #28a745, #20c997)';
                    progressBar.style.boxShadow = '0 2px 4px rgba(40, 167, 69, 0.3)';
                }
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
                button.addEventListener('click', (e) => {
                    const rect = button.getBoundingClientRect();
                    const ripple = document.createElement('span');
                    const size = Math.max(rect.width, rect.height);
                    const x = e.clientX - rect.left - size / 2;
                    const y = e.clientY - rect.top - size / 2;
                    
                    ripple.style.cssText = `
                        position: absolute;
                        width: ${size}px;
                        height: ${size}px;
                        background: rgba(255, 255, 255, 0.5);
                        border-radius: 50%;
                        transform: scale(0);
                        animation: ripple 0.6s linear;
                        left: ${x}px;
                        top: ${y}px;
                        pointer-events: none;
                    `;
                    
                    button.style.position = 'relative';
                    button.style.overflow = 'hidden';
                    button.appendChild(ripple);
                    
                    setTimeout(() => {
                        ripple.remove();
                    }, 600);
                });
                button.addEventListener('mouseenter', () => {
                    button.style.transform = 'translateY(-1px) scale(1.05)';
                    button.style.boxShadow = '0 6px 12px rgba(74, 144, 226, 0.4)';
                });

                button.addEventListener('mouseleave', () => {
                    button.style.transform = 'translateY(0) scale(1)';
                    button.style.boxShadow = '0 2px 4px rgba(74, 144, 226, 0.1)';
                });
            });
        }
    }
});


if (typeof document !== 'undefined') {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        /* Enhanced loading animations */
        .o_lab_test_flow_template_kanban .o_kanban_record {
            animation: labCardFadeIn 0.6s ease-out;
        }
        
        @keyframes labCardFadeIn {
            from {
                opacity: 0;
                transform: translateY(20px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }
        
        /* Professional badge animations */
        .o_lab_test_flow_template_kanban .badge {
            animation: badgePulse 2s ease-in-out infinite alternate;
        }
        
        @keyframes badgePulse {
            0% { 
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2); 
            }
            100% { 
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3); 
            }
        }
        
        /* Status indicator enhancements */
        .o_lab_test_flow_template_kanban .badge.bg-success::before,
        .o_lab_test_flow_template_kanban .badge.bg-info::before {
            content: '';
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: inherit;
            border-radius: inherit;
            opacity: 0.5;
            animation: glowPulse 2s ease-in-out infinite;
        }
        
        @keyframes glowPulse {
            0%, 100% { 
                transform: scale(1);
                opacity: 0.5;
            }
            50% { 
                transform: scale(1.1);
                opacity: 0.8;
            }
        }
    `;
    document.head.appendChild(style);
}

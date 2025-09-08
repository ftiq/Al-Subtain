/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

export class LabSignatureWidget extends Component {
    setup() {
        onMounted(() => {
            this.setupSignatureField();
        });
        
        onWillUnmount(() => {
            this.cleanup();
        });
    }
    
    setupSignatureField() {
        const signatureField = document.querySelector('.o_signature_field');
        if (signatureField) {

            if (!signatureField.value) {
                this.addPlaceholderMessage(signatureField);
            }
            

            this.addSaveValidation();
        }
    }
    
    addPlaceholderMessage(field) {
        const placeholder = document.createElement('div');
        placeholder.className = 'signature-placeholder';
        placeholder.innerHTML = `
            <div style="text-align: center; padding: 40px; color: #6c757d;">
                <i class="fa fa-edit" style="font-size: 2em; margin-bottom: 10px;"></i>
                <p>اضغط هنا لإضافة توقيعك الإلكتروني</p>
                <small>التوقيع مطلوب قبل اعتماد النتائج</small>
            </div>
        `;
        
        if (field.parentElement) {
            field.parentElement.appendChild(placeholder);
        }
        

        field.addEventListener('focus', () => {
            placeholder.style.display = 'none';
        });
    }
    
    addSaveValidation() {

        const approveButton = document.querySelector('button[name="action_approve_results"]');
        if (approveButton) {
            approveButton.addEventListener('click', (event) => {
                const signatureField = document.querySelector('.o_signature_field');
                if (signatureField && !signatureField.value) {
                    event.preventDefault();
                    this.showSignatureWarning();
                }
            });
        }
    }
    
    showSignatureWarning() {

        const warningModal = document.createElement('div');
        warningModal.className = 'alert alert-warning signature-warning';
        warningModal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 9999;
            width: 400px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            padding: 20px;
        `;
        
        warningModal.innerHTML = `
            <div>
                <i class="fa fa-exclamation-triangle" style="font-size: 2em; color: #ffc107; margin-bottom: 10px;"></i>
                <h5>التوقيع مطلوب</h5>
                <p>يجب عليك إضافة توقيعك الإلكتروني من تبويب "التوقيع الإلكتروني" قبل اعتماد النتائج.</p>
                <button class="btn btn-primary" onclick="this.parentElement.parentElement.remove()">
                    فهمت
                </button>
            </div>
        `;
        
        document.body.appendChild(warningModal);
        

        setTimeout(() => {
            if (warningModal.parentElement) {
                warningModal.remove();
            }
        }, 5000);
    }
    
    cleanup() {

        const placeholders = document.querySelectorAll('.signature-placeholder');
        placeholders.forEach(ph => ph.remove());
        
        const warnings = document.querySelectorAll('.signature-warning');
        warnings.forEach(w => w.remove());
    }
}


registry.category("services").add("lab_signature", {
    start() {

        document.addEventListener('DOMContentLoaded', () => {
            new LabSignatureWidget();
        });
    }
});


document.addEventListener('DOMContentLoaded', function() {

    const signatureFields = document.querySelectorAll('field[name="signature"]');
    signatureFields.forEach(field => {
        if (field.closest('.o_form_view')) {
            field.setAttribute('required', '1');
        }
    });
    

    const approveButtons = document.querySelectorAll('button[name="action_approve_results"]');
    approveButtons.forEach(button => {
        button.setAttribute('title', 'يتطلب توقيع إلكتروني صالح');
    });
});

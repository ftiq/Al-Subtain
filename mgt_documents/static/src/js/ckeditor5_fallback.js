/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class CKEditor5FallbackWidget extends Component {
    static template = "mgt_documents.CKEditor5FallbackWidget";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        height: { type: String, optional: true },
    };

    setup() {
        this.editorRef = useRef("editor");
        this.notification = useService("notification");
        this.state = useState({
            isLoading: false,
            isReady: true
        });
        
        onMounted(() => {
            this.initFallbackEditor();
        });
    }

    initFallbackEditor() {
        const editorElement = this.editorRef.el;
        
        if (editorElement) {
            this.addCustomToolbar();
            
            editorElement.style.minHeight = this.editorHeight;
            editorElement.style.border = '1px solid #ddd';
            editorElement.style.borderRadius = '4px';
            editorElement.style.padding = '10px';
            editorElement.style.fontFamily = 'Arial, sans-serif';
            editorElement.style.fontSize = '14px';
            editorElement.style.lineHeight = '1.6';
            
            if (this.props.record && this.props.record.data[this.props.name]) {
                editorElement.innerHTML = this.props.record.data[this.props.name];
            }
            
            editorElement.addEventListener('input', () => {
                if (!this.props.readonly) {
                    const data = editorElement.innerHTML;
                    this.props.record.update({ [this.props.name]: data });
                }
            });
            
            if (this.props.readonly) {
                editorElement.contentEditable = false;
                editorElement.style.backgroundColor = '#f8f9fa';
            } else {
                editorElement.contentEditable = true;
            }
        }
    }

    addCustomToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'fallback-toolbar';
        toolbar.innerHTML = `
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('bold', false, null);" title="غامق">
                    <i class="fa fa-bold"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('italic', false, null);" title="مائل">
                    <i class="fa fa-italic"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('underline', false, null);" title="تحته خط">
                    <i class="fa fa-underline"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('justifyLeft', false, null);" title="محاذاة يسار">
                    <i class="fa fa-align-left"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('justifyCenter', false, null);" title="محاذاة وسط">
                    <i class="fa fa-align-center"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('justifyRight', false, null);" title="محاذاة يمين">
                    <i class="fa fa-align-right"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('insertUnorderedList', false, null);" title="قائمة نقطية">
                    <i class="fa fa-list-ul"></i>
                </button>
                <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.execCommand('insertOrderedList', false, null);" title="قائمة مرقمة">
                    <i class="fa fa-list-ol"></i>
                </button>
            </div>
        `;
        
        this.editorRef.el.parentNode.insertBefore(toolbar, this.editorRef.el);
    }

    get value() {
        return this.props.record.data[this.props.name] || '';
    }

    get editorHeight() {
        return this.props.height || '400px';
    }
}

registry.category("fields").add("ckeditor5_fallback_widget", CKEditor5FallbackWidget);

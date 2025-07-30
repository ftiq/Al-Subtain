/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class RichTextWidget extends Component {
    static template = "mgt_documents.RichTextWidget";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        height: { type: String, optional: true },
        mode: { type: String, optional: true }, 
    };
    
    static supportedTypes = ["html"];

    setup() {
        this.editorRef = useRef("editor");
        this.toolbarRef = useRef("toolbar");
        this.notification = useService("notification");
        this.state = useState({
            isLoading: true,
            isReady: false,
            editorType: 'none', 
            showToolbar: true
        });
        
        this.editor = null;
        this.mode = this.props.mode || 'advanced'; 
        
        onMounted(() => {
            this.initEditor();
        });

        onWillUnmount(() => {
            this.destroyEditor();
        });
    }

    async initEditor() {
        if (this.mode === 'simple') {
            this.initSimpleEditor();
            return;
        }

        try {
            
            await this.initCKEditor5();
        } catch (error) {
            console.warn('فشل تحميل CKEditor 5، التبديل إلى المحرر البسيط:', error);
            this.initSimpleEditor();
        }
    }

    async initCKEditor5() {
        
        const { ClassicEditor } = await import('https://cdn.ckeditor.com/ckeditor5/40.2.0/classic/ckeditor.js');
        
        const editorConfig = {
            toolbar: {
                items: [
                    'heading', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', '|',
                    'bold', 'italic', 'underline', 'strikethrough', '|',
                    'alignment', '|',
                    'numberedList', 'bulletedList', '|',
                    'indent', 'outdent', '|',
                    'link', 'insertTable', '|',
                    'blockQuote', '|',
                    'undo', 'redo'
                ],
                shouldNotGroupWhenFull: true
            },
            language: 'ar',
            fontSize: {
                options: [9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30],
                supportAllValues: true
            },
            fontFamily: {
                options: [
                    'default',
                    'Arial, Helvetica, sans-serif',
                    'Times New Roman, Times, serif',
                    'Courier New, Courier, monospace',
                    'Amiri, serif',
                    'Cairo, sans-serif',
                    'Noto Sans Arabic, sans-serif'
                ],
                supportAllValues: true
            },
            placeholder: this.props.placeholder || 'ابدأ بكتابة محتوى الوثيقة...',
            alignment: {
                options: ['left', 'right', 'center', 'justify']
            }
        };

        this.editor = await ClassicEditor.create(this.editorRef.el, editorConfig);
        
        if (this.value) {
            this.editor.setData(this.value);
        }
        this.editor.model.document.on('change:data', () => {
            if (!this.props.readonly) {
                const data = this.editor.getData();
                this.updateValue(data);
            }
        });

        if (this.props.readonly) {
            this.editor.enableReadOnlyMode('readonly-mode');
        }

        this.state.editorType = 'ckeditor5';
        this.state.showToolbar = false;
        this.state.isLoading = false;
        this.state.isReady = true;
    }

    initSimpleEditor() {
        const editorElement = this.editorRef.el;
        
        if (!editorElement) return;

        editorElement.style.minHeight = this.editorHeight;
        editorElement.style.border = '1px solid #ddd';
        editorElement.style.borderRadius = '0 0 4px 4px';
        editorElement.style.padding = '15px';
        editorElement.style.fontFamily = 'Arial, sans-serif';
        editorElement.style.fontSize = '14px';
        editorElement.style.lineHeight = '1.6';
        editorElement.style.outline = 'none';
        editorElement.style.backgroundColor = this.props.readonly ? '#f8f9fa' : 'white';
        
        if (this.value) {
            editorElement.innerHTML = this.value;
        }
        
        editorElement.addEventListener('input', () => {
            if (!this.props.readonly) {
                const data = editorElement.innerHTML;
                this.updateValue(data);
            }
        });

        editorElement.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = e.clipboardData.getData('text/plain');
            document.execCommand('insertText', false, text);
        });
        
        editorElement.contentEditable = !this.props.readonly;
        
        this.setupSimpleToolbar();

        this.state.editorType = 'simple';
        this.state.showToolbar = true;
        this.state.isLoading = false;
        this.state.isReady = true;
    }

    setupSimpleToolbar() {
        const toolbar = this.toolbarRef.el;
        if (!toolbar) return;

        toolbar.addEventListener('click', (e) => {
            e.preventDefault();
            const button = e.target.closest('button');
            if (!button) return;

            const command = button.dataset.command;
            const value = button.dataset.value || null;

            if (command) {
                document.execCommand(command, false, value);
                this.editorRef.el.focus();
            }
        });
    }

    destroyEditor() {
        if (this.editor && this.state.editorType === 'ckeditor5') {
            this.editor.destroy()
                .then(() => {
                    this.editor = null;
                })
                .catch(error => {
                    console.error('خطأ في إغلاق المحرر:', error);
                });
        }
    }

    execCommand(command, value = null) {
        document.execCommand(command, false, value);
        this.editorRef.el.focus();
    }

    insertList(type) {
        const command = type === 'ul' ? 'insertUnorderedList' : 'insertOrderedList';
        this.execCommand(command);
    }

    changeTextAlign(align) {
        const commands = {
            'left': 'justifyLeft',
            'center': 'justifyCenter',
            'right': 'justifyRight',
            'justify': 'justifyFull'
        };
        this.execCommand(commands[align]);
    }

    changeFontSize(size) {
        this.execCommand('fontSize', size);
    }

    get value() {
        return this.props.value || '';
    }

    updateValue(newValue) {
        this.props.update(newValue);
    }

    get editorHeight() {
        return this.props.height || '400px';
    }

    get isAdvancedMode() {
        return this.state.editorType === 'ckeditor5';
    }

    get isSimpleMode() {
        return this.state.editorType === 'simple';
    }
}


registry.category("fields").add("rich_text_widget", RichTextWidget);

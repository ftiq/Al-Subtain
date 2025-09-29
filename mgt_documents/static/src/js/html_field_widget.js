/** @odoo-module **/

import { registry } from "@web/core/registry";
import { HtmlField } from "@web_editor/fields/html_field";

export class DocumentHtmlField extends HtmlField {
    
    setup() {
        super.setup();
        
        this.wysiwygOptions = {
            ...this.wysiwygOptions,
            direction: 'rtl',
            lang: 'ar',
            placeholder: this.props.placeholder || 'ابدأ بكتابة محتوى الوثيقة...',
            toolbar: [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'strikethrough', 'clear']],
                ['fontname', ['fontname']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['view', ['fullscreen', 'codeview']],
                ['help', ['help']]
            ],
            fontNames: [
                'Arial', 'Arial Black', 'Comic Sans MS', 'Courier New',
                'Helvetica Neue', 'Helvetica', 'Impact', 'Lucida Grande',
                'Tahoma', 'Times New Roman', 'Verdana',
                'Amiri', 'Cairo', 'Noto Sans Arabic', 'Droid Arabic Naskh'
            ],
            fontSizes: ['8', '9', '10', '11', '12', '14', '16', '18', '20', '24', '30', '36', '48'],
            styleTags: [
                'p', 'blockquote', 'pre', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
            ],
            defaultTextColor: '#212529',
            lineHeights: ['0.2', '0.3', '0.4', '0.5', '0.6', '0.8', '1.0', '1.2', '1.4', '1.5', '2.0', '3.0'],
            insertTableMaxSize: {
                col: 10,
                row: 10
            },
            callbacks: {
                onInit: this.onEditorInit.bind(this),
                onChange: this.onEditorChange.bind(this),
                onFocus: this.onEditorFocus.bind(this),
                onBlur: this.onEditorBlur.bind(this)
            }
        };
    }

    onEditorInit() {
        const editorEl = this.wysiwyg?.el;
        if (editorEl) {
            editorEl.style.direction = 'rtl';
            editorEl.style.textAlign = 'right';
            
            if (this.props.height) {
                editorEl.style.minHeight = this.props.height;
            }
        }
    }

    
    onEditorChange() {
        if (this.wysiwyg && !this.props.readonly) {
            const content = this.wysiwyg.getValue();
            this.props.update(content);
        }
    }

    onEditorFocus() {
    }

    onEditorBlur() {

    }

    get isVisible() {
        return !this.props.invisible;
    }

    get isReadonly() {
        return this.props.readonly;
    }
}


registry.category("fields").add("document_html_field", DocumentHtmlField);

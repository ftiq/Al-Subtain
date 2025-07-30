/** @odoo-module **/

import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";

export class CKEditor5Widget extends Component {
    static template = "mgt_documents.CKEditor5Widget";
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
            isLoading: true,
            isReady: false
        });
        
        this.editor = null;
        
        onMounted(() => {
            this.initCKEditor();
        });

        onWillUnmount(() => {
            this.destroyEditor();
        });
    }

    async initCKEditor() {
        try {
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
                        'todoList', '|',
                        'link', 'insertImage', 'insertTable', '|',
                        'blockQuote', 'codeBlock', '|',
                        'horizontalLine', 'specialCharacters', '|',
                        'textPartLanguage', '|',
                        'sourceEditing', '|',
                        'undo', 'redo'
                    ],
                    shouldNotGroupWhenFull: true
                },
                language: 'ar',
                fontSize: {
                    options: [
                        9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36
                    ],
                    supportAllValues: true
                },
                fontFamily: {
                    options: [
                        'default',
                        'Arial, Helvetica, sans-serif',
                        'Courier New, Courier, monospace',
                        'Georgia, serif',
                        'Lucida Sans Unicode, Lucida Grande, sans-serif',
                        'Tahoma, Geneva, sans-serif',
                        'Times New Roman, Times, serif',
                        'Trebuchet MS, Helvetica, sans-serif',
                        'Verdana, Geneva, sans-serif',
                        'Amiri, serif',
                        'Cairo, sans-serif',
                        'Noto Sans Arabic, sans-serif',
                        'Scheherazade New, serif'
                    ],
                    supportAllValues: true
                },
                fontColor: {
                    colors: [
                        {
                            color: 'hsl(0, 0%, 0%)',
                            label: 'Black'
                        },
                        {
                            color: 'hsl(0, 0%, 30%)',
                            label: 'Dim grey'
                        },
                        {
                            color: 'hsl(0, 0%, 60%)',
                            label: 'Grey'
                        },
                        {
                            color: 'hsl(0, 0%, 90%)',
                            label: 'Light grey'
                        },
                        {
                            color: 'hsl(0, 0%, 100%)',
                            label: 'White',
                            hasBorder: true
                        },
                        {
                            color: 'hsl(0, 75%, 60%)',
                            label: 'Red'
                        },
                        {
                            color: 'hsl(30, 75%, 60%)',
                            label: 'Orange'
                        },
                        {
                            color: 'hsl(60, 75%, 60%)',
                            label: 'Yellow'
                        },
                        {
                            color: 'hsl(90, 75%, 60%)',
                            label: 'Light green'
                        },
                        {
                            color: 'hsl(120, 75%, 60%)',
                            label: 'Green'
                        },
                        {
                            color: 'hsl(150, 75%, 60%)',
                            label: 'Aquamarine'
                        },
                        {
                            color: 'hsl(180, 75%, 60%)',
                            label: 'Turquoise'
                        },
                        {
                            color: 'hsl(210, 75%, 60%)',
                            label: 'Light blue'
                        },
                        {
                            color: 'hsl(240, 75%, 60%)',
                            label: 'Blue'
                        },
                        {
                            color: 'hsl(270, 75%, 60%)',
                            label: 'Purple'
                        }
                    ]
                },
                fontBackgroundColor: {
                    colors: [
                        {
                            color: 'hsl(0, 75%, 60%)',
                            label: 'Red'
                        },
                        {
                            color: 'hsl(30, 75%, 60%)',
                            label: 'Orange'
                        },
                        {
                            color: 'hsl(60, 75%, 60%)',
                            label: 'Yellow'
                        },
                        {
                            color: 'hsl(90, 75%, 60%)',
                            label: 'Light green'
                        },
                        {
                            color: 'hsl(120, 75%, 60%)',
                            label: 'Green'
                        },
                        {
                            color: 'hsl(150, 75%, 60%)',
                            label: 'Aquamarine'
                        },
                        {
                            color: 'hsl(180, 75%, 60%)',
                            label: 'Turquoise'
                        },
                        {
                            color: 'hsl(210, 75%, 60%)',
                            label: 'Light blue'
                        },
                        {
                            color: 'hsl(240, 75%, 60%)',
                            label: 'Blue'
                        },
                        {
                            color: 'hsl(270, 75%, 60%)',
                            label: 'Purple'
                        }
                    ]
                },
                heading: {
                    options: [
                        { model: 'paragraph', title: 'Paragraph', class: 'ck-heading_paragraph' },
                        { model: 'heading1', view: 'h1', title: 'Heading 1', class: 'ck-heading_heading1' },
                        { model: 'heading2', view: 'h2', title: 'Heading 2', class: 'ck-heading_heading2' },
                        { model: 'heading3', view: 'h3', title: 'Heading 3', class: 'ck-heading_heading3' },
                        { model: 'heading4', view: 'h4', title: 'Heading 4', class: 'ck-heading_heading4' },
                        { model: 'heading5', view: 'h5', title: 'Heading 5', class: 'ck-heading_heading5' },
                        { model: 'heading6', view: 'h6', title: 'Heading 6', class: 'ck-heading_heading6' }
                    ]
                },
                placeholder: this.props.placeholder || 'ابدأ بكتابة محتوى الوثيقة...',
                table: {
                    contentToolbar: [
                        'tableColumn',
                        'tableRow',
                        'mergeTableCells',
                        'tableCellProperties',
                        'tableProperties'
                    ]
                },
                image: {
                    toolbar: [
                        'imageTextAlternative',
                        'toggleImageCaption',
                        'imageStyle:inline',
                        'imageStyle:block',
                        'imageStyle:side',
                        'linkImage'
                    ]
                },
                link: {
                    decorators: {
                        addTargetToExternalLinks: true,
                        defaultProtocol: 'https://',
                        toggleDownloadable: {
                            mode: 'manual',
                            label: 'Downloadable',
                            attributes: {
                                download: 'file'
                            }
                        }
                    }
                },
                alignment: {
                    options: ['left', 'right', 'center', 'justify']
                },
                codeBlock: {
                    languages: [
                        { language: 'css', label: 'CSS' },
                        { language: 'html', label: 'HTML' },
                        { language: 'javascript', label: 'JavaScript' },
                        { language: 'php', label: 'PHP' },
                        { language: 'python', label: 'Python' },
                        { language: 'xml', label: 'XML' },
                        { language: 'sql', label: 'SQL' }
                    ]
                },
                htmlSupport: {
                    allow: [
                        {
                            name: /.*/,
                            attributes: true,
                            classes: true,
                            styles: true
                        }
                    ]
                }
            };

            this.editor = await ClassicEditor.create(this.editorRef.el, editorConfig);
            
            if (this.props.record && this.props.record.data[this.props.name]) {
                this.editor.setData(this.props.record.data[this.props.name]);
            }
            this.editor.model.document.on('change:data', () => {
                if (!this.props.readonly) {
                    const data = this.editor.getData();
                    this.props.record.update({ [this.props.name]: data });
                }
            });

            if (this.props.readonly) {
                this.editor.enableReadOnlyMode('readonly-mode');
            }

            this.state.isLoading = false;
            this.state.isReady = true;

        } catch (error) {
            console.error('خطأ في تحميل CKEditor:', error);
            this.notification.add(
                'فشل في تحميل محرر النصوص المتقدم',
                { type: 'danger' }
            );
            this.state.isLoading = false;
        }
    }

    destroyEditor() {
        if (this.editor) {
            this.editor.destroy()
                .then(() => {
                    this.editor = null;
                })
                .catch(error => {
                    console.error('خطأ في إغلاق المحرر:', error);
                });
        }
    }

    get value() {
        return this.props.record.data[this.props.name] || '';
    }

    get editorHeight() {
        return this.props.height || '400px';
    }
}

registry.category("fields").add("ckeditor5_widget", CKEditor5Widget);

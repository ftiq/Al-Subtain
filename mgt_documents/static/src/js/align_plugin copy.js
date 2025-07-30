/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Plugin } from "@html_editor/plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { withSequence } from "@html_editor/utils/resource";
import { isBlock } from "@html_editor/utils/blocks";
import { isTextNode } from "@html_editor/utils/dom_info";


class AlignPlugin extends Plugin {
    static id = "align_text";
    static dependencies = ["selection"];

    isSelectionFormat(formatName, traversedNodes = this.dependencies.selection.getTraversedNodes()) {
        const selectedNodes = traversedNodes.filter(isTextNode);
        if (!selectedNodes.length) {
            return false;
        }
        const textAlignValue = formatName.replace("formatAlignLeft", "left")
                                       .replace("formatAlignCenter", "center")
                                       .replace("formatAlignRight", "right");
        return selectedNodes.every(node => {
            let parent = node.parentNode;
            while (parent && parent !== this.editable) {
                const textAlign = parent.style.textAlign;
                if (textAlign === textAlignValue) {
                    return true;
                }
                if (isBlock(parent)) {
                    break;
                }
                parent = parent.parentNode;
            }
            return false;
        });
    }

    resources = {
        user_commands: [
            {
                id: "formatAlignLeft",
                title: _t("Align Left"),
                description: _t("Align text to the left"),
                icon: "fa-align-left",
                run: () => this.document.execCommand("justifyLeft"),
            },
            {
                id: "formatAlignCenter",
                title: _t("Align Center"),
                description: _t("Center align text"),
                icon: "fa-align-center",
                run: () => this.document.execCommand("justifyCenter"),
            },
            {
                id: "formatAlignRight",
                title: _t("Align Right"),
                description: _t("Align text to the right"),
                icon: "fa-align-right",
                run: () => this.document.execCommand("justifyRight"),
            },
            {
                id: "formatAlignJustify",
                title: _t("Justify"),
                description: _t("Justify text"),
                icon: "fa-align-justify",
                run: () => this.document.execCommand("justifyFull"),
            },
        ],
        shortcuts: [
            { hotkey: "control+shift+l", commandId: "formatAlignLeft" },
            { hotkey: "control+shift+c", commandId: "formatAlignCenter" },
            { hotkey: "control+shift+r", commandId: "formatAlignRight" },
            { hotkey: "control+shift+j", commandId: "formatAlignJustify" },
        ],
        toolbar_groups: withSequence(20, { id: "alignement" }),
        toolbar_items: [
            {
                id: "align_left",
                groupId: "alignement",
                commandId: "formatAlignLeft",
                isActive: (sel, nodes) => this.isSelectionFormat("formatAlignLeft", nodes),
            },
            {
                id: "align_center",
                groupId: "alignement",
                commandId: "formatAlignCenter",
                isActive: (sel, nodes) => this.isSelectionFormat("formatAlignCenter", nodes),
            },
            {
                id: "align_right",
                groupId: "alignement",
                commandId: "formatAlignRight",
                isActive: (sel, nodes) => this.isSelectionFormat("formatAlignRight", nodes),
            },
            {
                id: "align_justify",
                groupId: "alignement",
                commandId: "formatAlignJustify",
                isActive: (sel, nodes) => this.isSelectionFormat("formatAlignJustify", nodes),
            },
        ],
        powerbox_items: [
            { categoryId: "structure", commandId: "formatAlignLeft" },
            { categoryId: "structure", commandId: "formatAlignCenter" },
            { categoryId: "structure", commandId: "formatAlignRight" },
            { categoryId: "structure", commandId: "formatAlignJustify" },
        ],
    };
}


MAIN_PLUGINS.push(AlignPlugin);
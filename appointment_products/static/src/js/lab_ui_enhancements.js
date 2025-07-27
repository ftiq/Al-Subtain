/**
 * appointment_products.lab_ui_enhancements
 * 



*/
import { patch } from "@web/core/utils/patch";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

patch(KanbanRenderer.prototype, {
    /**

    * @override
     */
    _render(record) {
        const el = super._render(record);
        if (record.model === "lab.sample" && record.data.state && el) {
            el.dataset.state = record.data.state;

            el.style.opacity = 0;
            requestAnimationFrame(() => {
                el.style.transition = "opacity 300ms";
                el.style.opacity = 1;
            });
        }
        return el;
    },
}); 
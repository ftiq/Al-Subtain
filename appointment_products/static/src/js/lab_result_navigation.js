/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

patch(ListController.prototype, {

    
    onCellKeydown(hotkey, { cell, grid }) {
        console.log("Lab Navigation: Key pressed:", hotkey, "Model:", this.model.resModel);
        

        if (this.model.resModel !== 'lab.result.line') {
            return super.onCellKeydown(hotkey, { cell, grid });
        }


        if (hotkey === "Enter" || hotkey === "Tab") {
            const currentRecord = grid.getRecord(cell);
            const currentColumn = grid.getColumn(cell);
            
            console.log("Lab Navigation: Current record:", currentRecord?.data || null);
            console.log("Lab Navigation: Current field:", currentColumn?.name || null);
            

            const isNumericField = ['result_value_numeric', 'value_numeric'].includes(currentColumn?.name);
            const isComputed = currentRecord?.data?.is_computed || false;
            
            if (isNumericField && !isComputed) {

                const nextCell = this._findNextEditableNumericCell(cell, grid);
                if (nextCell) {
                    console.log("Lab Navigation: Moving to next cell:", nextCell);
                    grid.selectCell(nextCell.col, nextCell.row);
                    grid.editCell(nextCell.col, nextCell.row);
                    return;
                }
            }
        }
        
        return super.onCellKeydown(hotkey, { cell, grid });
    },


    
    _findNextEditableNumericCell(currentCell, grid) {
        const numericFields = ['result_value_numeric', 'value_numeric'];
        const totalRows = grid.model.root.records.length;
        const totalCols = grid.columns.length;
        

        let startRow = currentCell.row;
        let startCol = currentCell.col + 1;
        

        for (let col = startCol; col < totalCols; col++) {
            const column = grid.columns[col];
            if (numericFields.includes(column.name)) {
                const record = grid.getRecord({ row: startRow, col });
                if (record && record.data && !record.data.is_computed) {
                    return { row: startRow, col, field: column.name };
                }
            }
        }
        

        for (let row = startRow + 1; row < totalRows; row++) {
            const record = grid.getRecord({ row, col: 0 });
            

            if (record && record.data) {

                if (record.data.is_computed) {
                    continue;
                }
                

                if (record.data.is_summary_field) {
                    continue;
                }
            }
            

            for (let col = 0; col < totalCols; col++) {
                const column = grid.columns[col];
                if (numericFields.includes(column.name)) {
                    return { row, col, field: column.name };
                }
            }
        }
        
        return null;
    }
});

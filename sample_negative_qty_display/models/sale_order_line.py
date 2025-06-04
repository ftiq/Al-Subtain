class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ... (هنا يمكن أن يكون تعريف onchange كما ورد أعلاه أيضاً) ...

    @api.model
    def create(self, vals):
        # إذا كان المنتج هو المنتج الخاص (ID = 735)، تأكد أن الكمية سالبة
        if vals.get('product_id') == 735:
            qty = vals.get('product_uom_qty', 0.0) or 0.0
            if qty > 0:
                vals['product_uom_qty'] = -qty
        return super(SaleOrderLine, self).create(vals)

    def write(self, vals):
        # يمكن أن يكون التحقق في write أكثر تعقيداً قليلاً لأننا نتعامل مع سجلات موجودة
        for line in self:
            # حدد المنتج والكمية الحالية والمحدثة إن وجدت
            product = vals.get('product_id', line.product_id.id)
            qty = vals.get('product_uom_qty', line.product_uom_qty)
            # إذا كان المنتج خاصاً وتوجد كمية موجبة، حولها إلى سالبة
            if product == 735 and qty and qty > 0:
                vals.update({'product_uom_qty': -qty})
        return super(SaleOrderLine, self).write(vals)

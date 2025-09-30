from odoo import fields, models, api

class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    # إعادة تعريف الحقل بدون الـ depends المكسورة
    purchase_order_count = fields.Integer(
        string="Purchase Orders (Patched)",
        compute="_compute_purchase_order_count_fixed"
    )

    @api.depends()  # بدون product_line_ids
    def _compute_purchase_order_count_fixed(self):
        for rec in self:
            rec.purchase_order_count = 0

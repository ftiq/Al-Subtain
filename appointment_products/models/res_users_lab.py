from odoo import models, api, _
from odoo.exceptions import UserError


class ResUsersLabSecurity(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        technician_group = self.env.ref('appointment_products.group_lab_technician', raise_if_not_found=False)
        manager_group = self.env.ref('appointment_products.group_lab_manager', raise_if_not_found=False)

        current_uid = self.env.uid

        res = super(ResUsersLabSecurity, self).write(vals)

        if technician_group and manager_group:
            for user in self:
                if user.id == current_uid:
                    if user.has_group('appointment_products.group_lab_manager') and user.has_group('appointment_products.group_lab_technician'):
                        raise UserError( _("🚫 لا يمكنك إضافة صلاحية 'فني المختبر' إلى حسابك لأنك مدير المختبر. الرجاء استخدام حساب آخر أو إزالة صلاحية مدير المختبر أولاً."))
        return res 
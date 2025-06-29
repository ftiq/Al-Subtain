# -*- coding: utf-8 -*-
from odoo import models, fields, _


class StockPickingLabNotify(models.Model):
    _inherit = 'stock.picking'

    lab_notified = fields.Boolean(string='تم إشعار المختبر', tracking=True)

    def action_notify_lab(self):
        """يستدعيه مستخدم المخزون بعد إتمام الاستلام لإبلاغ المختبر."""
        ActivityType = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        lab_group = self.env.ref('appointment_products.group_lab_inspector', raise_if_not_found=False)

        if not lab_group:
            return

        tasks_model = self.env['project.task']

        lab_partners = lab_group.users.mapped('partner_id').ids

        for picking in self:
            if picking.lab_notified:
                continue

            tasks = tasks_model.search([('stock_receipt_id', '=', picking.id)])
            for task in tasks:
                task.write({
                    'stock_done': True,
                    'stock_done_date': fields.Datetime.now(),
                })

                if lab_partners:
                    task.message_subscribe(partner_ids=lab_partners)

                task.message_post(
                    body=_('تم إنهاء المهمة المخزنية لهذا الاستلام — جاهزة للفحص المختبري.'),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    partner_ids=lab_partners,
                )

                for user in lab_group.users:
                    task.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        user_id=user.id,
                        summary=_('بدء الفحص المختبري'),
                        note=_('يرجى البدء بإجراءات الفحص بعد إنهاء المخزون.'),
                    )

            picking.write({'lab_notified': True})

            if lab_partners:
                picking.message_subscribe(partner_ids=lab_partners)

            picking.message_post(
                body=_('تم إشعار المختبر بأن الاستلام مكتمل.'),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
                partner_ids=lab_partners,
            )

    def action_do_nothing(self):
        """زر غير فعّال لإظهار نص تم الإشعار"""
        return True 
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockPickingLabNotify(models.Model):
    _inherit = 'stock.picking'

    lab_notified = fields.Boolean(string='تم إشعار المختبر', tracking=True)
    lab_notification_status = fields.Char(string='حالة الإشعار', compute='_compute_lab_notification_status', store=False)
    is_task_related = fields.Boolean(string='مرتبط بمهمة', compute='_compute_is_task_related', store=False)
    has_all_lab_codes = fields.Boolean(string='تم إدخال جميع الرموز المختبرية', compute='_compute_has_all_lab_codes', store=False)

    def _compute_is_task_related(self):
        """تحديد ما إذا كان الاستلام مرتبط بمهمة خدمة ميدانية"""
        for record in self:
            record.is_task_related = bool(self.env['project.task'].search([('stock_receipt_id', '=', record.id)], limit=1))
            
    def _compute_has_all_lab_codes(self):
        """تحديد ما إذا كانت جميع سطور الحركة تحتوي على رموز مختبرية"""
        for record in self:
            move_lines_needing_codes = record.move_line_ids.filtered(lambda line: line.product_id)
            if not move_lines_needing_codes:
                record.has_all_lab_codes = False
            else:
                lines_with_codes = move_lines_needing_codes.filtered(lambda line: line.field_code)
                record.has_all_lab_codes = len(lines_with_codes) == len(move_lines_needing_codes)

    @api.depends('lab_notified', 'state', 'is_task_related')
    def _compute_lab_notification_status(self):
        for record in self:
            if not record.is_task_related:
                record.lab_notification_status = ''
            elif record.state == 'done':
                record.lab_notification_status = 'تم التصديق'
            elif record.lab_notified:
                record.lab_notification_status = 'تم الإشعار'
            else:
                record.lab_notification_status = 'لم يتم الإشعار'

    def action_notify_lab(self):
        """يستدعيه مستخدم المخزون بعد إتمام الاستلام لإبلاغ المختبر."""
        ActivityType = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        lab_group = self.env.ref('appointment_products.group_lab_manager', raise_if_not_found=False)

        if not lab_group:
            return

        tasks_model = self.env['project.task']

        lab_partners = lab_group.users.mapped('partner_id').ids

        for picking in self:
            if picking.lab_notified or not picking.is_task_related:
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


class StockPickingTypeLab(models.Model):
    _inherit = 'stock.picking.type'

    count_picking_lab_ready = fields.Integer(
        string='عدد الجاهز للفحص',
        compute='_compute_count_picking_lab_ready'
    )

    def _compute_count_picking_lab_ready(self):
        """حساب عدد السجلات التي تم إشعارها ولكن لم يتم تصديقها بعد"""
        for record in self:
            domain = [
                ('picking_type_id', '=', record.id),
                ('lab_notified', '=', True),
                ('state', '!=', 'done'),
                ('state', '!=', 'cancel')
            ]
            record.count_picking_lab_ready = self.env['stock.picking'].search_count(domain)

    def get_action_picking_tree_lab_ready(self):
        """عرض السجلات الجاهزة للفحص"""
        return self._get_action('appointment_products.action_picking_tree_lab_ready')

    def _get_action(self, action_xmlid):
        """مساعد لإنشاء الإجراءات"""
        action = self.env["ir.actions.actions"]._for_xml_id(action_xmlid)
        if self:
            action['display_name'] = self.display_name
        return action 
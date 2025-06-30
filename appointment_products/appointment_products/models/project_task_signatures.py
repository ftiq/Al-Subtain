# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProjectTaskSignatures(models.Model):
    _inherit = 'project.task'



    exec_signature = fields.Binary(string='توقيع ممثل الجهة المنفذة', attachment=True)
    exec_signer_name = fields.Char(string='اسم ممثل الجهة المنفذة')
    exec_is_signed = fields.Boolean(string='تم التوقيع (منفذ)', compute='_compute_exec_is_signed', store=True)



    super_signature = fields.Binary(string='توقيع ممثل الجهة المشرفة', attachment=True)
    super_signer_name = fields.Char(string='اسم ممثل الجهة المشرفة')
    super_is_signed = fields.Boolean(string='تم التوقيع (مشرف)', compute='_compute_super_is_signed', store=True)



    company_signature = fields.Binary(string='توقيع ممثل شركة السبطين', attachment=True)
    company_signer_name = fields.Char(string='اسم ممثل شركة السبطين')
    company_is_signed = fields.Boolean(string='تم التوقيع (السبطين)', compute='_compute_company_is_signed', store=True)



    attachment_image = fields.Binary(string='صورة مرفقة', attachment=True)
    image_is_attached = fields.Boolean(string='تم إرفاق الصورة', compute='_compute_image_is_attached', store=True)
    
    # الصور المرفقة الجديدة
    attachment_ids = fields.One2many(
        'project.task.attachment',
        'task_id',
        string='الصور المرفقة'
    )
    attachment_count = fields.Integer(
        string='عدد الصور',
        compute='_compute_attachment_count',
        store=False
    )


    @api.depends('exec_signature')
    def _compute_exec_is_signed(self):
        for rec in self:
            rec.exec_is_signed = bool(rec.exec_signature)

    @api.depends('super_signature')
    def _compute_super_is_signed(self):
        for rec in self:
            rec.super_is_signed = bool(rec.super_signature)

    @api.depends('company_signature')
    def _compute_company_is_signed(self):
        for rec in self:
            rec.company_is_signed = bool(rec.company_signature)

    @api.depends('attachment_image')
    def _compute_image_is_attached(self):
        for rec in self:
            rec.image_is_attached = bool(rec.attachment_image)
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            # تحديث العدد بشكل فوري من قاعدة البيانات
            attachment_count = self.env['project.task.attachment'].search_count([
                ('task_id', '=', rec.id)
            ])
            rec.attachment_count = attachment_count


    def action_clear_exec_signature(self):
        self.write({'exec_signature': False, 'exec_signer_name': False})
        return True

    def action_clear_super_signature(self):
        self.write({'super_signature': False, 'super_signer_name': False})
        return True

    def action_clear_company_signature(self):
        self.write({'company_signature': False, 'company_signer_name': False})
        return True

    def action_clear_attachment_image(self):
        """مسح الصورة المرفقة"""
        self.write({'attachment_image': False})
        return True

    def action_preview_attachment_image(self):
        """فتح معاينة للصورة المرفقة في تبويب جديد باستخدام /web/image"""
        self.ensure_one()
        if not self.attachment_image:
            return False
        url = (
            "/web/image?model=project.task&id=%s&field=attachment_image&unique=" % self.id
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    @api.onchange('user_ids')
    def _onchange_user_company_signer(self):
        """تعيين الاسم تلقائياً من أول مستخدم مُسند إذا كان الحقل فارغاً."""
        for rec in self:
            if not rec.company_signer_name and rec.user_ids:
                rec.company_signer_name = rec.user_ids[0].name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('company_signer_name') and vals.get('user_ids'):
                user_ids_commands = vals['user_ids']
                if user_ids_commands and isinstance(user_ids_commands, list):

                    first_id = None
                    for command in user_ids_commands:
                        if isinstance(command, (tuple, list)):
                            if command[0] in (4, 1):
                                first_id = command[1]
                                break
                            if command[0] == 6 and command[2]:
                                first_id = command[2][0]
                                break
                    if first_id:
                        user = self.env['res.users'].browse(first_id)
                        vals['company_signer_name'] = user.name
        return super().create(vals_list)
    
    # دوال الصور المرفقة
    def action_view_attachments(self):
        """عرض الصور المرفقة"""
        self.ensure_one()
        return {
            'name': 'صور مرفقة - %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.attachment',
            'view_mode': 'kanban,list,form',
            'context': {
                'default_task_id': self.id,
                'search_default_task_id': self.id,
            },
            'domain': [('task_id', '=', self.id)],
        }
    
    def action_add_attachment(self):
        """إضافة صورة واحدة"""
        self.ensure_one()
        return {
            'name': 'إضافة صورة مرفقة',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.attachment',
            'view_mode': 'form',
            'context': {
                'default_task_id': self.id,
            },
            'target': 'new',
        }
    
    def action_bulk_add_attachments(self):
        """إضافة صور متعددة باستخدام الـ wizard"""
        self.ensure_one()
        return {
            'name': 'رفع صور متعددة',
            'type': 'ir.actions.act_window',
            'res_model': 'task.attachment.wizard',
            'view_mode': 'form',
            'context': {
                'default_task_id': self.id,
            },
            'target': 'new',
        }
    
    def action_migrate_old_attachment(self):
        """نقل الصورة القديمة إلى النظام الجديد"""
        self.ensure_one()
        if not self.attachment_image:
            return False
        
        self.env['project.task.attachment'].create({
            'task_id': self.id,
            'name': 'صورة منقولة من النظام القديم',
            'image': self.attachment_image,
            'attachment_type': 'other',
            'description': 'تم نقل هذه الصورة من النظام القديم',
        })
        
        # مسح الصورة
        self.attachment_image = False
        
        # إعادة حساب عدد الصور بعد النقل
        self._compute_attachment_count()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def refresh_attachment_count(self):
        """تحديث عدد الصور بشكل فوري"""
        self.ensure_one()
        self._compute_attachment_count()
        return True 
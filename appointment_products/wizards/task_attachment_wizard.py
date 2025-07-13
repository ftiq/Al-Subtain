# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64


class TaskAttachmentWizard(models.TransientModel):
    _name = 'task.attachment.wizard'
    _description = 'أداة رفع الصور المتعددة'

    task_id = fields.Many2one(
        'project.task',
        string='المهمة',
        required=True,
        readonly=True
    )
    
    attachment_type = fields.Selection([
        ('before', 'قبل التنفيذ'),
        ('during', 'أثناء التنفيذ'),
        ('after', 'بعد التنفيذ'),
        ('signature', 'مرفق مع التوقيع'),
        ('problem', 'مشكلة أو ملاحظة'),
        ('other', 'أخرى')
    ], string='نوع المرفق', default='other', required=True)
    
    description = fields.Text(
        string='وصف عام للصور',
        help='وصف مشترك لجميع الصور التي سيتم رفعها'
    )
    
    is_public = fields.Boolean(
        string='صور عامة',
        default=False,
        help='إذا كانت الصور قابلة للعرض لجميع المستخدمين'
    )
    

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='الصور',
        help='يمكنك تحديد ورفع عدة صور مرة واحدة عبر هذا الحقل',
    )

    image_1 = fields.Binary(string='الصورة الأولى', attachment=True)
    name_1 = fields.Char(string='وصف الصورة الأولى')
    
    image_2 = fields.Binary(string='الصورة الثانية', attachment=True)
    name_2 = fields.Char(string='وصف الصورة الثانية')
    
    image_3 = fields.Binary(string='الصورة الثالثة', attachment=True)
    name_3 = fields.Char(string='وصف الصورة الثالثة')
    
    image_4 = fields.Binary(string='الصورة الرابعة', attachment=True)
    name_4 = fields.Char(string='وصف الصورة الرابعة')
    
    image_5 = fields.Binary(string='الصورة الخامسة', attachment=True)
    name_5 = fields.Char(string='وصف الصورة الخامسة')

    def action_upload_images(self):
        """رفع الصور وإنشاء السجلات"""
        self.ensure_one()
        
        if not self.task_id:
            raise ValidationError(_('يجب تحديد المهمة'))
        
        created_attachments = []
        

        images_data = []
        if self.attachment_ids:
            for att in self.attachment_ids:

                images_data.append((att.datas, att.name))


        legacy_images = [
            (self.image_1, self.name_1 or f'صورة 1 - {self.task_id.name}'),
            (self.image_2, self.name_2 or f'صورة 2 - {self.task_id.name}'),
            (self.image_3, self.name_3 or f'صورة 3 - {self.task_id.name}'),
            (self.image_4, self.name_4 or f'صورة 4 - {self.task_id.name}'),
            (self.image_5, self.name_5 or f'صورة 5 - {self.task_id.name}'),
        ]

        images_data += [img for img in legacy_images if img[0]]
        
        sequence_start = len(self.task_id.attachment_ids) * 10
        
        for i, (image, name) in enumerate(images_data):
            if image:
                attachment_vals = {
                    'task_id': self.task_id.id,
                    'name': name,
                    'image': image,
                    'attachment_type': self.attachment_type,
                    'description': self.description,
                    'is_public': self.is_public,
                    'sequence': sequence_start + (i + 1) * 10,
                }
                
                attachment = self.env['project.task.attachment'].create(attachment_vals)
                created_attachments.append(attachment)
        
        if not created_attachments:
            raise ValidationError(_('يجب رفع صورة واحدة على الأقل!'))
        
        self.task_id.refresh_attachment_count()
        

        if len(created_attachments) == 1:
            return {
                'name': _('الصورة المرفوعة'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.attachment',
                'res_id': created_attachments[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': _('الصور المرفوعة - %s') % self.task_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.attachment',
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', [a.id for a in created_attachments])],
                'target': 'current',
            }

    def action_upload_and_close(self):
        """رفع الصور وإغلاق النافذة"""
        self.action_upload_images()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الرفع بنجاح'),
                'message': _('تم رفع الصور وإضافتها للمهمة بنجاح.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.onchange('attachment_type')
    def _onchange_attachment_type(self):
        """تحديث الوصف تلقائياً بناءً على نوع المرفق"""
        if self.attachment_type:
            type_descriptions = {
                'before': 'صور قبل بدء التنفيذ',
                'during': 'صور أثناء التنفيذ',
                'after': 'صور بعد إنهاء التنفيذ',
                'signature': 'صور مرفقة مع التوقيع',
                'problem': 'صور توضح مشكلة أو ملاحظة',
                'other': 'صور متنوعة',
            }
            self.description = type_descriptions.get(self.attachment_type, '')


    def unlink(self):
        """عند حذف سجل الـ Wizard احذف أيضاً المرفقات المؤقتة التى رُفعت عن طريقه."""
        if self.attachment_ids:
            self.attachment_ids.unlink()
        return super().unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_bulk_add_attachments(self):
        """فتح أداة رفع الصور المتعددة"""
        self.ensure_one()
        return {
            'name': _('رفع صور متعددة'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.attachment.wizard',
            'view_mode': 'form',
            'context': {
                'default_task_id': self.id,
            },
            'target': 'new',
        } 
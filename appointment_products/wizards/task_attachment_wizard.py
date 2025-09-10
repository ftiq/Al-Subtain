# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import base64


class TaskAttachmentWizard(models.TransientModel):
    _name = 'task.attachment.wizard'
    _description = 'Multiple image upload wizard'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        readonly=True
    )
    
    attachment_type = fields.Selection([
        ('before', 'Before Execution'),
        ('during', 'During Execution'),
        ('after', 'After Execution'),
        ('signature', 'Signature'),
        ('problem', 'Problem or Note'),
        ('other', 'Other')
    ], string='Attachment Type', default='other', required=True)
    
    description = fields.Text(
        string='General Description of Images',
        help='Common description for all images to be uploaded'
    )
    
    is_public = fields.Boolean(
        string='Public Images',
        default=False,
        help='If the images are viewable by all users'
    )
    

    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Images',
        help='You can select and upload multiple images at once through this field',
    )

    image_1 = fields.Binary(string='First Image', attachment=True)
    name_1 = fields.Char(string='Description of First Image')
    
    image_2 = fields.Binary(string='Second Image', attachment=True)
    name_2 = fields.Char(string='Description of Second Image')
    
    image_3 = fields.Binary(string='Third Image', attachment=True)
    name_3 = fields.Char(string='Description of Third Image')
    
    image_4 = fields.Binary(string='Fourth Image', attachment=True)
    name_4 = fields.Char(string='Description of Fourth Image')
    
    image_5 = fields.Binary(string='Fifth Image', attachment=True)
    name_5 = fields.Char(string='Description of Fifth Image')

    def action_upload_images(self):
        """Upload images and create records"""
        self.ensure_one()
        
        if not self.task_id:
            raise ValidationError(_('Task must be selected'))
        
        created_attachments = []
        

        images_data = []
        if self.attachment_ids:
            for att in self.attachment_ids:

                images_data.append((att.datas, att.name))


        legacy_images = [
            (self.image_1, self.name_1 or f'First Image - {self.task_id.name}'),
            (self.image_2, self.name_2 or f'Second Image - {self.task_id.name}'),
            (self.image_3, self.name_3 or f'Third Image - {self.task_id.name}'),
            (self.image_4, self.name_4 or f'Fourth Image - {self.task_id.name}'),
            (self.image_5, self.name_5 or f'Fifth Image - {self.task_id.name}'),
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
            raise ValidationError(_('At least one image must be uploaded!'))
        
        self.task_id.refresh_attachment_count()
        

        if len(created_attachments) == 1:
            return {
                'name': _('Uploaded Image'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.attachment',
                'res_id': created_attachments[0].id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'name': _('Uploaded Images - %s') % self.task_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'project.task.attachment',
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', [a.id for a in created_attachments])],
                'target': 'current',
            }

    def action_upload_and_close(self):
        """Upload images and close the window"""
        self.action_upload_images()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Upload Successful'),
                'message': _('Images uploaded and added to the task successfully.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    @api.onchange('attachment_type')
    def _onchange_attachment_type(self):
        """Update the description automatically based on the attachment type"""
        if self.attachment_type:
            type_descriptions = {
                'before': 'Images before execution',
                'during': 'Images during execution',
                'after': 'Images after execution',
                'signature': 'Images attached with signature',
                'problem': 'Images showing a problem or note',
                'other': 'Multiple images',
            }
            self.description = type_descriptions.get(self.attachment_type, '')


    def unlink(self):
        """When deleting the Wizard record, also delete the temporary attachments uploaded through it."""
        if self.attachment_ids:
            self.attachment_ids.unlink()
        return super().unlink()


class ProjectTask(models.Model):
    _inherit = 'project.task'

    def action_bulk_add_attachments(self):
        """Open the multiple image upload wizard"""
        self.ensure_one()
        return {
            'name': _('Upload Multiple Images'),
            'type': 'ir.actions.act_window',
            'res_model': 'task.attachment.wizard',
            'view_mode': 'form',
            'context': {
                'default_task_id': self.id,
            },
            'target': 'new',
        } 
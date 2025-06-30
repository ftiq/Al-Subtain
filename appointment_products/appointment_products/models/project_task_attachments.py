# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProjectTaskAttachment(models.Model):
    _name = 'project.task.attachment'
    _description = 'صور مرفقة بالمهمة'
    _order = 'sequence, create_date desc'
    _rec_name = 'name'

    task_id = fields.Many2one(
        'project.task',
        string='المهمة',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    name = fields.Char(
        string='وصف الصورة',
        required=True,
        help='وصف مختصر للصورة المرفقة'
    )
    
    image = fields.Binary(
        string='الصورة',
        required=True,
        attachment=True,
        help='الصورة المرفقة'
    )
    
    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='ترتيب عرض الصورة'
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
        string='تفاصيل إضافية',
        help='تفاصيل أو ملاحظات حول الصورة'
    )
    
    date_taken = fields.Datetime(
        string='تاريخ التقاط الصورة',
        default=fields.Datetime.now,
        help='تاريخ ووقت التقاط الصورة'
    )
    
    uploaded_by = fields.Many2one(
        'res.users',
        string='رفعت بواسطة',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    file_size = fields.Float(
        string='حجم الملف (KB)',
        compute='_compute_file_size',
        store=True,
        help='حجم الملف بالكيلوبايت'
    )
    
    is_public = fields.Boolean(
        string='عامة',
        default=True,
        help='إذا كانت الصورة قابلة للعرض لجميع المستخدمين'
    )

    @api.depends('image')
    def _compute_file_size(self):
        """حساب حجم الملف"""
        for record in self:
            if record.image:
                import base64
                try:
                    file_data = base64.b64decode(record.image)
                    record.file_size = len(file_data) / 1024  # تحويل إلى KB
                except:
                    record.file_size = 0.0
            else:
                record.file_size = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """إضافة ترقيم تلقائي للاسم وتحديث عدد الصور"""
        for vals in vals_list:
            if not vals.get('name') and vals.get('task_id'):
                task = self.env['project.task'].browse(vals['task_id'])
                attachment_count = self.search_count([('task_id', '=', task.id)])
                vals['name'] = f"صورة {attachment_count + 1} - {task.name}"
        
        result = super().create(vals_list)
        

        for record in result:
            if record.task_id:
                record.task_id._compute_attachment_count()
        
        return result

    def action_preview(self):
        """فتح معاينة للصورة في نافذة منفصلة"""
        self.ensure_one()
        if not self.image:
            return False
        
        url = f"/web/image?model=project.task.attachment&id={self.id}&field=image&unique="
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_download(self):
        """تحميل الصورة"""
        self.ensure_one()
        if not self.image:
            return False
            
        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/content?model=project.task.attachment&id={self.id}&field=image&download=true&filename={self.name}.jpg",
            'target': 'self',
        }

    @api.constrains('image')
    def _check_image_size(self):
        """التحقق من حجم الصورة (حد أقصى 10 ميجا)"""
        icp = self.env['ir.config_parameter'].sudo()
        max_mb = int(icp.get_param('appointment_products.max_image_size_mb', 10))
        max_size = max_mb * 1024 * 1024 if max_mb > 0 else 0
        for record in self:
            if record.image:
                import base64
                try:
                    file_data = base64.b64decode(record.image)
                    if max_size and len(file_data) > max_size:
                        raise ValidationError(_('حجم الصورة كبير جداً! الحد الأقصى المسموح به هو %s ميجابايت.') % max_mb)
                except:
                    pass
    

    
    def unlink(self):
        """تحديث عدد الصور بعد الحذف"""
        tasks = self.mapped('task_id')
        result = super().unlink()
        # تحديث عدد الصور للمهام المرتبطة
        for task in tasks:
            task._compute_attachment_count()
        return result


 
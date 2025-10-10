# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DocumentHistory(models.Model):
    """نموذج سجل تاريخ الوثائق لتتبع جميع التغييرات"""
    
    _name = 'document.history'
    _description = 'سجل تاريخ الوثائق'
    _order = 'timestamp desc, id desc'
    _rec_name = 'display_name'
    

    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='المستخدم',
        required=True,
        default=lambda self: self.env.user,
        index=True
    )
    
    timestamp = fields.Datetime(
        string='وقت التغيير',
        required=True,
        default=fields.Datetime.now,
        index=True
    )
    
    action = fields.Selection([
        ('created', 'تم الإنشاء'),
        ('updated', 'تم التحديث'),
        ('deleted', 'تم الحذف'),
        ('submitted', 'تم التقديم'),
        ('reviewed', 'تم المراجعة'),
        ('approved', 'تم الاعتماد'),
        ('rejected', 'تم الرفض'),
        ('reset', 'تم إعادة التعيين'),
        ('archived', 'تم الأرشفة'),
        ('cancelled', 'تم الإلغاء'),
        ('restored', 'تم الاستعادة'),
        ('signed', 'تم التوقيع'),
        ('completed', 'تم إنهاء الموافقة'),
        ('attachment_added', 'تم إضافة مرفق'),
        ('attachment_removed', 'تم حذف مرفق'),
        ('comment_added', 'تم إضافة تعليق'),
        ('access_granted', 'تم منح الوصول'),
        ('access_revoked', 'تم إلغاء الوصول'),
        ('other', 'أخرى')
    ], string='نوع العملية', required=True, index=True)
    
    description = fields.Text(
        string='وصف التغيير',
        required=True
    )
    

    previous_state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدمة'),
        ('in_review', 'قيد المراجعة'),
        ('in_progress', 'قيد التنفيذ'),
        ('pending_approval', 'في انتظار الموافقة'),
        ('waiting_approval', 'في انتظار الموافقة'),
        ('approved', 'معتمدة'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
        ('archived', 'مؤرشفة'),
        ('received', 'مستلمة'),
        ('registered', 'مسجلة'),
        ('routed', 'موجهة'),
        ('under_review', 'قيد المراجعة'),
        ('in_execution', 'قيد التنفيذ'),
        ('rejected', 'مرفوضة'),
        ('on_hold', 'معلقة')
    ], string='الحالة السابقة')
    
    new_state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدمة'),
        ('in_review', 'قيد المراجعة'),
        ('in_progress', 'قيد التنفيذ'),
        ('pending_approval', 'في انتظار الموافقة'),
        ('waiting_approval', 'في انتظار الموافقة'),
        ('approved', 'معتمدة'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغاة'),
        ('archived', 'مؤرشفة'),
        ('received', 'مستلمة'),
        ('registered', 'مسجلة'),
        ('routed', 'موجهة'),
        ('under_review', 'قيد المراجعة'),
        ('in_execution', 'قيد التنفيذ'),
        ('rejected', 'مرفوضة'),
        ('on_hold', 'معلقة')
    ], string='الحالة الجديدة')
    

    field_changes = fields.Text(
        string='تفاصيل التغييرات',
        help='تفاصيل الحقول التي تم تغييرها'
    )
    
    ip_address = fields.Char(
        string='عنوان IP',
        help='عنوان IP للمستخدم عند إجراء التغيير'
    )
    
    user_agent = fields.Char(
        string='معلومات المتصفح',
        help='معلومات المتصفح المستخدم'
    )
    

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='المرفق المرتبط',
        help='المرفق المرتبط بهذا التغيير (إن وجد)'
    )
    
    approval_request_id = fields.Many2one(
        'approval.request',
        string='طلب الموافقة',
        help='طلب الموافقة المرتبط بهذا التغيير (إن وجد)'
    )
    


    display_name = fields.Char(
        string='الاسم المعروض',
        compute='_compute_display_name'
    )
    
    document_name = fields.Char(
        string='اسم الوثيقة',
        related='document_id.name',
        store=True
    )
    
    document_reference = fields.Char(
        string='رقم الوثيقة المرجعي',
        related='document_id.reference_number',
        store=True
    )
    
    user_name = fields.Char(
        string='اسم المستخدم',
        related='user_id.name',
        store=True
    )
    

    @api.depends('action', 'timestamp', 'user_id.name')
    def _compute_display_name(self):
        """حساب الاسم المعروض للسجل"""
        for record in self:
            action_name = dict(record._fields['action'].selection).get(record.action, record.action)
            timestamp_str = record.timestamp.strftime('%Y-%m-%d %H:%M') if record.timestamp else ''
            record.display_name = f"{action_name} - {record.user_id.name} - {timestamp_str}"
    

    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء سجل جديد مع معلومات إضافية"""
        for vals in vals_list:

            request = self.env.context.get('request')
            if request:
                vals.update({
                    'ip_address': request.httprequest.environ.get('REMOTE_ADDR'),
                    'user_agent': request.httprequest.environ.get('HTTP_USER_AGENT'),
                })
        
        return super().create(vals_list)
    
    def unlink(self):
        """منع حذف سجلات التاريخ"""
        raise UserError(_('لا يمكن حذف سجلات التاريخ للحفاظ على سلامة المراجعة'))
    

    @api.model
    def create_history_record(self, document_id, action, description, **kwargs):
        """طريقة مساعدة لإنشاء سجل تاريخ"""
        vals = {
            'document_id': document_id,
            'action': action,
            'description': description,
            'timestamp': fields.Datetime.now(),
            'user_id': self.env.user.id,
        }
        vals.update(kwargs)
        
        return self.create(vals)
    
    @api.model
    def get_document_timeline(self, document_id):
        """الحصول على الخط الزمني للوثيقة"""
        return self.search([
            ('document_id', '=', document_id)
        ], order='timestamp asc')
    
    @api.model
    def get_user_activity(self, user_id, date_from=None, date_to=None):
        """الحصول على نشاط المستخدم"""
        domain = [('user_id', '=', user_id)]
        
        if date_from:
            domain.append(('timestamp', '>=', date_from))
        if date_to:
            domain.append(('timestamp', '<=', date_to))
        
        return self.search(domain, order='timestamp desc')
    
    @api.model
    def get_document_statistics(self, document_id):
        """الحصول على إحصائيات الوثيقة"""
        history_records = self.search([('document_id', '=', document_id)])
        
        stats = {
            'total_changes': len(history_records),
            'unique_users': len(history_records.mapped('user_id')),
            'creation_date': False,
            'last_update': False,
            'state_changes': 0,
            'attachments_added': 0,
        }
        
        if history_records:
            creation_record = history_records.filtered(lambda r: r.action == 'created')
            if creation_record:
                stats['creation_date'] = creation_record[0].timestamp
            
            stats['last_update'] = history_records[0].timestamp
            stats['state_changes'] = len(history_records.filtered(
                lambda r: r.previous_state != r.new_state and r.new_state
            ))
            stats['attachments_added'] = len(history_records.filtered(
                lambda r: r.action == 'attachment_added'
            ))
        
        return stats
    

    def action_view_document(self):
        """عرض الوثيقة المرتبطة"""
        self.ensure_one()
        return {
            'name': _('الوثيقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_user(self):
        """عرض المستخدم المرتبط"""
        self.ensure_one()
        return {
            'name': _('المستخدم'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'target': 'new',
        } 
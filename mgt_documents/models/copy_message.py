# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CopyMessage(models.Model):
    """نموذج للرسائل المعدة مسبقاً لإرسال النسخ"""
    _name = 'document.copy.message'
    _description = 'رسالة النسخة المعدة مسبقاً'
    _order = 'sequence, name'
    _rec_name = 'name'

    name = fields.Char(
        string='اسم الرسالة',
        required=True,
        help='اسم مميز للرسالة'
    )
    
    message = fields.Text(
        string='نص الرسالة',
        required=True,
        help='محتوى الرسالة التي سيتم إرسالها'
    )
    
    sequence = fields.Integer(
        string='الترتيب',
        default=10,
        help='ترتيب عرض الرسالة في القائمة'
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True,
        help='إلغاء تحديد هذا الخيار لإخفاء الرسالة دون حذفها'
    )
    
    usage_count = fields.Integer(
        string='عدد مرات الاستخدام',
        compute='_compute_usage_count',
        search='_search_usage_count',
        help='عدد مرات استخدام هذه الرسالة'
    )
    
    @api.depends()
    def _compute_usage_count(self):
        """حساب عدد مرات استخدام الرسالة"""
        for record in self:
            count = self.env['document.document'].search_count([
                ('copy_message_id', '=', record.id)
            ])
            record.usage_count = count
    
    def _search_usage_count(self, operator, value):
        """دالة بحث مخصصة لحقل usage_count"""

        messages_with_count = []
        for message in self.search([]):
            count = self.env['document.document'].search_count([
                ('copy_message_id', '=', message.id)
            ])
            if operator == '>' and count > value:
                messages_with_count.append(message.id)
            elif operator == '=' and count == value:
                messages_with_count.append(message.id)
            elif operator == '<' and count < value:
                messages_with_count.append(message.id)
            elif operator == '>=' and count >= value:
                messages_with_count.append(message.id)
            elif operator == '<=' and count <= value:
                messages_with_count.append(message.id)
        
        return [('id', 'in', messages_with_count)]
    
    def name_get(self):
        """تخصيص عرض اسم الرسالة"""
        result = []
        for record in self:
            name = record.name
            if record.message:
                preview = record.message[:50] + '...' if len(record.message) > 50 else record.message
                name = f"{record.name} ({preview})"
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """بحث متقدم في اسم ومحتوى الرسالة"""
        args = args or []
        if name:
            domain = ['|', ('name', operator, name), ('message', operator, name)]
            records = self.search(domain + args, limit=limit)
            return [record.id for record in records]
        return super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)

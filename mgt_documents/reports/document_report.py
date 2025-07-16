# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
from datetime import datetime, timedelta


class DocumentReport(models.Model):
    """تقرير تحليلي للوثائق والمخاطبات"""
    
    _name = 'document.report'
    _description = 'تقرير الوثائق'
    _auto = False
    _rec_name = 'document_name'
    _order = 'create_date desc'

    document_id = fields.Many2one('document.document', string='الوثيقة', readonly=True)
    document_name = fields.Char(string='اسم الوثيقة', readonly=True)
    reference_number = fields.Char(string='الرقم المرجعي', readonly=True)
    document_type = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
        ('internal', 'داخلي'),
        ('circular', 'تعميم'),
        ('ebook', 'كتاب إلكتروني'),
        ('memo', 'مذكرة'),
        ('report', 'تقرير')
    ], string='نوع الوثيقة', readonly=True)
    
    category_id = fields.Many2one('document.category', string='الفئة', readonly=True)
    priority = fields.Selection([
        ('0', 'عادي'),
        ('1', 'مهم'),
        ('2', 'عاجل'),
        ('3', 'عاجل جداً')
    ], string='الأولوية', readonly=True)
    
    sender_id = fields.Many2one('res.partner', string='الجهة المرسلة', readonly=True)
    sender_employee_id = fields.Many2one('hr.employee', string='الموظف المرسل', readonly=True)
    recipient_id = fields.Many2one('res.partner', string='الجهة المستقبلة', readonly=True)
    recipient_employee_id = fields.Many2one('hr.employee', string='الموظف المستقبل', readonly=True)
    department_id = fields.Many2one('hr.department', string='القسم', readonly=True)
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('submitted', 'مقدمة'),
        ('in_review', 'قيد المراجعة'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة'),
        ('archived', 'مؤرشفة'),
        ('cancelled', 'ملغاة')
    ], string='الحالة', readonly=True)
    
    approval_status = fields.Selection([
        ('pending', 'في انتظار الموافقة'),
        ('approved', 'موافق عليها'),
        ('rejected', 'مرفوضة'),
        ('cancelled', 'ملغاة')
    ], string='حالة الموافقة', readonly=True)
    
    create_date = fields.Datetime(string='تاريخ الإنشاء', readonly=True)
    date = fields.Datetime(string='تاريخ الوثيقة', readonly=True)
    submitted_date = fields.Datetime(string='تاريخ التقديم', readonly=True)
    approved_date = fields.Datetime(string='تاريخ الاعتماد', readonly=True)
    archived_date = fields.Datetime(string='تاريخ الأرشفة', readonly=True)
    
    days_to_submit = fields.Integer(string='أيام للتقديم', readonly=True)
    days_to_approve = fields.Integer(string='أيام للاعتماد', readonly=True)
    days_to_archive = fields.Integer(string='أيام للأرشفة', readonly=True)
    total_processing_time = fields.Integer(string='إجمالي وقت المعالجة (أيام)', readonly=True)
    
    attachment_count = fields.Integer(string='عدد المرفقات', readonly=True)
    signature_count = fields.Integer(string='عدد التوقيعات', readonly=True)
    approval_count = fields.Integer(string='عدد طلبات الموافقة', readonly=True)
    
    is_signed = fields.Boolean(string='موقعة', readonly=True)
    is_confidential = fields.Boolean(string='سرية', readonly=True)
    
    create_uid = fields.Many2one('res.users', string='منشئ الوثيقة', readonly=True)
    approved_by = fields.Many2one('res.users', string='اعتمدت بواسطة', readonly=True)
    
    year = fields.Char(string='السنة', readonly=True)
    month = fields.Selection([
        ('01', 'يناير'),
        ('02', 'فبراير'),
        ('03', 'مارس'),
        ('04', 'أبريل'),
        ('05', 'مايو'),
        ('06', 'يونيو'),
        ('07', 'يوليو'),
        ('08', 'أغسطس'),
        ('09', 'سبتمبر'),
        ('10', 'أكتوبر'),
        ('11', 'نوفمبر'),
        ('12', 'ديسمبر')
    ], string='الشهر', readonly=True)
    
    quarter = fields.Selection([
        ('Q1', 'الربع الأول'),
        ('Q2', 'الربع الثاني'),
        ('Q3', 'الربع الثالث'),
        ('Q4', 'الربع الرابع')
    ], string='الربع', readonly=True)

    def init(self):
        """إنشاء VIEW للتقرير في قاعدة البيانات"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        query = """
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    dd.id,
                    dd.id as document_id,
                    dd.name as document_name,
                    dd.reference_number,
                    dd.document_type,
                    dd.category_id,
                    dd.priority,
                    dd.sender_id,
                    dd.sender_employee_id,
                    dd.recipient_id,
                    dd.recipient_employee_id,
                    dd.department_id,
                    dd.state,
                    dd.approval_status,
                    dd.create_date,
                    dd.date,
                    dd.submitted_date,
                    dd.approved_date,
                    dd.archived_date,
                    dd.create_uid,
                    dd.approved_by,
                    dd.is_confidential,
                    
                    -- Processing time calculations
                    CASE 
                        WHEN dd.submitted_date IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM (dd.submitted_date - dd.create_date))/86400
                        ELSE NULL 
                    END::INTEGER as days_to_submit,
                    
                    CASE 
                        WHEN dd.approved_date IS NOT NULL AND dd.submitted_date IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM (dd.approved_date - dd.submitted_date))/86400
                        ELSE NULL 
                    END::INTEGER as days_to_approve,
                    
                    CASE 
                        WHEN dd.archived_date IS NOT NULL AND dd.approved_date IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM (dd.archived_date - dd.approved_date))/86400
                        ELSE NULL 
                    END::INTEGER as days_to_archive,
                    
                    CASE 
                        WHEN dd.archived_date IS NOT NULL THEN 
                            EXTRACT(EPOCH FROM (dd.archived_date - dd.create_date))/86400
                        ELSE NULL 
                    END::INTEGER as total_processing_time,
                    
                    -- Counts from related tables
                    COALESCE(att.attachment_count, 0) as attachment_count,
                    COALESCE(sig.signature_count, 0) as signature_count,
                    COALESCE(app.approval_count, 0) as approval_count,
                    
                    -- Boolean fields
                    CASE WHEN sig.signature_count > 0 THEN TRUE ELSE FALSE END as is_signed,
                    
                    -- Date grouping fields
                    EXTRACT(YEAR FROM dd.date)::TEXT as year,
                    LPAD(EXTRACT(MONTH FROM dd.date)::TEXT, 2, '0') as month,
                    
                    CASE 
                        WHEN EXTRACT(MONTH FROM dd.date) <= 3 THEN 'Q1'
                        WHEN EXTRACT(MONTH FROM dd.date) <= 6 THEN 'Q2'
                        WHEN EXTRACT(MONTH FROM dd.date) <= 9 THEN 'Q3'
                        ELSE 'Q4'
                    END as quarter
                    
                FROM document_document dd
                
                -- Attachment count subquery
                LEFT JOIN (
                    SELECT 
                        res_id,
                        COUNT(*) as attachment_count
                    FROM ir_attachment 
                    WHERE res_model = 'document.document' 
                    GROUP BY res_id
                ) att ON att.res_id = dd.id
                
                -- Signature count subquery
                LEFT JOIN (
                    SELECT 
                        ds.document_id,
                        COUNT(*) as signature_count
                    FROM digital_signature ds
                    WHERE ds.is_valid = TRUE
                    GROUP BY ds.document_id
                ) sig ON sig.document_id = dd.id
                
                -- Approval count subquery
                LEFT JOIN (
                    SELECT 
                        ar.document_id,
                        COUNT(*) as approval_count
                    FROM document_approval_request ar
                    GROUP BY ar.document_id
                ) app ON app.document_id = dd.id
            )
        """ % self._table
        
        self.env.cr.execute(query) 
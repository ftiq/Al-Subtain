# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class DocumentStatistics(models.TransientModel):
    """نموذج إحصائيات الوثائق"""
    
    _name = 'document.statistics'
    _description = 'إحصائيات الوثائق'

    date_from = fields.Date(
        string='من تاريخ',
        default=lambda self: fields.Date.today().replace(day=1),
        required=True
    )
    
    date_to = fields.Date(
        string='إلى تاريخ',
        default=fields.Date.today,
        required=True
    )
    
    department_ids = fields.Many2many(
        'hr.department',
        string='الأقسام'
    )
    
    category_ids = fields.Many2many(
        'document.category',
        string='الفئات'
    )
    
    document_types = fields.Selection([
        ('all', 'جميع الأنواع'),
        ('incoming', 'واردة'),
        ('outgoing', 'صادرة'),
        ('internal', 'داخلية'),
        ('ebooks', 'كتب إلكترونية')
    ], string='نوع الوثائق', default='all')
    
    total_documents = fields.Integer(string='إجمالي الوثائق', readonly=True)
    documents_by_type = fields.Html(string='الوثائق حسب النوع', readonly=True)
    documents_by_status = fields.Html(string='الوثائق حسب الحالة', readonly=True)
    documents_by_department = fields.Html(string='الوثائق حسب القسم', readonly=True)
    approval_statistics = fields.Html(string='إحصائيات الموافقات', readonly=True)
    processing_times = fields.Html(string='أوقات المعالجة', readonly=True)

    def action_generate_statistics(self):
        """توليد الإحصائيات"""
        self.ensure_one()
        
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to)
        ]
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        
        if self.category_ids:
            domain.append(('category_id', 'in', self.category_ids.ids))
        
        if self.document_types != 'all':
            if self.document_types == 'ebooks':
                domain.append(('document_type', '=', 'ebook'))
            else:
                domain.append(('document_type', '=', self.document_types))
        
        documents = self.env['document.document'].search(domain)
        
        self._calculate_basic_statistics(documents)
        self._calculate_type_statistics(documents)
        self._calculate_status_statistics(documents)
        self._calculate_department_statistics(documents)
        self._calculate_approval_statistics(documents)
        self._calculate_processing_times(documents)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def _calculate_basic_statistics(self, documents):
        """حساب الإحصائيات الأساسية"""
        self.total_documents = len(documents)

    def _calculate_type_statistics(self, documents):
        """حساب إحصائيات الأنواع"""
        type_stats = {}
        type_labels = dict(documents._fields['document_type'].selection)
        
        for doc in documents:
            doc_type = doc.document_type
            if doc_type not in type_stats:
                type_stats[doc_type] = 0
            type_stats[doc_type] += 1
        
        html = '<table class="table table-striped">'
        html += '<thead><tr><th>نوع الوثيقة</th><th>العدد</th><th>النسبة المئوية</th></tr></thead><tbody>'
        
        total = len(documents)
        for doc_type, count in type_stats.items():
            percentage = (count * 100 / total) if total > 0 else 0
            type_name = type_labels.get(doc_type, doc_type)
            html += f'<tr><td>{type_name}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>'
        
        html += '</tbody></table>'
        self.documents_by_type = html

    def _calculate_status_statistics(self, documents):
        """حساب إحصائيات الحالات"""
        status_stats = {}
        status_labels = dict(documents._fields['state'].selection)
        
        for doc in documents:
            state = doc.state
            if state not in status_stats:
                status_stats[state] = 0
            status_stats[state] += 1
        
        html = '<table class="table table-striped">'
        html += '<thead><tr><th>الحالة</th><th>العدد</th><th>النسبة المئوية</th></tr></thead><tbody>'
        
        total = len(documents)
        for state, count in status_stats.items():
            percentage = (count * 100 / total) if total > 0 else 0
            state_name = status_labels.get(state, state)
            html += f'<tr><td>{state_name}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>'
        
        html += '</tbody></table>'
        self.documents_by_status = html

    def _calculate_department_statistics(self, documents):
        """حساب إحصائيات الأقسام"""
        dept_stats = {}
        
        for doc in documents:
            dept_name = doc.department_id.name if doc.department_id else 'غير محدد'
            if dept_name not in dept_stats:
                dept_stats[dept_name] = 0
            dept_stats[dept_name] += 1
        
        html = '<table class="table table-striped">'
        html += '<thead><tr><th>القسم</th><th>العدد</th><th>النسبة المئوية</th></tr></thead><tbody>'
        
        total = len(documents)
        for dept_name, count in sorted(dept_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count * 100 / total) if total > 0 else 0
            html += f'<tr><td>{dept_name}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>'
        
        html += '</tbody></table>'
        self.documents_by_department = html

    def _calculate_approval_statistics(self, documents):
        """حساب إحصائيات الموافقات"""
        approval_stats = {
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'cancelled': 0
        }
        
        for doc in documents:
            if doc.approval_status in approval_stats:
                approval_stats[doc.approval_status] += 1
        
        approval_labels = dict(documents._fields['approval_status'].selection)
        
        html = '<table class="table table-striped">'
        html += '<thead><tr><th>حالة الموافقة</th><th>العدد</th><th>النسبة المئوية</th></tr></thead><tbody>'
        
        total = len(documents)
        for status, count in approval_stats.items():
            percentage = (count * 100 / total) if total > 0 else 0
            status_name = approval_labels.get(status, status)
            html += f'<tr><td>{status_name}</td><td>{count}</td><td>{percentage:.1f}%</td></tr>'
        
        html += '</tbody></table>'
        self.approval_statistics = html

    def _calculate_processing_times(self, documents):
        """حساب أوقات المعالجة"""
        processing_times = []
        
        for doc in documents:
            if doc.create_date and doc.approved_date:
                days = (doc.approved_date - doc.create_date).days
                processing_times.append(days)
        
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            min_time = min(processing_times)
            max_time = max(processing_times)
            
            html = '<table class="table table-striped">'
            html += '<thead><tr><th>المقياس</th><th>القيمة (أيام)</th></tr></thead><tbody>'
            html += f'<tr><td>متوسط وقت المعالجة</td><td>{avg_time:.1f}</td></tr>'
            html += f'<tr><td>أقل وقت معالجة</td><td>{min_time}</td></tr>'
            html += f'<tr><td>أطول وقت معالجة</td><td>{max_time}</td></tr>'
            html += f'<tr><td>عدد الوثائق المعالجة</td><td>{len(processing_times)}</td></tr>'
            html += '</tbody></table>'
        else:
            html = '<p>لا توجد بيانات كافية لحساب أوقات المعالجة</p>'
        
        self.processing_times = html

    def action_print_report(self):
        """طباعة التقرير"""
        return self.env.ref('mgt_documents.document_statistics_report').report_action(self)

    def action_export_excel(self):
        """تصدير إلى Excel"""

        pass 
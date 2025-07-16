# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class DocumentDashboard(models.TransientModel):
    """نموذج لوحة التحكم للوثائق"""
    
    _name = 'document.dashboard'
    _description = 'لوحة تحكم الوثائق'


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
    

    department_id = fields.Many2one(
        'hr.department',
        string='القسم'
    )
    

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company
    )
    

    total_documents = fields.Integer(
        string='إجمالي الوثائق',
        compute='_compute_statistics'
    )
    
    draft_documents = fields.Integer(
        string='وثائق المسودة',
        compute='_compute_statistics'
    )
    
    submitted_documents = fields.Integer(
        string='وثائق مقدمة',
        compute='_compute_statistics'
    )
    
    approved_documents = fields.Integer(
        string='وثائق معتمدة',
        compute='_compute_statistics'
    )
    
    rejected_documents = fields.Integer(
        string='وثائق مرفوضة',
        compute='_compute_statistics'
    )
    
    archived_documents = fields.Integer(
        string='وثائق مؤرشفة',
        compute='_compute_statistics'
    )
    

    incoming_documents = fields.Integer(
        string='وثائق واردة',
        compute='_compute_type_statistics'
    )
    
    outgoing_documents = fields.Integer(
        string='وثائق صادرة',
        compute='_compute_type_statistics'
    )
    
    internal_documents = fields.Integer(
        string='وثائق داخلية',
        compute='_compute_type_statistics'
    )
    
    ebooks_count = fields.Integer(
        string='كتب إلكترونية',
        compute='_compute_type_statistics'
    )
    

    recent_documents = fields.Integer(
        string='وثائق اليوم',
        compute='_compute_recent_activity'
    )
    
    pending_approvals = fields.Integer(
        string='موافقات معلقة',
        compute='_compute_recent_activity'
    )
    
    overdue_documents = fields.Integer(
        string='وثائق متأخرة',
        compute='_compute_recent_activity'
    )
    

    documents_by_state_chart = fields.Text(
        string='رسم بياني للحالات',
        compute='_compute_chart_data'
    )
    
    documents_by_type_chart = fields.Text(
        string='رسم بياني للأنواع',
        compute='_compute_chart_data'
    )
    
    monthly_trend_chart = fields.Text(
        string='رسم بياني للاتجاه الشهري',
        compute='_compute_chart_data'
    )
    
    @api.depends('date_from', 'date_to', 'department_id', 'company_id')
    def _compute_statistics(self):
        """حساب الإحصائيات الأساسية"""
        for record in self:
            domain = record._get_base_domain()
            
            Document = self.env['document.document']
            
            record.total_documents = Document.search_count(domain)
            record.draft_documents = Document.search_count(domain + [('state', '=', 'draft')])
            record.submitted_documents = Document.search_count(domain + [('state', '=', 'submitted')])
            record.approved_documents = Document.search_count(domain + [('state', '=', 'approved')])
            record.rejected_documents = Document.search_count(domain + [('state', '=', 'rejected')])
            record.archived_documents = Document.search_count(domain + [('state', '=', 'archived')])
    
    @api.depends('date_from', 'date_to', 'department_id', 'company_id')
    def _compute_type_statistics(self):
        """حساب إحصائيات أنواع الوثائق"""
        for record in self:
            domain = record._get_base_domain()
            
            Document = self.env['document.document']
            
            record.incoming_documents = Document.search_count(domain + [('document_type', '=', 'incoming')])
            record.outgoing_documents = Document.search_count(domain + [('document_type', '=', 'outgoing')])
            record.internal_documents = Document.search_count(domain + [('document_type', '=', 'internal')])
            record.ebooks_count = Document.search_count(domain + [('document_type', '=', 'ebook')])
    
    @api.depends('date_from', 'date_to', 'department_id', 'company_id')
    def _compute_recent_activity(self):
        """حساب الأنشطة الحديثة"""
        for record in self:
            base_domain = record._get_base_domain()
            
            Document = self.env['document.document']
            ApprovalRequest = self.env['document.approval.request']
            

            today_domain = base_domain + [
                ('create_date', '>=', fields.Date.today()),
                ('create_date', '<', fields.Date.today() + timedelta(days=1))
            ]
            record.recent_documents = Document.search_count(today_domain)
            

            approval_domain = [('status', '=', 'pending')]
            if record.department_id:
                approval_domain.append(('approver_id.department_id', '=', record.department_id.id))
            if record.company_id:
                approval_domain.append(('company_id', '=', record.company_id.id))
            record.pending_approvals = ApprovalRequest.search_count(approval_domain)
            

            overdue_date = fields.Date.today() - timedelta(days=7)
            overdue_domain = base_domain + [
                ('state', 'in', ['submitted', 'in_review']),
                ('submitted_date', '<', overdue_date)
            ]
            record.overdue_documents = Document.search_count(overdue_domain)
    
    @api.depends('date_from', 'date_to', 'department_id', 'company_id')
    def _compute_chart_data(self):
        """حساب بيانات الرسوم البيانية"""
        for record in self:
            domain = record._get_base_domain()
            Document = self.env['document.document']
            

            states_data = []
            for state, label in Document._fields['state'].selection:
                count = Document.search_count(domain + [('state', '=', state)])
                if count > 0:
                    states_data.append({'label': label, 'value': count})
            record.documents_by_state_chart = str(states_data)
            

            types_data = []
            for doc_type, label in Document._fields['document_type'].selection:
                count = Document.search_count(domain + [('document_type', '=', doc_type)])
                if count > 0:
                    types_data.append({'label': label, 'value': count})
            record.documents_by_type_chart = str(types_data)
            

            monthly_data = []
            for i in range(6):
                start_date = (fields.Date.today().replace(day=1) - timedelta(days=i*30)).replace(day=1)
                end_date = start_date + timedelta(days=31)
                end_date = end_date.replace(day=1) - timedelta(days=1)
                
                month_domain = domain + [
                    ('create_date', '>=', start_date),
                    ('create_date', '<=', end_date)
                ]
                count = Document.search_count(month_domain)
                monthly_data.append({
                    'month': start_date.strftime('%Y-%m'),
                    'value': count
                })
            
            record.monthly_trend_chart = str(monthly_data)
    
    def _get_base_domain(self):
        """الحصول على النطاق الأساسي للبحث"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        return domain
    
    def action_view_documents(self, state=None, doc_type=None):
        """عرض الوثائق مع فلاتر محددة"""
        domain = self._get_base_domain()
        
        if state:
            domain.append(('state', '=', state))
        
        if doc_type:
            domain.append(('document_type', '=', doc_type))
        
        return {
            'name': _('الوثائق'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'tree,kanban,form',
            'domain': domain,
            'context': {'create': False}
        }
    
    def action_view_pending_approvals(self):
        """عرض الموافقات المعلقة"""
        domain = [('status', '=', 'pending')]
        
        if self.department_id:
            domain.append(('approver_id.department_id', '=', self.department_id.id))
        
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))
        
        return {
            'name': _('الموافقات المعلقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.approval.request',
            'view_mode': 'tree,form',
            'domain': domain
        }
    
    def action_refresh_dashboard(self):
        """تحديث لوحة التحكم"""

        self._compute_statistics()
        self._compute_type_statistics()
        self._compute_recent_activity()
        self._compute_chart_data()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم التحديث'),
                'message': _('تم تحديث لوحة التحكم بنجاح'),
                'type': 'success',
            }
        } 
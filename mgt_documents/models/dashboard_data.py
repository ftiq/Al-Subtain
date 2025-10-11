# -*- coding: utf-8 -*-

from odoo import models, api, _


class DashboardData(models.TransientModel):
    _name = 'document.dashboard.data'
    _description = 'Document Dashboard Data'

    @api.model
    def get_dashboard_data(self):
        current_user = self.env.user
        domain = []
        if not current_user.has_group('mgt_documents.group_doc_admin'):
            if current_user.has_group('mgt_documents.group_doc_manager'):
                if current_user.employee_id and current_user.employee_id.department_id:
                    domain = ['|', ('create_uid', '=', current_user.id), 
                             ('department_id', '=', current_user.employee_id.department_id.id)]
                else:
                    domain = [('company_id', '=', current_user.company_id.id)]
            else:
                domain = [('create_uid', '=', current_user.id)]
        
        documents = self.env['document.document'].search(domain)
        
        # Only users with approval permissions should query approval.request to avoid ACL errors
        can_read_approvals = (
            current_user.has_group('mgt_documents.group_doc_contributor') or
            current_user.has_group('mgt_documents.group_doc_approver') or
            current_user.has_group('mgt_documents.group_doc_manager') or
            current_user.has_group('mgt_documents.group_doc_admin')
        )
        pending_approvals = self.env['approval.request'].browse([])
        if can_read_approvals:
            approval_domain = [('request_status', 'in', ['new', 'pending', 'under_approval'])]
            if not current_user.has_group('mgt_documents.group_doc_admin'):
                approval_domain.append(('approver_ids.user_id', '=', current_user.id))
            pending_approvals = self.env['approval.request'].search(approval_domain)
        

        statistics = {
            'total_documents': len(documents),
            'outgoing_total': len(documents.filtered(lambda d: d.document_type == 'outgoing')),
            'internal_total': len(documents.filtered(lambda d: d.document_type == 'internal')),
            'report_total': len(documents.filtered(lambda d: d.document_type == 'report')),
            'memo_total': len(documents.filtered(lambda d: d.document_type == 'memo')),
            'circular_total': len(documents.filtered(lambda d: d.document_type == 'circular')),
            'letter_total': len(documents.filtered(lambda d: d.document_type == 'letter')),
            'contract_total': len(documents.filtered(lambda d: d.document_type == 'contract')),
            'invoice_total': len(documents.filtered(lambda d: d.document_type == 'invoice')),
            'other_total': len(documents.filtered(lambda d: d.document_type == 'other')),
            'incoming_total': len(documents.filtered(lambda d: d.document_type == 'incoming')),
            'archived_total': len(documents.filtered(lambda d: d.processing_state == 'archived')),
            'draft_documents': len(documents.filtered(lambda d: d.processing_state == 'received')),
            'submitted_documents': len(documents.filtered(lambda d: d.processing_state in ('routed', 'under_review', 'registered'))),
            'approved_documents': len(documents.filtered(lambda d: d.processing_state == 'approved')),
            'pending_approvals': len(pending_approvals)
        }
        
        recent_documents = documents.sorted('create_date', reverse=True)[:10]
        recent_docs_data = []
        for doc in recent_documents:
            recent_docs_data.append({
                'id': doc.id,
                'name': doc.name,
                'reference_number': doc.reference_number,
                'date': doc.date.strftime('%Y-%m-%d') if doc.date else '',
                'processing_state': doc.processing_state,
                'document_type': doc.document_type
            })
        
        approval_data = []
        for approval in pending_approvals:
            approval_data.append({
                'id': approval.id,
                'name': approval.name,
                'request_date': approval.date_start.strftime('%Y-%m-%d') if approval.date_start else '',
                'due_date': approval.expected_response_date.strftime('%Y-%m-%d') if getattr(approval, 'expected_response_date', False) else '',
                'document_id': approval.document_id.id if hasattr(approval, 'document_id') and approval.document_id else False,
                'status': approval.request_status
            })
        
        company = self.env.company
        company_info = {
            'id': company.id,
            'name': company.name,
            'logo': bool(company.logo),
            'street': company.street or '',
            'phone': company.phone or '',
            'email': company.email or ''
        }
        
        return {
            'stats': statistics,
            'recent_documents': recent_docs_data,
            'pending_approvals': approval_data,
            'company_info': company_info
        }

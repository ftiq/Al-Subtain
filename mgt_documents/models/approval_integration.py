# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة المرتبطة',
        ondelete='cascade',
        help='الوثيقة الحكومية المرتبطة بطلب الموافقة',
        index=True
    )
    
    urgency_level = fields.Selection([
        ('normal', 'عادي'),
        ('urgent', 'عاجل'),
        ('very_urgent', 'عاجل جداً'),
        ('critical', 'حرج - فوري')
    ], string='مستوى العجلة', default='normal', tracking=True)
    
    confidentiality_level = fields.Selection([
        ('public', 'عام'),
        ('internal', 'داخلي'),
        ('confidential', 'سري'),
        ('top_secret', 'سري للغاية')
    ], string='مستوى السرية', default='internal', tracking=True)
    
    department_id = fields.Many2one(
        'hr.department',
        string='القسم المختص',
        tracking=True,
        default=lambda self: self.env.user.employee_id.department_id.id if self.env.user.employee_id else False
    )
    
    approval_type_detailed = fields.Selection([
        ('content_review', 'مراجعة المحتوى'),
        ('legal_review', 'مراجعة قانونية'),
        ('financial_approval', 'موافقة مالية'),
        ('publication_approval', 'موافقة النشر'),
        ('archiving_approval', 'موافقة الأرشفة'),
        ('access_permission', 'إذن الوصول'),
        ('signature_authority', 'صلاحية التوقيع'),
        ('security_clearance', 'تصريح أمني')
    ], string='نوع الموافقة التفصيلي', tracking=True)
    
    expected_response_date = fields.Datetime(
        string='تاريخ الرد المتوقع',
        help='التاريخ المتوقع للحصول على الموافقة'
    )
    
    auto_escalation = fields.Boolean(
        string='التصعيد التلقائي',
        default=True,
        help='تفعيل التصعيد التلقائي عند التأخير'
    )
    
    escalation_period = fields.Integer(
        string='فترة التصعيد (ساعات)',
        default=24,
        help='عدد الساعات قبل التصعيد التلقائي'
    )
    
    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_is_overdue',
        help='هل تجاوز طلب الموافقة الوقت المحدد'
    )
    
    days_since_request = fields.Integer(
        string='أيام منذ الطلب',
        compute='_compute_days_since_request'
    )
    
    approval_chain_progress = fields.Float(
        string='تقدم سلسلة الموافقة (%)',
        compute='_compute_approval_chain_progress',
        help='نسبة اكتمال سلسلة الموافقات'
    )
    
    next_approver_info = fields.Char(
        string='الموافق التالي',
        compute='_compute_next_approver_info',
        help='معلومات الموافق التالي في السلسلة'
    )
    
    document_id = fields.Many2one(
        'document.document',
        string='الوثيقة المرتبطة',
        help='الوثيقة التي يتم طلب الموافقة عليها'
    )
    
    related_documents = fields.Many2many(
        'document.document',
        'approval_document_rel',
        'approval_id',
        'document_id',
        string='الوثائق ذات الصلة',
        help='وثائق إضافية مرتبطة بهذه الموافقة'
    )
    
    ai_recommended_approvers = fields.Text(
        string='الموافقين المقترحين  ',
        help='قائمة بالموافقين المقترحين بناءً'
    )
    
    risk_assessment = fields.Selection([
        ('low', 'مخاطر منخفضة'),
        ('medium', 'مخاطر متوسطة'),
        ('high', 'مخاطر عالية'),
        ('critical', 'مخاطر حرجة')
    ], string='تقييم المخاطر', compute='_compute_risk_assessment', store=True)
    
    complexity_score = fields.Float(
        string='درجة التعقيد',
        compute='_compute_complexity_score',
        store=True,
        help='درجة تعقيد الموافقة من 1-10'
    )
    
    @api.depends('urgency_level', 'create_date')
    def _compute_expected_response_date(self):
        for record in self:
            if not record.create_date:
                record.expected_response_date = False
                continue
                
            hours_mapping = {
                'normal': 72, 'urgent': 24, 'very_urgent': 8, 'critical': 2
            }
            hours = hours_mapping.get(record.urgency_level, 72)
            record.expected_response_date = record.create_date + timedelta(hours=hours)
    
    @api.depends('expected_response_date')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_overdue = (
                record.expected_response_date and 
                record.expected_response_date < now and
                record.request_status in ['new', 'pending', 'under_approval']
            )
    
    @api.depends('create_date')
    def _compute_days_since_request(self):
        today = fields.Datetime.now()
        for record in self:
            if record.create_date:
                record.days_since_request = (today - record.create_date).days
            else:
                record.days_since_request = 0
    
    @api.depends('approver_ids.status')
    def _compute_approval_chain_progress(self):
        """حساب تقدم سلسلة الموافقة"""
        for record in self:
            if not record.approver_ids:
                record.approval_chain_progress = 0.0
                continue
                
            total_approvers = len(record.approver_ids)
            approved_count = len(record.approver_ids.filtered(
                lambda a: a.status == 'approved'
            ))
            
            record.approval_chain_progress = (approved_count / total_approvers) * 100 if total_approvers > 0 else 0.0
    
    @api.depends('approver_ids.status', 'approver_sequence')
    def _compute_next_approver_info(self):
        """تحديد معلومات الموافق التالي"""
        for record in self:
            if not record.approver_sequence:
                pending_approvers = record.approver_ids.filtered(
                    lambda a: a.status == 'pending'
                )
                if pending_approvers:
                    names = pending_approvers.mapped('user_id.name')
                    record.next_approver_info = f"في انتظار: {', '.join(names[:3])}"
                    if len(names) > 3:
                        record.next_approver_info += f" و {len(names) - 3} آخرين"
                else:
                    record.next_approver_info = "تمت الموافقة"
            else:
                next_approver = record.approver_ids.filtered(
                    lambda a: a.status == 'pending'
                ).sorted('sequence')[:1]
                
                if next_approver:
                    record.next_approver_info = f"الموافق التالي: {next_approver.user_id.name}"
                else:
                    record.next_approver_info = "اكتملت الموافقات"
    
    @api.depends('digital_signatures')
    def _compute_signature_count(self):
        """حساب عدد التوقيعات الرقمية"""
        for record in self:
            record.signature_count = len(record.digital_signatures.filtered('is_valid'))
    
    @api.depends('urgency_level', 'confidentiality_level', 'approval_type_detailed')
    def _compute_risk_assessment(self):
        """تقييم المخاطر باستخدام خوارزمية ذكية"""
        for record in self:
            risk_score = 0
            
            urgency_risk = {
                'normal': 1,
                'urgent': 2,
                'very_urgent': 3,
                'critical': 4
            }.get(record.urgency_level, 1)
            
            confidentiality_risk = {
                'public': 1,
                'internal': 2,
                'confidential': 3,
                'top_secret': 4
            }.get(record.confidentiality_level, 1)
            
            type_risk = {
                'content_review': 1,
                'legal_review': 3,
                'financial_approval': 3,
                'publication_approval': 2,
                'archiving_approval': 1,
                'access_permission': 2,
                'signature_authority': 4,
                'security_clearance': 4
            }.get(record.approval_type_detailed, 2)
            
            risk_score = (urgency_risk + confidentiality_risk + type_risk) / 3
            
            if risk_score <= 1.5:
                record.risk_assessment = 'low'
            elif risk_score <= 2.5:
                record.risk_assessment = 'medium'
            elif risk_score <= 3.5:
                record.risk_assessment = 'high'
            else:
                record.risk_assessment = 'critical'
    
    @api.depends('approver_ids', 'urgency_level', 'confidentiality_level')
    def _compute_complexity_score(self):
        """حساب درجة تعقيد الموافقة"""
        for record in self:
            complexity = 0
            
            complexity += len(record.approver_ids) * 0.5
            
            urgency_complexity = {
                'normal': 1,
                'urgent': 2,
                'very_urgent': 3,
                'critical': 4
            }.get(record.urgency_level, 1)
            complexity += urgency_complexity
            
            confidentiality_complexity = {
                'public': 1,
                'internal': 2,
                'confidential': 3,
                'top_secret': 4
            }.get(record.confidentiality_level, 1)
            complexity += confidentiality_complexity
            
            record.complexity_score = min(max(complexity, 1), 10)
    
    @api.onchange('document_id')
    def _onchange_document_id(self):
        """تحديث تلقائي عند اختيار وثيقة"""
        if not self.document_id:
            return
            
        doc = self.document_id
        

        self.urgency_level = getattr(doc, 'urgency_level', 'normal')
        self.confidentiality_level = getattr(doc, 'confidentiality_level', 'internal')
        self.department_id = doc.department_id
        

        self.approval_type_detailed = self._suggest_approval_type(doc)
        

        suggested_approver = doc._get_approver()
        if suggested_approver and not self.approver_ids.filtered(lambda a: a.user_id == suggested_approver):
            self.approver_ids = [(0, 0, {
                'user_id': suggested_approver.id,
                'status': 'new',
                'sequence': 1
            })]
            

        if (self.env.context.get('transfer_document_attachments') and 
            hasattr(self, 'id') and self.id):
            doc._transfer_attachments_to_approval(self)
    
    def _suggest_approval_type(self, document):
        """اقتراح نوع الموافقة بناءً على نوع الوثيقة"""
        if not document.document_type_id:
            return 'content_review'
            
        doc_type = document.document_type_id.name.lower()
        type_mapping = {
            'عقد': 'legal_review',
            'اتفاقية': 'legal_review',
            'فاتورة': 'financial_approval',
            'مالي': 'financial_approval',
            'تعميم': 'publication_approval',
            'نشر': 'publication_approval',
            'تقرير': 'content_review',
            'مذكرة': 'content_review'
        }
        
        for keyword, approval_type in type_mapping.items():
            if keyword in doc_type:
                return approval_type
                
        return 'content_review'
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء طلب موافقة مع نقل المرفقات"""
        requests = super().create(vals_list)
        
        for request in requests:

            if request.document_id and request.document_id.attachment_ids:
                request.document_id._transfer_attachments_to_approval(request)
                
        return requests
    
    @api.onchange('urgency_level')
    def _onchange_urgency_level(self):
        """تحديث فترة التصعيد بناءً على مستوى العجلة"""
        escalation_periods = {
            'normal': 72,      
            'urgent': 24,      
            'very_urgent': 8,  
            'critical': 2      
        }
        self.escalation_period = escalation_periods.get(self.urgency_level, 24)
    
    def action_smart_assign_approvers(self):
        """تعيين ذكي للموافقين بناءً على نوع الوثيقة والقسم"""
        for record in self:
            if not record.document_id:
                continue
                
            suggested_approvers = []
            
            if record.department_id and record.department_id.manager_id:
                suggested_approvers.append(record.department_id.manager_id.user_id)
            
            doc_type = record.document_id.document_type
            if doc_type in ['contract', 'financial']:
                finance_dept = self.env['hr.department'].search([
                    ('name', 'ilike', 'مالي')
                ], limit=1)
                if finance_dept and finance_dept.manager_id:
                    suggested_approvers.append(finance_dept.manager_id.user_id)
            
            if record.approval_type_detailed == 'legal_review':
                legal_dept = self.env['hr.department'].search([
                    ('name', 'ilike', 'قانوني')
                ], limit=1)
                if legal_dept and legal_dept.manager_id:
                    suggested_approvers.append(legal_dept.manager_id.user_id)
            
            unique_approvers = list(set(suggested_approvers))
            
            if not record.approver_ids.filtered(lambda a: a.status != 'new'):
                record.approver_ids.unlink()
            
            sequence = 10
            for approver in unique_approvers:
                if approver:
                    self.env['approval.approver'].create({
                        'request_id': record.id,
                        'user_id': approver.id,
                        'sequence': sequence,
                        'status': 'new'
                    })
                    sequence += 10
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('تم تعيين الموافقين بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_escalate_approval(self):
        """تصعيد طلب الموافقة للمستوى الأعلى"""
        for record in self:
            current_approvers = record.approver_ids.filtered(
                lambda a: a.status == 'pending'
            )
            
            for approver in current_approvers:
                if approver.user_id.employee_id and approver.user_id.employee_id.parent_id:
                    manager = approver.user_id.employee_id.parent_id.user_id
                    
                    self.env['approval.approver'].create({
                        'request_id': record.id,
                        'user_id': manager.id,
                        'sequence': approver.sequence + 5,
                        'status': 'new'
                    })
                    
                    record.message_post(
                        body=f"تم تصعيد الموافقة إلى {manager.name}",
                        message_type='notification',
                        subtype_xmlid='mail.mt_note'
                    )
    
    def action_view_document(self):
        """عرض الوثيقة المرتبطة"""
        if not self.document_id:
            raise UserError(_('لا توجد وثيقة مرتبطة بهذا الطلب'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('الوثيقة المرتبطة'),
            'res_model': 'document.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_create_digital_signature(self):
        """إنشاء توقيع رقمي للموافقة"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('إنشاء توقيع رقمي'),
            'res_model': 'digital.signature',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approval_request_id': self.id,
                'default_document_id': self.document_id.id if self.document_id else False,
                'default_name': f'توقيع - {self.name}',
            }
        }
    
    @api.model
    def _ai_suggest_approvers(self, document_type, department, urgency):
        """اقتراح موافقين   """

        suggestions = []
        
        if document_type in ['contract', 'financial']:
            suggestions.append('مدير القسم المالي')
        
        if urgency in ['very_urgent', 'critical']:
            suggestions.append('المدير العام')
        
        return suggestions
    
    def _analyze_approval_patterns(self):
        """تحليل أنماط الموافقة للتحسين المستقبلي"""

        domain = [
            ('document_id.document_type', '=', self.document_id.document_type if self.document_id else False),
            ('request_status', '=', 'approved'),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=90))
        ]
        
        similar_approvals = self.search(domain, limit=50)
        
        avg_approval_time = 0
        if similar_approvals:
            total_time = sum([
                (approval.date_confirmed - approval.create_date).total_seconds() 
                for approval in similar_approvals 
                if approval.date_confirmed
            ])
            avg_approval_time = total_time / len(similar_approvals) / 3600  # بالساعات
        
        return {
            'average_approval_time_hours': avg_approval_time,
            'similar_approvals_count': len(similar_approvals),
            'success_rate': len(similar_approvals) / max(len(similar_approvals) + 1, 1) * 100
        }
    
    @api.constrains('urgency_level', 'expected_response_date')
    def _check_urgency_consistency(self):
        """التحقق من تناسق مستوى العجلة مع تاريخ الرد المتوقع"""
        for record in self:
            if record.urgency_level == 'critical' and record.expected_response_date:
                time_diff = record.expected_response_date - record.create_date
                if time_diff.total_seconds() > 7200:  
                    raise ValidationError(_(

                    ))
    
    @api.constrains('escalation_period')
    def _check_escalation_period(self):
        """التحقق من صحة فترة التصعيد"""
        for record in self:
            if record.escalation_period and record.escalation_period < 1:
                raise ValidationError(_('فترة التصعيد يجب أن تكون ساعة واحدة على الأقل'))
    
    @api.model
    def _cron_auto_escalate_overdue_approvals(self):
        """مهمة مجدولة للتصعيد التلقائي للموافقات المتأخرة"""
        overdue_approvals = self.search([
            ('request_status', '=', 'pending'),
            ('auto_escalation', '=', True),
            ('is_overdue', '=', True)
        ])
        
        for approval in overdue_approvals:
            try:
                approval.action_escalate_approval()
                approval.message_post(
                    body="تم التصعيد التلقائي بسبب تجاوز الوقت المحدد",
                    message_type='notification'
                )
            except Exception as e:
                continue
    
    @api.model
    def _cron_send_approval_reminders(self):
        """إرسال تذكيرات للموافقين"""
        pending_approvals = self.search([
            ('request_status', '=', 'pending'),
            ('create_date', '<=', fields.Datetime.now() - timedelta(hours=12))
        ])
        
        for approval in pending_approvals:
            pending_approvers = approval.approver_ids.filtered(
                lambda a: a.status == 'pending'
            )
            
            for approver in pending_approvers:
                template = self.env.ref(
                    'mgt_documents.email_template_approval_reminder',
                    raise_if_not_found=False
                )
                if template:
                    template.send_mail(approval.id, force_send=True)

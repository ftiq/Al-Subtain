# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class DocumentDocument(models.Model):
    _name = 'document.document'
    _description = 'الوثائق والمخاطبات'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    

    name = fields.Text(
        string='عنوان الوثيقة',
        required=True,
        tracking=True
    )
    
    reference_number = fields.Char(
        string='الرقم المرجعي',
        required=True,
        copy=False,
        default=lambda self: _('جديد'),
        tracking=True
    )
    
    display_name = fields.Char(
        string='الاسم المعروض',
        compute='_compute_display_name',
        store=True
    )
    
    date = fields.Datetime(
        string='تاريخ الوثيقة',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    

    document_direction = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'),
        ('internal', 'داخلي')
    ], string='اتجاه الوثيقة', compute='_compute_document_direction', store=True, tracking=True)

    document_type = fields.Selection([
        ('incoming', 'وارد'),
        ('outgoing', 'صادر'), 
        ('internal', 'داخلي'),
        ('circular', 'تعميم'),
        ('memo', 'مذكرة'),
        ('request', 'طلب'),
        ('report', 'تقرير'),
        ('letter', 'رسالة'),
        ('contract', 'عقد'),
        ('invoice', 'فاتورة'),
        ('other', 'أخرى'),
    ], string='نوع الوثيقة', default='incoming', tracking=True)
    
    routing_priority = fields.Selection([
        ('routine', 'اعتيادي'),
        ('urgent', 'عاجل'),
        ('very_urgent', 'عاجل جداً'),
        ('confidential', 'سري')
    ], string='أولوية التوجيه', default='routine', tracking=True, help='أولوية معالجة الوثيقة')
    
    processing_state = fields.Selection([
        ('received', 'مستلمة'),
        ('registered', 'مسجلة'),
        ('routed', 'موجهة'),
        ('under_review', 'قيد المراجعة'),
        ('approved', 'معتمدة'),
        ('in_execution', 'قيد التنفيذ'),
        ('completed', 'مكتملة'),
        ('on_hold', 'معلقة'),
        ('rejected', 'مرفوضة'),
        ('archived', 'مؤرشفة')
    ], string='حالة المعالجة', default='received', tracking=True, help='حالة معالجة الوثيقة الحالية')
    
    document_type_id = fields.Many2one(
        'document.category',
        string='فئة الوثيقة',
        tracking=True,
        help='الفئة التفصيلية للوثيقة'
    )
    
    

    # workflow_id removed - workflow disabled
    
    # current_step removed - workflow disabled
    
    received_date = fields.Datetime(
        string='تاريخ الاستلام',
        default=fields.Datetime.now,
        tracking=True,
        help='تاريخ استلام الوثيقة في النظام'
    )
    
    target_completion_date = fields.Datetime(
        string='الموعد المستهدف للإنجاز',
        tracking=True,
        help='التاريخ المتوقع لإنجاز معالجة الوثيقة'
    )
    
    actual_completion_date = fields.Datetime(
        string='تاريخ الإنجاز الفعلي',
        tracking=True,
        help='التاريخ الفعلي لإنجاز معالجة الوثيقة'
    )
    
    handling_instructions = fields.Text(
        string='تعليمات المعالجة',
        help='تعليمات خاصة لمعالجة هذه الوثيقة'
    )
    
    escalation_notes = fields.Text(
        string='ملاحظات التصعيد',
        help='ملاحظات حول تصعيد الوثيقة'
    )
    
    is_overdue = fields.Boolean(
        string='متأخر',
        compute='_compute_overdue_status',
        store=True,
        help='هل تجاوزت الوثيقة الموعد المستهدف'
    )
    
    processing_duration = fields.Float(
        string='مدة المعالجة (ساعات)',
        compute='_compute_processing_duration',
        store=True,
        help='المدة الفعلية لمعالجة الوثيقة'
    )
    
    current_version_id = fields.Many2one(
        'document.version',
        string='الإصدار الحالي'
    )
    

    task_ids = fields.One2many(
        'admin.task',
        'request_document_id',
        string='المهام المرتبطة'
    )
    
    active_tasks_count = fields.Integer(
        string='عدد المهام النشطة',
        compute='_compute_tasks_count'
    )
    
    approval_requests = fields.One2many(
        'approval.request',
        'document_id',
        string='طلبات الموافقة'
    )
    
    approval_count = fields.Integer(
        string='عدد طلبات الموافقة',
        compute='_compute_approval_count'
    )
    
    history_ids = fields.One2many(
        'document.history',
        'document_id',
        string='سجل التغييرات'
    )
    
    version_count = fields.Integer(
        string='عدد الإصدارات',
        compute='_compute_version_count'
    )
    history_count = fields.Integer(
        string='عدد سجل التغييرات',
        compute='_compute_history_count'
    )
    related_documents_count = fields.Integer(
        string='عدد الوثائق المرتبطة',
        compute='_compute_related_documents_count'
    )
    
    needs_approval = fields.Boolean(
        string='يحتاج موافقة',
        compute='_compute_needs_approval',
        store=True
    )
    
    has_pending_approvals = fields.Boolean(
        string='طلبات موافقة معلقة',
        compute='_compute_has_pending_approvals',
        store=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='معتمد من'
    )
    
    approved_date = fields.Datetime(
        string='تاريخ الاعتماد'
    )
    
    rejection_reason = fields.Text(
        string='سبب الرفض'
    )
    
    is_archived = fields.Boolean(
        string='مؤرشف',
        compute='_compute_is_archived'
    )
    
    archived_by = fields.Many2one(
        'res.users',
        string='مؤرشف من'
    )
    
    archived_date = fields.Datetime(
        string='تاريخ الأرشفة'
    )
    
    archive_location = fields.Char(
        string='موقع الأرشيف'
    )
    
    

    subject = fields.Char(
        string='الموضوع',
        required=True,
        tracking=True
    )
    
    summary = fields.Text(
        string='الملخص',
        tracking=True
    )
    
    content = fields.Html(
        string='محتوى الوثيقة'
    )
    

    @api.depends('document_type')
    def _compute_document_direction(self):
        for rec in self:
            mapping = {
                'incoming': 'incoming',
                'outgoing': 'outgoing',
                'internal': 'internal',
                'circular': 'internal',
                'memo': 'internal',
                'report': 'internal',
                'request': 'internal',
                'letter': 'outgoing',
                'contract': 'outgoing',
                'invoice': 'outgoing',
                'other': 'internal',
            }
            rec.document_direction = mapping.get(rec.document_type or 'incoming', 'incoming')


    @api.depends('task_ids.state')
    def _compute_tasks_count(self):
        """حساب عدد المهام النشطة - مُحسن للأداء"""
        
        if not self:
            return
            
        task_data = self.env['admin.task'].read_group(
            domain=[('request_document_id', 'in', self.ids)],
            fields=['request_document_id', 'state'],
            groupby=['request_document_id', 'state'],
            lazy=False
        )
        
        document_tasks = {doc.id: 0 for doc in self}
        
        active_states = ['draft', 'assigned', 'in_progress', 'pending_review']
        for data in task_data:
            doc_id = data['request_document_id'][0]
            state = data['state']
            count = data['__count']
            
            if state in active_states:
                document_tasks[doc_id] += count
        
        for doc in self:
            doc.active_tasks_count = document_tasks.get(doc.id, 0)
    
    @api.depends('target_completion_date', 'actual_completion_date', 'processing_state')
    def _compute_overdue_status(self):
        """حساب حالة التأخير"""
        now = fields.Datetime.now()
        for doc in self:
            if (doc.target_completion_date and 
                doc.target_completion_date < now and 
                doc.processing_state not in ['completed', 'archived', 'rejected']):
                doc.is_overdue = True
            else:
                doc.is_overdue = False
    
    @api.depends('received_date', 'actual_completion_date')
    def _compute_processing_duration(self):
        """حساب مدة المعالجة الفعلية"""
        for doc in self:
            if doc.received_date and doc.actual_completion_date:
                delta = doc.actual_completion_date - doc.received_date
                doc.processing_duration = delta.total_seconds() / 3600  
            else:
                doc.processing_duration = 0.0

    def action_start_review(self):
        """بدء مراجعة الوثيقة"""
        for doc in self:
            if doc.processing_state not in ['routed']:
                raise UserError(_('يمكن بدء مراجعة الوثائق الموجهة فقط'))
            _logger.info(f"[DOC][start_review][start] user=%s doc_id=%s ref=%s ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state)
            doc.write({
                'processing_state': 'under_review'
            })
            doc._create_review_task()
            doc._create_history_record('بدء مراجعة الوثيقة', 'تم بدء عملية مراجعة الوثيقة', 'routed', 'under_review')
            _logger.info(f"[DOC][start_review][done] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المراجع/المعنيين بالمراجعة وجدولة نشاط مراجعة
            try:
                body = _(f"تم بدء مراجعة الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='start_review', body=body, schedule_activity=True, activity_deadline_days=2)
            except Exception:
                pass
            
    def action_complete(self):
        """إكمال معالجة الوثيقة - مُحسن بtransaction atomicity"""
        for doc in self:
            pending_tasks = self.env['admin.task'].search([
                ('request_document_id', '=', doc.id),
                ('state', 'not in', ['completed', 'cancelled'])
            ])
            
            if pending_tasks:
                _logger.warning(f"[DOC][complete][blocked] doc_id=%s pending_tasks=%s",
                                doc.id, len(pending_tasks))
                raise UserError(_('يجب إنجاز جميع المهام أولاً'))
            
            with doc.env.cr.savepoint():
                doc.write({
                    'processing_state': 'completed',
                    'actual_completion_date': fields.Datetime.now()
                })
                _logger.info(f"[DOC][complete][done] doc_id=%s ps=%s",
                             doc.id, doc.processing_state)
                
    def action_register(self):
        """تسجيل الوثيقة في النظام"""
        for doc in self:
            if doc.processing_state != 'received':
                raise UserError(_('يمكن تسجيل الوثائق المستلمة فقط'))
            _logger.info(f"[DOC][register][start] user=%s doc_id=%s ref=%s ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state)
            doc.write({
                'processing_state': 'registered'
            })
            
            doc._create_history_record('تسجيل الوثيقة', 'تم تسجيل الوثيقة في النظام', 'received', 'registered')
            _logger.info(f"[DOC][register][done] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المعنيين بالتسجيل
            try:
                body = _(f"تم تسجيل الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='register', body=body, schedule_activity=False)
            except Exception:
                pass
    
    def action_route(self):
        """توجيه الوثيقة للقسم المناسب (مبسط - بدون محرك التوجيه)"""
        for doc in self:
            if doc.processing_state not in ['registered', 'received']:
                raise UserError(_('يمكن توجيه الوثائق المسجلة فقط'))
            _logger.info(f"[DOC][route][start] user=%s doc_id=%s ref=%s ps=%s dept=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state,
                         doc.department_id.display_name if doc.department_id else None)
            
            doc.write({
                'processing_state': 'routed',
            })
            
            doc._create_history_record('توجيه الوثيقة', 'تم توجيه الوثيقة للقسم المناسب', 'registered', 'routed')
            _logger.info(f"[DOC][route][after_write] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المعنيين بالتوجيه وجدولة نشاط للمستلم/مدير القسم
            try:
                body = _(f"تم توجيه الوثيقة رقم {doc.reference_number} إلى القسم/المستلم المحدد.")
                doc._notify_stakeholders(event='route', body=body, schedule_activity=True, activity_deadline_days=2)
            except Exception:
                pass
    
    def action_approve(self):
        """اعتماد الوثيقة"""
        for doc in self:
            if doc.processing_state != 'under_review':
                raise UserError(_('يمكن اعتماد الوثائق قيد المراجعة فقط'))
            _logger.info(f"[DOC][approve][start] user=%s doc_id=%s ref=%s ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state)
            doc.write({
                'processing_state': 'approved',
                'approved_date': fields.Datetime.now(),
                'approved_by': doc.env.user.id,
            })
            
            doc._create_execution_tasks()
            
            doc._create_history_record('اعتماد الوثيقة', 'تم اعتماد الوثيقة والموافقة عليها', 'under_review', 'approved')
            _logger.info(f"[DOC][approve][done] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المعنيين وإرسال بريد اعتماد
            try:
                body = _(f"تم اعتماد الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='approve', body=body, schedule_activity=True, activity_deadline_days=3)
            except Exception:
                pass
            try:
                tmpl = doc.env.ref('mgt_documents.email_template_document_approved', raise_if_not_found=False)
                if tmpl:
                    tmpl.send_mail(doc.id, force_send=True)
            except Exception:
                pass
            # إقفال طلبات الموافقة المعلقة لهذه الوثيقة
            try:
                pending = doc.approval_requests.filtered(lambda r: r.request_status in ['new', 'pending', 'under_approval'])
                if pending:
                    pending.write({'request_status': 'approved', 'date_confirmed': fields.Datetime.now()})
            except Exception:
                pass
    
    def action_start_execution_processing(self):
        """بدء تنفيذ معالجة الوثيقة"""
        for doc in self:
            if doc.processing_state != 'approved':
                raise UserError(_('يمكن بدء تنفيذ الوثائق المعتمدة فقط'))
            _logger.info(f"[DOC][start_execution_processing][start] user=%s doc_id=%s ref=%s ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state)
            doc.write({
                'processing_state': 'in_execution'
            })
            
            doc._create_history_record('بدء تنفيذ الوثيقة', 'تم بدء تنفيذ متطلبات الوثيقة', 'approved', 'in_execution')
            _logger.info(f"[DOC][start_execution_processing][done] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المعنيين ببدء التنفيذ
            try:
                body = _(f"تم بدء تنفيذ متطلبات الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='start_execution', body=body, schedule_activity=False)
            except Exception:
                pass
    
    def action_reject(self):
        """رفض الوثيقة"""
        for doc in self:
            old_state = doc.processing_state
            doc.write({
                'processing_state': 'rejected'
            })
            
            active_tasks = doc.task_ids.filtered(
                lambda t: t.state not in ['completed', 'cancelled']
            )
            active_tasks.write({'state': 'cancelled'})
            
            doc._create_history_record('رفض الوثيقة', 'تم رفض الوثيقة وإلغاء معالجتها', old_state, 'rejected')
            _logger.info(f"[DOC][reject] user=%s doc_id=%s ref=%s old_ps=%s new_ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, old_state, doc.processing_state)
            # إشعار المعنيين وإرسال بريد رفض
            try:
                body = _(f"تم رفض الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='reject', body=body, schedule_activity=False)
            except Exception:
                pass
            try:
                tmpl = doc.env.ref('mgt_documents.email_template_document_rejected', raise_if_not_found=False)
                if tmpl:
                    tmpl.send_mail(doc.id, force_send=True)
            except Exception:
                pass
            # تحديث طلبات الموافقة المعلقة إلى مرفوضة
            try:
                pending = doc.approval_requests.filtered(lambda r: r.request_status in ['new', 'pending', 'under_approval'])
                if pending:
                    pending.write({'request_status': 'rejected'})
            except Exception:
                pass
    
    def action_archive(self):
        """أرشفة الوثيقة"""
        for doc in self:
            if doc.processing_state != 'completed':
                raise UserError(_('يمكن أرشفة الوثائق المكتملة فقط'))
            _logger.info(f"[DOC][archive][start] user=%s doc_id=%s ref=%s ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, doc.processing_state)
            doc.write({
                'processing_state': 'archived',
                'archived_date': fields.Datetime.now(),
                'archived_by': doc.env.user.id,
            })
            
            doc._create_history_record('أرشفة الوثيقة', 'تم أرشفة الوثيقة في النظام', 'completed', 'archived')
            _logger.info(f"[DOC][archive][done] doc_id=%s ps=%s",
                         doc.id, doc.processing_state)
            # إشعار المعنيين وإرسال بريد أرشفة
            try:
                body = _(f"تم أرشفة الوثيقة رقم {doc.reference_number}.")
                doc._notify_stakeholders(event='archive', body=body, schedule_activity=False)
            except Exception:
                pass
            try:
                tmpl = doc.env.ref('mgt_documents.email_template_document_archived', raise_if_not_found=False)
                if tmpl:
                    tmpl.send_mail(doc.id, force_send=True)
            except Exception:
                pass
    
    def action_hold(self):
        """تعليق معالجة الوثيقة"""
        for doc in self:
            old_state = doc.processing_state
            doc.write({
                'processing_state': 'on_hold'
            })
            
            doc._create_history_record('تعليق المعالجة', 'تم تعليق معالجة الوثيقة مؤقتاً', old_state, 'on_hold')
            _logger.info(f"[DOC][hold] user=%s doc_id=%s ref=%s old_ps=%s new_ps=%s",
                         doc.env.user.login, doc.id, doc.reference_number, old_state, doc.processing_state)
    

        
    def _create_execution_tasks(self):
        """إنشاء مهام تنفيذية بعد الاعتماد"""
        self.ensure_one()
        
        task_data = {
            'name': f'تنفيذ الوثيقة: {self.name}',
            'description': f'تنفيذ متطلبات الوثيقة رقم {self.reference_number}',
            'task_type': 'execute_action',
            'request_document_id': self.id,
            'priority': '2',
            'state': 'assigned'
        }
        
        if self.target_completion_date:
            task_data['due_date'] = self.target_completion_date
        else:
            task_data['due_date'] = fields.Datetime.now() + timedelta(days=5)
        
        executor = self._get_default_executor()
        if executor:
            task_data['assigned_employee_id'] = executor.id
            task_data['assigned_department_id'] = executor.department_id.id
        
        task = self.env['admin.task'].create(task_data)
        return task
                
    # وظائف سير العمل معطلة - تم إزالتها
        
    def _create_review_task(self):
        """إنشاء مهمة مراجعة"""
        self.ensure_one()
        
        reviewer = self._get_default_reviewer()
        
        if reviewer:
            task_data = {
                'name': f'مراجعة الوثيقة: {self.name}',
                'description': f'مراجعة وتقييم الوثيقة رقم {self.reference_number}',
                'task_type': 'review_document',
                'request_document_id': self.id,
                'assigned_employee_id': reviewer.id,
                'priority': '1',
                'due_date': fields.Datetime.now() + timedelta(days=2),
                'state': 'assigned'
            }
            
            if reviewer.department_id:
                task_data['assigned_department_id'] = reviewer.department_id.id
            
            task = self.env['admin.task'].create(task_data)
            
            try:
                if hasattr(task, 'action_assign'):
                    task.action_assign()
            except Exception as e:
                _logger.warning(f'فشل في تعيين مهمة المراجعة: {str(e)}')
            
            return task
        else:
            
            task_data = {
                'name': f'مراجعة الوثيقة: {self.name}',
                'description': f'مراجعة وتقييم الوثيقة رقم {self.reference_number} - يحتاج تعيين مراجع',
                'task_type': 'review_document',
                'request_document_id': self.id,
                'priority': '1',
                'due_date': fields.Datetime.now() + timedelta(days=2),
                'state': 'draft'
            }
            
            if self.department_id:
                task_data['assigned_department_id'] = self.department_id.id
            
            task = self.env['admin.task'].create(task_data)
            _logger.info(f'تم إنشاء مهمة مراجعة بدون مراجع محدد للوثيقة {self.reference_number}')
            return task
            
    def _get_default_reviewer(self):
        """الحصول على مراجع افتراضي"""
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
            
        current_user = self.env.user
        if current_user.employee_id:
            employee = current_user.employee_id
            if employee.parent_id:
                return employee.parent_id
            
            if employee.department_id and employee.department_id.manager_id:
                return employee.department_id.manager_id
                
        approvers_group = self.env.ref('mgt_documents.group_doc_approver', raise_if_not_found=False)
        if approvers_group and approvers_group.users:
            for user in approvers_group.users:
                if user.employee_id:
                    return user.employee_id
                
        return False

    def _get_stakeholder_partners(self):
        """تجميع المعنيين لإشعارهم كمتابعين وإرسال إشعار لهم"""
        self.ensure_one()
        partner_ids = set()
        try:
            if self.sender_employee_id and self.sender_employee_id.user_id and self.sender_employee_id.user_id.partner_id:
                partner_ids.add(self.sender_employee_id.user_id.partner_id.id)
        except Exception:
            pass
        try:
            if self.recipient_employee_id and self.recipient_employee_id.user_id and self.recipient_employee_id.user_id.partner_id:
                partner_ids.add(self.recipient_employee_id.user_id.partner_id.id)
        except Exception:
            pass
        try:
            if self.department_id and self.department_id.manager_id and self.department_id.manager_id.user_id and self.department_id.manager_id.user_id.partner_id:
                partner_ids.add(self.department_id.manager_id.user_id.partner_id.id)
        except Exception:
            pass
        try:
            if self.create_uid and self.create_uid.partner_id:
                partner_ids.add(self.create_uid.partner_id.id)
        except Exception:
            pass
        # ضم المراجع الافتراضي إن وُجد (قد لا يكون له user)
        try:
            reviewer = self._get_default_reviewer()
            if reviewer and reviewer.user_id and reviewer.user_id.partner_id:
                partner_ids.add(reviewer.user_id.partner_id.id)
        except Exception:
            pass
        return list(partner_ids)

    def _notify_stakeholders(self, event='update', body=None, schedule_activity=False, activity_deadline_days=2):
        """إشعار المتابعين وإضافة متابعين عند الحاجة، مع خيار جدولة نشاط"""
        self.ensure_one()
        partners = self._get_stakeholder_partners()
        if partners:
            try:
                self.message_subscribe(partner_ids=partners)
            except Exception:
                pass
        default_bodies = {
            'register': _('تم تسجيل الوثيقة.'),
            'route': _('تم توجيه الوثيقة.'),
            'start_review': _('تم بدء مراجعة الوثيقة.'),
            'approve': _('تم اعتماد الوثيقة.'),
            'start_execution': _('تم بدء التنفيذ.'),
            'reject': _('تم رفض الوثيقة.'),
            'archive': _('تم أرشفة الوثيقة.'),
        }
        msg = body or default_bodies.get(event, _('تحديث على الوثيقة.'))
        try:
            self.message_post(body=msg, message_type='notification', partner_ids=partners, subtype_xmlid='mail.mt_comment')
        except Exception:
            pass

        if schedule_activity:
            try:
                act_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                if act_type:
                    # اختيار مستخدم للنشاط: المستقبل أو مدير القسم أو المنشئ
                    user = None
                    if self.recipient_employee_id and self.recipient_employee_id.user_id:
                        user = self.recipient_employee_id.user_id
                    elif self.department_id and self.department_id.manager_id and self.department_id.manager_id.user_id:
                        user = self.department_id.manager_id.user_id
                    elif self.create_uid:
                        user = self.create_uid
                    if user:
                        deadline = fields.Date.today() + timedelta(days=activity_deadline_days or 2)
                        self.activity_schedule(activity_type_id=act_type.id, summary=msg, user_id=user.id, date_deadline=deadline)
            except Exception:
                pass
        
    def action_resume_from_hold(self):
        """استئناف وثيقة كانت في حالة التعليق إلى أقرب حالة سابقة حسب السجل."""
        for doc in self:
            if doc.processing_state != 'on_hold':
                raise UserError(_('هذه الوثيقة ليست في حالة تعليق'))
            # ابحث عن آخر حالة معالجة قبل on_hold
            last = doc.env['document.history'].search([
                ('document_id', '=', doc.id),
                ('new_state', '!=', 'on_hold'),
                ('new_state', '!=', False),
            ], order='timestamp desc', limit=1)
            target_processing = last.new_state if last and last.new_state in dict(doc._fields['processing_state'].selection) else 'under_review'
            old_ps = doc.processing_state
            doc.write({
                'processing_state': target_processing,
            })
            doc._create_history_record('restored', _('تم استئناف المعالجة بعد التعليق'), old_ps, target_processing)
            _logger.info(f"[DOC][resume_from_hold] doc_id=%s ps:%s->%s", doc.id, old_ps, target_processing)

    def _cleanup_runtime_links(self):
        """تنظيف الروابط وقت الرجوع لمسودة: إلغاء المهام غير المنتهية"""
        for doc in self:
            active_tasks = doc.task_ids.filtered(lambda t: t.state not in ['completed', 'cancelled'])
            if active_tasks:
                active_tasks.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """إرجاع الوثيقة إلى مسودة من أي حالة (مرفوض/ملغي/معلق/أخرى)"""
        for doc in self:
            old_ps = doc.processing_state
            doc._cleanup_runtime_links()
            doc.write({
                'processing_state': 'received',
                'approved_by': False,
                'approved_date': False,
                'rejection_reason': False,
            })
            doc._create_history_record('reset', _('تمت إعادة الوثيقة إلى مسودة'), old_ps, 'received')
            _logger.info(f"[DOC][reset_to_draft] doc_id=%s ps:%s->received", doc.id, old_ps)

    def action_uncancel(self):
        """إلغاء الإلغاء/الرفض وإرجاع الوثيقة لمسودة"""
        for doc in self:
            if doc.processing_state != 'rejected':
                raise UserError(_('الوثيقة ليست ملغاة أو مرفوضة'))
            doc.action_reset_to_draft()

    def action_spawn_current_step_tasks(self):
        """إنشاء مهام للخطوة الحالية في سير العمل لهذه الوثيقة (معطل - لم يعد هناك سير عمل)."""
        self.ensure_one()
        raise UserError(_('وظيفة سير العمل تم تعطيلها في النظام'))
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _get_default_executor(self):
        """الحصول على منفذ افتراضي"""

        if self.department_id:
            department_employees = self.env['hr.employee'].search([
                ('department_id', '=', self.department_id.id),
                ('active', '=', True)
            ], limit=1)
            
            if department_employees:
                return department_employees[0]
                
        return False
    
    category_id = fields.Many2one(
        'document.category',
        string='الفئة',
        required=True,
        tracking=True,
        default=lambda self: self._get_default_category()
    )
    
    priority = fields.Selection([
        ('0', 'عادي'),
        ('1', 'مهم'),
        ('2', 'عاجل'),
        ('3', 'عاجل جداً')
    ], string='الأولوية', default='0', tracking=True)
    
    urgency_level = fields.Selection([
        ('low', 'منخفض'),
        ('medium', 'متوسط'), 
        ('high', 'عالي'),
        ('critical', 'حرج')
    ], string='مستوى الاستعجال', compute='_compute_urgency_level', store=True)
    

    sender_id = fields.Many2one(
        'res.partner',
        string='الجهة المرسلة',
        tracking=True,
        default=lambda self: self._get_default_sender_partner(),
        help='تُحدد تلقائياً بناءً على قسم المستخدم الحالي'
    )
    
    sender_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المرسل',
        tracking=True,
        default=lambda self: self._get_default_sender_employee(),
        readonly=True,
        help='يُحدد تلقائياً بناءً على المستخدم المسجل للدخول'
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string='الجهة المستقبلة',
        tracking=True
    )
    
    recipient_employee_id = fields.Many2one(
        'hr.employee',
        string='الموظف المستقبل',
        tracking=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='القسم المعني',
        tracking=True
    )
    

    submitted_date = fields.Datetime(
        string='تاريخ التقديم',
        readonly=True,
        copy=False
    )
    
    reviewed_date = fields.Datetime(
        string='تاريخ المراجعة',
        readonly=True,
        copy=False
    )
    

    auto_archive_date = fields.Date(
        string='تاريخ الأرشفة التلقائية',
        compute='_compute_auto_archive_date',
        store=True
    )
    
    retention_period = fields.Integer(
        string='فترة الاحتفاظ (بالأيام)',
        default=365,
        help='عدد الأيام للاحتفاظ بالوثيقة قبل الأرشفة التلقائية'
    )
    

    keywords = fields.Many2many(
        'document.keyword',
        string='الكلمات المفتاحية'
    )
    
    confidentiality_level = fields.Selection([
        ('public', 'عام'),
        ('internal', 'داخلي'),
        ('confidential', 'سري'),
        ('top_secret', 'سري للغاية')
    ], string='مستوى السرية', default='internal', tracking=True)
    
    related_documents = fields.Many2many(
        'document.document',
        'document_related_rel',
        'document1_id',
        'document2_id',
        string='الوثائق ذات الصلة'
    )
    
    notes = fields.Text(
        string='ملاحظات داخلية'
    )
    

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        default=lambda self: self.env.company
    )

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        """تحديد نوع الوثيقة بناءً على document_type_id"""
        if self.document_type_id:
            doc_type_name = self.document_type_id.name.lower()
            if 'وارد' in doc_type_name:
                self.document_type = 'incoming'
            elif 'صادر' in doc_type_name:
                self.document_type = 'outgoing'
            elif 'داخلي' in doc_type_name:
                self.document_type = 'internal'
            elif 'تقرير' in doc_type_name:
                self.document_type = 'report'
            elif 'مذكرة' in doc_type_name:
                self.document_type = 'memo'
            elif 'تعميم' in doc_type_name:
                self.document_type = 'circular'
            else:
                self.document_type = 'incoming'
    
    @api.onchange('document_type')
    def _onchange_document_type(self):
        """تحديد نوع الوثيقة والفئة بناءً على نوع الوثيقة المحدد"""
        if self.document_type:
            # Search category by code instead of relying on XML IDs that may not exist
            code_map = {
                'incoming': 'INCOMING',
                'outgoing': 'OUTGOING',
                'internal': 'INTERNAL',
                'circular': 'CIRCULAR',
                'memo': 'MEMO',
                'report': 'REPORT',
            }
            cat_code = code_map.get(self.document_type)
            if cat_code:
                category = self.env['document.category'].search([('code', '=', cat_code)], limit=1)
                if category and getattr(category, 'is_active', True):
                    self.document_type_id = category.id
                    self.category_id = category.parent_id.id if category.parent_id else category.id

            # إن كانت الوثيقة واردة اجعل الجهة المرسلة فارغة ليدخلها المستخدم يدوياً
            if self.document_type == 'incoming':
                self.sender_id = False
                # لا حاجة لموظف مرسل في الوارد
                self.sender_employee_id = False

            if self.category_id:

                cat = self.category_id
                if cat and cat.default_priority:
                    priority_map = {
                        'low': '0',
                        'normal': '1',
                        'high': '2',
                        'urgent': '3',
                    }
                    self.priority = priority_map.get(cat.default_priority, self.priority)

    def _doc_type_from_category(self, category):
        """اشتقاق document_type من فئة الوثيقة (category.code/name)."""
        try:
            code = (category.code or '').upper()
        except Exception:
            code = ''
        mapping = {
            'INCOMING': 'incoming',
            'OUTGOING': 'outgoing',
            'INTERNAL': 'internal',
            'CIRCULAR': 'circular',
            'MEMO': 'memo',
            'REPORT': 'report',
            'CONTRACT': 'contract',
            'INVOICE': 'invoice',
        }
        if code in mapping:
            return mapping[code]
        # Fallback by name keywords
        name = (getattr(category, 'name', '') or '').lower()
        if 'وارد' in name:
            return 'incoming'
        if 'صادر' in name:
            return 'outgoing'
        if 'داخل' in name:
            return 'internal'
        if 'تعميم' in name:
            return 'circular'
        if 'مذكرة' in name:
            return 'memo'
        if 'تقرير' in name:
            return 'report'
        if 'عقد' in name:
            return 'contract'
        if 'فاتورة' in name:
            return 'invoice'
        return 'other'

    @api.onchange('category_id')
    def _onchange_category_id_set_document_type(self):
        """اجعل category_id هو مرجع الحقيقة: يحدد document_type تلقائياً."""
        for rec in self:
            if rec.category_id:
                try:
                    rec.document_type = rec._doc_type_from_category(rec.category_id)
                except Exception:
                    pass

    def _generate_reference_number(self, vals):
        """توليد الرقم المرجعي بصيغة الدليل: INC/OFL/0001/2025 ونحوها."""
        doc_type = vals.get('document_type', 'incoming')
        category_id = vals.get('document_type_id') or vals.get('category_id')

        direction_prefix_map = {
            'incoming': 'INC',
            'outgoing': 'OUT',
            'internal': 'INT',
            'circular': 'CIR',
            'memo': 'MEM',
            'report': 'RPT',
            'request': 'REQ',
            'letter': 'LET',
            'contract': 'CNT',
            'invoice': 'INV',
            'other': 'DOC'
        }
        secondary_type_map = {
            'incoming': 'OFL',   # افتراض رسائل رسمية للوارد إذا لم تتوفر فئة
            'outgoing': 'OFL',   # افتراض رسائل رسمية للصادر إذا لم تتوفر فئة
            'internal': 'MEM',   # افتراض مذكرة للداخلي عند غياب كود الفئة
            'memo': 'MEM',
            'report': 'RPT',
            'circular': 'CIR',
            'letter': 'LET',
            'contract': 'CNT',
            'invoice': 'INV',
        }

        direction = direction_prefix_map.get(doc_type, 'DOC')
        second = None
        if category_id:
            category = self.env['document.category'].browse(category_id)
            if category and category.code:
                second = category.code
        if not second:
            second = secondary_type_map.get(doc_type, 'DOC')

        seq_str = self.env['ir.sequence'].next_by_code('document.reference') or 'DOC/0001/%s' % fields.Date.today().year
        parts = (seq_str or '').split('/')
        number = '0001'
        year = str(fields.Date.today().year)
        if len(parts) >= 3:
            number = parts[1] or number
            year = parts[2] or year

        return f"{direction}/{second}/{number}/{year}"
    
    @api.depends('name', 'reference_number')
    def _compute_display_name(self):
        """حساب الاسم المعروض للوثيقة"""
        for record in self:
            if record.reference_number and record.reference_number != _('جديد'):
                record.display_name = f"[{record.reference_number}] {record.name}"
            else:
                record.display_name = record.name or _('وثيقة جديدة')
    
    @api.depends('approval_requests')
    def _compute_approval_count(self):
        """حساب عدد طلبات الموافقة"""
        for record in self:
            record.approval_count = len(record.approval_requests)
    
    @api.depends('approval_requests.request_status')
    def _compute_has_pending_approvals(self):
        """تحديد وجود طلبات موافقة معلقة - مُحسن للأداء"""
        if not self:
            return
            
        approval_data = self.env['approval.request'].read_group(
            domain=[
                ('document_id', 'in', self.ids),
                ('request_status', 'in', ['new', 'pending', 'under_approval'])
            ],
            fields=['document_id'],
            groupby=['document_id'],
            lazy=False
        )
        
        docs_with_pending = {data['document_id'][0] for data in approval_data}
        
        for record in self:
            record.has_pending_approvals = record.id in docs_with_pending
    
    @api.depends('history_ids')
    def _compute_history_count(self):
        """حساب عدد التغييرات في السجل"""
        for record in self:
            record.history_count = len(record.history_ids)
    
    @api.depends('current_version_id')
    def _compute_version_count(self):
        """حساب عدد الإصدارات"""
        for record in self:
            version_count = self.env['document.version'].search_count([
                ('document_id', '=', record.id)
            ])
            record.version_count = version_count
    
    @api.depends('related_documents')
    def _compute_related_documents_count(self):
        """حساب عدد الوثائق المرتبطة"""
        for record in self:
            record.related_documents_count = len(record.related_documents)
    
    @api.depends('date', 'approved_date', 'retention_period', 'category_id', 'category_id.auto_archive_enabled', 'category_id.auto_archive_days', 'category_id.archive_condition')
    def _compute_auto_archive_date(self):
        """حساب تاريخ الأرشفة التلقائية مع مراعاة إعدادات الفئة.

        الأولوية:
        - إذا كانت الفئة مفعلة للأرشفة التلقائية:
          - after_days: الاعتماد على (approved_date أو date) + auto_archive_days
          - after_approval: الاعتماد على approved_date فقط
          - manual: لا تاريخ تلقائي
        - خلاف ذلك: fallback إلى retention_period على مستوى الوثيقة
        """
        for record in self:
            category = record.category_id
            if category and category.auto_archive_enabled:
                base_date = record.approved_date or record.date
                if category.archive_condition == 'after_days' and base_date and category.auto_archive_days:
                    record.auto_archive_date = (base_date + timedelta(days=category.auto_archive_days)).date()
                elif category.archive_condition == 'after_approval' and record.approved_date and category.auto_archive_days:
                    record.auto_archive_date = (record.approved_date + timedelta(days=category.auto_archive_days)).date()
                else:
                    record.auto_archive_date = False
            else:
                if record.date and record.retention_period:
                    record.auto_archive_date = (record.date + timedelta(days=record.retention_period)).date()
                else:
                    record.auto_archive_date = False
    
    @api.depends('document_type', 'category_id.requires_approval')
    def _compute_needs_approval(self):
        """تحديد ما إذا كانت الوثيقة تحتاج موافقة"""
        for record in self:
            needs_by_type = record.document_type in ['outgoing', 'circular', 'memo', 'report']
            needs_by_category = bool(record.category_id and record.category_id.requires_approval)
            record.needs_approval = needs_by_type or needs_by_category
    
    @api.depends('processing_state')
    def _compute_is_archived(self):
        """تحديد ما إذا كانت الوثيقة مؤرشفة"""
        for record in self:
            record.is_archived = (
                (record.processing_state == 'archived')
            )

    @api.depends('priority', 'processing_state', 'date')
    def _compute_urgency_level(self):
        """حساب مستوى الاستعجال بناءً على الأولوية والحالة والتاريخ"""
        for record in self:
            urgency = 'low'  
            

            if record.priority == '3': 
                urgency = 'critical'
            elif record.priority == '2': 
                urgency = 'high'
            elif record.priority == '1': 
                urgency = 'medium'
            
            if record.processing_state in ['under_review', 'routed'] and urgency != 'critical':
                urgency = 'medium' if urgency == 'low' else 'high'
            
            if record.date:
                days_old = (fields.Datetime.now() - record.date).days
                if days_old > 7 and urgency in ['low', 'medium']:
                    urgency = 'medium' if urgency == 'low' else 'high'
            
            record.urgency_level = urgency

    def write(self, vals):
        """تحديث الوثيقة مع تسجيل التغييرات"""
        # If category changes, sync document_type accordingly before validations
        if 'category_id' in vals and vals.get('category_id'):
            try:
                cat = self.env['document.category'].browse(vals['category_id'])
                if cat:
                    vals.setdefault('document_type', self._doc_type_from_category(cat))
            except Exception:
                pass
        if 'category_id' in vals or 'document_type' in vals:
            for rec in self:
                new_category_id = vals.get('category_id', rec.category_id.id)
                new_type = vals.get('document_type', rec.document_type)
                if new_category_id:
                    cat = self.env['document.category'].browse(new_category_id)
                    allowed = cat.get_allowed_document_types() if cat else []
                    if allowed and new_type not in allowed:
                        raise ValidationError(_('نوع الوثيقة "%s" غير مسموح في الفئة "%s"') % (new_type, cat.display_name))
        tracked_fields = {
            'processing_state': 'حالة المعالجة',
            'name': 'العنوان',
            'subject': 'الموضوع',
            'category_id': 'الفئة',
            'priority': 'الأولوية'
        }
        
        changes = []
        for field, field_name in tracked_fields.items():
            if field in vals:
                try:
                    for record in self:
                        old_value = getattr(record, field)
                        new_value = vals[field]
                        if old_value != new_value:
                            if (hasattr(record._fields[field], 'comodel_name') and 
                                record._fields[field].comodel_name and 
                                record._fields[field].comodel_name in self.env):
                                
                                comodel_name = record._fields[field].comodel_name
                                
                                if old_value:
                                    try:
                                        old_record = self.env[comodel_name].browse(old_value)
                                        old_display = old_record.display_name if old_record.exists() else str(old_value)
                                    except Exception:
                                        old_display = str(old_value)
                                else:
                                    old_display = _('غير محدد')
                                
                                if new_value:
                                    try:
                                        new_record = self.env[comodel_name].browse(new_value)
                                        new_display = new_record.display_name if new_record.exists() else str(new_value)
                                    except Exception:
                                        new_display = str(new_value)
                                else:
                                    new_display = _('غير محدد')
                                
                                changes.append(f"{field_name}: {old_display} ← {new_display}")

                            elif hasattr(record._fields[field], 'selection'):
                                old_display = dict(record._fields[field].selection).get(old_value, old_value)
                                new_display = dict(record._fields[field].selection).get(new_value, new_value)
                                changes.append(f"{field_name}: {old_display} ← {new_display}")
                            else:
                                changes.append(f"{field_name}: {old_value} ← {new_value}")
                except Exception as e:
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Error tracking field {field}: {str(e)}")
                    continue
        
        result = super().write(vals)
        

        if changes:
            try:
                for record in self:
                    record._create_history_record('updated', '; '.join(changes))
            except Exception as e:
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Error creating history record: {str(e)}")
        
        return result
    
    def unlink(self):
        """حذف الوثيقة مع التحقق من الصلاحيات"""
        for record in self:
            if record.processing_state not in ('received', 'rejected'):
                raise UserError(_('لا يمكن حذف الوثيقة إلا في حالة المسودة أو الملغاة'))
            

            record._create_history_record('deleted', _('تم حذف الوثيقة'))
        
        return super().unlink()
    
    
    def _get_default_category(self):
        """الحصول على الفئة الافتراضية"""
        default_category = self.env.ref('mgt_documents.category_administrative', raise_if_not_found=False)
        if default_category and default_category.is_active:
            return default_category.id
        default_category = self.env['document.category'].search([
            ('is_active', '=', True)
        ], limit=1)
        return default_category.id if default_category else False
    
    def copy(self, default=None):
        """عند إنشاء نسخة مطابقة، تُعاد كمسودة مع إعادة تهيئة الحقول الحساسة"""
        self.ensure_one()
        default = dict(default or {})
        default.update({
            'processing_state': 'received',
            'approved_by': False,
            'approved_date': False,
            'archived_by': False,
            'archived_date': False,
            'rejection_reason': False,
            'task_ids': False,
            'history_ids': False,
        })
        # سيُعاد تعيين reference_number تلقائياً لأنه copy=False
        return super(DocumentDocument, self).copy(default)
    
    def _create_history_record(self, action, description, old_state=None, new_state=None):
        """إنشاء سجل في تاريخ الوثيقة"""

        action_mapping = {
            'تسجيل الوثيقة': 'created',
            'توجيه الوثيقة': 'submitted',
            'بدء مراجعة الوثيقة': 'reviewed',
            'اعتماد الوثيقة': 'approved',
            'رفض الوثيقة': 'rejected',
            'أرشفة الوثيقة': 'archived',
            'تعليق المعالجة': 'other',
            'بدء تنفيذ الوثيقة': 'other',
            'إكمال معالجة الوثيقة': 'completed',
            'تفعيل تلقائي لسير العمل': 'other',
            'auto_triggered': 'other',
            'updated': 'updated',
            'deleted': 'deleted',
            'submitted': 'submitted',
            'approved': 'approved',
            'rejected': 'rejected',
            'archived': 'archived',
            'completed': 'completed',
            'created': 'created'
        }
        
        mapped_action = action_mapping.get(action, 'other')
        
        try:
            self.env['document.history'].create({
                'document_id': self.id,
                'action': action_mapping.get(action, action),
                'description': description,
                'timestamp': fields.Datetime.now(),
                'previous_state': old_state,
                'new_state': new_state or self.processing_state if hasattr(self, 'processing_state') else False,
            })
        except Exception as e:
            
            _logger.warning(f'فشل في إنشاء سجل التاريخ للوثيقة {self.id}: {str(e)}')
    

    def action_submit(self):
        """تقديم الوثيقة للمراجعة - تفويض للطريقة الموحدة"""
        for record in self:
            record.action_submit_for_processing()
        return None
    
    
    def _create_approval_request(self):
        """إنشاء طلب موافقة للوثيقة"""

        approver = self._get_approver()
        
        if approver:
            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
            if category:
                self.env['approval.request'].create({
                    'name': f'طلب موافقة على الوثيقة: {self.name}',
                    'category_id': category.id,
                    'request_owner_id': self.env.user.id,
                    'date_start': fields.Datetime.now(),
                    'reason': f'طلب موافقة على الوثيقة رقم: {self.reference_number or self.name}',
                    'document_id': self.id,
                })
                # The document is now in approval process via processing_state
                pass
    
    def _get_approver(self):
        """تحديد الموافق المناسب"""
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
        
        group = self.env.ref('mgt_documents.group_doc_manager', raise_if_not_found=False)
        if group and group.users:
            return group.users[0]
        
        return False
    
    def _get_approval_category(self):
        """تحديد فئة الموافقة بناءً على نوع الوثيقة"""
        category_mapping = {
            'incoming': 'INCOMING_DOCS',
            'outgoing': 'OUTGOING_DOCS', 
            'internal': 'INTERNAL_DOCS',
            'memo': 'MEMO_APPROVAL',
            'circular': 'CIRCULAR_APPROVAL',
            'report': 'REPORT_APPROVAL',
            'contract': 'CONTRACT_APPROVAL'
        }
        
        doc_type = getattr(self, 'document_type', 'incoming')
        category_name = category_mapping.get(doc_type, 'GENERAL')
        
        category = self.env['approval.category'].search([('name', '=', category_name)], limit=1)
        if not category:
            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
        
        return category
    
    def _map_processing_to_workflow_state(self, p_state):
        """تحويل حالة المعالجة إلى حالة سير العمل الأقرب (متوقف - الوظيفة غير مستخدمة)"""
        # This function is no longer used since workflow_state has been removed
        return None
    
    @api.onchange('sender_id', 'sender_employee_id')
    def _compute_sender_info(self):
        """تحديد الجهة المرسلة والموظف المرسل تلقائياً"""
        for record in self:
            current_user = self.env.user
            
            if current_user.employee_id:
                record.sender_employee_id = current_user.employee_id.id
                
                if current_user.employee_id.department_id:
                    department_partner = self.env['res.partner'].search([
                        ('name', 'ilike', current_user.employee_id.department_id.name)
                    ], limit=1)
                    
                    if department_partner:
                        record.sender_id = department_partner.id
                    elif current_user.employee_id.work_contact_id:
                        record.sender_id = current_user.employee_id.work_contact_id.id
                    else:
                        record.sender_id = current_user.partner_id.id
                else:
                    record.sender_id = current_user.partner_id.id
            else:
                record.sender_employee_id = False
                record.sender_id = current_user.partner_id.id
    

    def action_view_approvals(self):
        """عرض طلبات الموافقة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلبات الموافقة'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
            'target': 'current',
        }

    def action_view_tasks(self):
        """عرض المهام المرتبطة بالوثيقة"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('المهام المرتبطة'),
            'res_model': 'admin.task',
            'view_mode': 'list,form,kanban',
            'domain': [('request_document_id', '=', self.id)],
            'context': {'default_request_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_history(self):
        """عرض سجل التغييرات"""
        return {
            'name': _('سجل التغييرات'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.history',
            'view_mode': 'list,form',
            'domain': [('document_id', 'in', self.ids)],
            'context': {'default_document_id': self.id if len(self) == 1 else False}
        }
    
    def action_view_versions(self):
        """عرض إصدارات الوثيقة"""
        self.ensure_one()
        return {
            'name': _('إصدارات الوثيقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.version',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {
                'default_document_id': self.id,
                'search_default_document_id': self.id
            }
        }
    

    
    @api.constrains('date')
    def _check_date(self):
        """التحقق من صحة التاريخ"""
        for record in self:
            if record.date and record.date > fields.Datetime.now():
                raise ValidationError(_('لا يمكن أن يكون تاريخ الوثيقة في المستقبل'))
    
    @api.constrains('retention_period')
    def _check_retention_period(self):
        """التحقق من فترة الاحتفاظ"""
        for record in self:
            if record.retention_period and record.retention_period < 1:
                raise ValidationError(_('يجب أن تكون فترة الاحتفاظ أكبر من صفر'))
        
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء وثيقة جديدة مع توليد رقم مرجعي وتفعيل تلقائي مبسط"""
        for vals in vals_list:
            # Ensure document_type follows category_id if provided
            try:
                cat_id = vals.get('category_id') or vals.get('document_type_id')
                if cat_id and 'document_type' not in vals:
                    cat = self.env['document.category'].browse(cat_id)
                    vals['document_type'] = self._doc_type_from_category(cat) if cat else vals.get('document_type', 'incoming')
            except Exception:
                pass
            # رقم مرجعي
            if not vals.get('reference_number') or vals.get('reference_number') == _('جديد'):
                vals['reference_number'] = self._generate_reference_number(vals)

            # أولوية افتراضية من الفئة إن لزم
            cat_id = vals.get('category_id') or vals.get('document_type_id')
            if cat_id and 'priority' not in vals:
                cat = self.env['document.category'].browse(cat_id)
                if cat and getattr(cat, 'default_priority', False):
                    pmap = {'low': '0', 'normal': '1', 'high': '2', 'urgent': '3'}
                    if pmap.get(cat.default_priority) is not None:
                        vals['priority'] = pmap.get(cat.default_priority)

            # تحقق من توافق النوع مع الفئة عند التحديد
            if vals.get('category_id'):
                cat = self.env['document.category'].browse(vals['category_id'])
                allowed = cat.get_allowed_document_types() if cat else []
                if allowed:
                    current_type = vals.get('document_type', 'incoming')
                    if current_type not in allowed:
                        raise ValidationError(_('نوع الوثيقة "%s" غير مسموح في الفئة "%s"') % (current_type, cat.display_name))

        records = super().create(vals_list)

        return records

    
    def action_request_approval(self):
        """طلب موافقة موحد"""
        self.ensure_one()
        
        category = self._get_approval_category()
        suggested_approver = self._get_approver()
        urgency_mapping = {'0': 'normal', '1': 'urgent', '2': 'very_urgent', '3': 'critical'}

        
        return {
            'name': _('طلب موافقة'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_name': f'موافقة على الوثيقة: {self.name}',
                'default_category_id': category.id if category else False,
                'default_request_owner_id': self.env.user.id,
                'default_urgency_level': urgency_mapping.get(self.priority, 'normal'),
                'default_confidentiality_level': getattr(self, 'confidentiality_level', 'internal'),
                'default_department_id': self.department_id.id if self.department_id else False,
                'default_reason': f'طلب موافقة على الوثيقة رقم: {self.reference_number}',
                'transfer_document_attachments': True,
                'suggested_approver_id': suggested_approver.id if suggested_approver else False,
            }
        }
    
    def action_view_related_documents(self):
        """عرض الوثائق المرتبطة"""
        self.ensure_one()
        if not self.related_documents:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('لا توجد وثائق مرتبطة'),
                    'message': _('لم يتم ربط أي وثائق بهذه الوثيقة'),
                    'type': 'info'
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'الوثائق ذات الصلة بـ {self.name}',
            'res_model': 'document.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.related_documents.ids)],
            'context': {
                'search_default_group_by_processing_state': 1,
            },
            'target': 'current',
        }
    
    def _map_urgency_to_approval_urgency(self):
        """تحويل مستوى الأولوية في الوثيقة إلى مستوى العجلة في الموافقة"""
        priority_mapping = {
            '0': 'normal',     
            '1': 'urgent',     
            '2': 'very_urgent', 
            '3': 'critical'     
        }
        return priority_mapping.get(self.priority, 'normal')

    @api.onchange('document_direction')
    def _onchange_smart_classification(self):
        """Placeholder لتصنيف تلقائي بدون حقول مهجورة"""
        return

    @api.onchange('sender_employee_id')
    def _onchange_sender_employee_id_set_department(self):
        """عند اختيار موظف مرسل، تعيين قسمه تلقائياً إن لم يكن محدداً"""
        for rec in self:
            if rec.sender_employee_id and rec.sender_employee_id.department_id:
                if not rec.department_id:
                    rec.department_id = rec.sender_employee_id.department_id
        return None
    
    def _get_default_sender_employee(self):
        """الحصول على الموظف المرسل الافتراضي"""
        current_user = self.env.user
        if current_user.employee_id:
            return current_user.employee_id.id
        return False
    
    def _get_default_sender_partner(self):
        """الحصول على الجهة المرسلة الافتراضية"""
        current_user = self.env.user
        # إذا كانت الوثيقة واردة وفق سياق الإنشاء، لا نعيّن قيمة افتراضية
        try:
            if self.env.context.get('default_document_type') == 'incoming':
                return False
        except Exception:
            pass

        if current_user.employee_id and current_user.employee_id.department_id:
            department = current_user.employee_id.department_id
            

            department_partner = self.env['res.partner'].search([
                ('name', 'ilike', department.name)
            ], limit=1)
            
            if department_partner:
                return department_partner.id
            elif current_user.employee_id.work_contact_id:
                return current_user.employee_id.work_contact_id.id
        

        return current_user.partner_id.id if current_user.partner_id else False
    

    @api.onchange('recipient_employee_id')
    def _onchange_recipient_employee_id_set_department(self):
        """عند اختيار موظف مستقبل، تعيين قسمه تلقائياً إن لم يكن محدداً"""
        for rec in self:
            if rec.recipient_employee_id and rec.recipient_employee_id.department_id:
                if not rec.department_id:
                    rec.department_id = rec.recipient_employee_id.department_id
        return None
    
    @api.onchange('department_id')
    def _onchange_department_adjust_employees(self):
        """عند تغيير القسم، لا نقوم بإفراغ المرسل/المستلم للسماح بالتوجيه بين الأقسام"""
        # تم السماح بالتوجيه عبر الأقسام؛ لا تغيير قسري للقيم هنا.
        return None
    
    def _get_allowed_employee_ids(self):
        """الحصول على قائمة الموظفين المسموح لهم بالوصول"""
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_doc_manager') or 
            current_user.has_group('mgt_documents.group_doc_admin')):
            return self.env['hr.employee'].search([]).ids
        

        elif current_user.has_group('mgt_documents.group_doc_approver'):
            if current_user.employee_id and current_user.employee_id.department_id:
                user_department = current_user.employee_id.department_id

                child_departments = self._get_child_departments(user_department)
                all_departments = [user_department.id] + child_departments.ids
                
                employees = self.env['hr.employee'].search([
                    ('department_id', 'in', all_departments)
                ])
                return employees.ids
            return [current_user.employee_id.id] if current_user.employee_id else []
        else:
            return [current_user.employee_id.id] if current_user.employee_id else []

    @api.constrains('category_id')
    def _check_category_access(self):
        """منع استخدام فئة لا يملك المستخدم صلاحية الوصول إليها"""
        for rec in self:
            if rec.category_id and not rec.category_id.is_accessible_by_user(self.env.user):
                raise ValidationError(_('ليس لديك صلاحية استخدام فئة الوثائق: %s') % rec.category_id.display_name)
    
    def _get_allowed_department_ids(self):
        """الحصول على قائمة الأقسام المسموح بالوصول إليها"""
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_doc_manager') or 
            current_user.has_group('mgt_documents.group_doc_admin')):
            return self.env['hr.department'].search([]).ids
        

        elif current_user.has_group('mgt_documents.group_doc_approver'):
            if current_user.employee_id and current_user.employee_id.department_id:
                user_department = current_user.employee_id.department_id
                child_departments = self._get_child_departments(user_department)
                return [user_department.id] + child_departments.ids
            return []
        else:
            if current_user.employee_id and current_user.employee_id.department_id:
                return [current_user.employee_id.department_id.id]
            return []
    
    def _get_child_departments(self, parent_department):
        """الحصول على الأقسام الفرعية التابعة لقسم معين"""
        child_departments = self.env['hr.department'].search([
            ('parent_id', '=', parent_department.id)
        ])
        
        all_children = child_departments
        for child in child_departments:
            all_children |= self._get_child_departments(child)
        
        return all_children
    
    def _check_access_rights(self, operation, raise_exception=True):
        """التحقق من صلاحيات الوصول للعمليات"""
        result = super()._check_access_rights(operation, raise_exception=raise_exception)
        
        current_user = self.env.user
        
        if operation == 'unlink':
            if not (current_user.has_group('mgt_documents.group_doc_manager') or 
                   current_user.has_group('mgt_documents.group_doc_admin')):
                if raise_exception:
                    raise UserError(_('ليس لديك صلاحية حذف الوثائق'))
                return False
        
        return result
    
    def check_document_access(self, operation='read'):
        """التحقق من صلاحية الوصول لوثيقة معينة"""
        self.ensure_one()
        current_user = self.env.user
        
        if (current_user.has_group('mgt_documents.group_doc_manager') or 
            current_user.has_group('mgt_documents.group_doc_admin')):
            return True
        

        if self.create_uid == current_user:
            return True
        

        if current_user.has_group('mgt_documents.group_doc_approver'):
            if (current_user.employee_id and 
                current_user.employee_id.department_id and 
                self.department_id == current_user.employee_id.department_id):
                return True
        
        if self.confidentiality_level in ['confidential', 'top_secret']:
            return (current_user.has_group('mgt_documents.group_doc_approver') or
                   current_user.has_group('mgt_documents.group_doc_manager') or
                   current_user.has_group('mgt_documents.group_doc_admin'))
        
        return False
    
    _sql_constraints = [
        ('reference_number_unique', 'UNIQUE(reference_number, company_id)', 'الرقم المرجعي يجب أن يكون فريداً!'),
        ('retention_period_positive', 'CHECK(retention_period > 0)', 'فترة الاحتفاظ يجب أن تكون أكبر من صفر!'),
    ]
    
    
    def _build_hierarchical_approvers(self, max_levels=None, include_dept_manager=True):
        """
        بناء السلسلة الهرمية للموافقات بناءً على الهيكل التنظيمي
        
        :param max_levels: الحد الأقصى لمستويات الموافقة
        :param include_dept_manager: تضمين مدير القسم في بداية السلسلة
        :return: قائمة بمعرفات المستخدمين مرتبة حسب التسلسل الهرمي
        """
        self.ensure_one()
        
        employee = self.sender_employee_id
        if not employee:
            _logger.warning(f"لا يوجد موظف مرسل محدد للوثيقة {self.reference_number}")
            return []
        
        config = self.env['ir.config_parameter'].sudo()
        if max_levels is None:
            max_levels = int(config.get_param('mgt_documents.max_approval_levels', 5))
        
        chain_users = []
        visited_emp_ids = set()
        current = employee
        

        if include_dept_manager and employee.department_id and employee.department_id.manager_id:
            dept_manager = employee.department_id.manager_id
            if (
                dept_manager.user_id and
                (
                    dept_manager.user_id.has_group('mgt_documents.group_doc_approver') or
                    dept_manager.user_id.has_group('mgt_documents.group_doc_manager') or
                    dept_manager.user_id.has_group('mgt_documents.group_doc_admin')
                ) and
                dept_manager.id != employee.id
            ):
                chain_users.append(dept_manager.user_id)
                visited_emp_ids.add(dept_manager.id)
                _logger.info(f"تم إضافة مدير القسم {dept_manager.name} للسلسلة الهرمية")
        

        while current and current.parent_id and current.parent_id.id not in visited_emp_ids:
            manager = current.parent_id
            

            if (
                manager.user_id and
                (
                    manager.user_id.has_group('mgt_documents.group_doc_approver') or
                    manager.user_id.has_group('mgt_documents.group_doc_manager') or
                    manager.user_id.has_group('mgt_documents.group_doc_admin')
                ) and
                manager.id != employee.id
            ):
                
                if self._can_approve_confidentiality_level(manager.user_id):
                    chain_users.append(manager.user_id)
                    _logger.info(f"تم إضافة المدير {manager.name} للسلسلة الهرمية")
                else:
                    _logger.warning(f"المدير {manager.name} لا يملك صلاحية الاطلاع على مستوى السرية {self.confidentiality_level}")
            
            visited_emp_ids.add(manager.id)
            current = manager
            

            if max_levels and len(chain_users) >= max_levels:
                _logger.info(f"تم الوصول للحد الأقصى من مستويات الموافقة: {max_levels}")
                break
        

        dedup_users = []
        seen_user_ids = set()
        for user in chain_users:
            if user.id not in seen_user_ids:
                dedup_users.append(user)
                seen_user_ids.add(user.id)
        
        _logger.info(f"تم بناء سلسلة موافقة بـ {len(dedup_users)} مستوى للوثيقة {self.reference_number}")
        return dedup_users
    
    def _can_approve_confidentiality_level(self, user):
        """
        التحقق من قدرة المستخدم على الموافقة على المستوى المحدد من السرية
        
        :param user: المستخدم المراد فحصه
        :return: True إذا كان يمكنه الموافقة، False إذا لم يكن
        """
        if self.confidentiality_level == 'public':
            return True
        elif self.confidentiality_level == 'internal':
            return user.has_group('base.group_user') or user.has_group('mgt_documents.group_doc_viewer')
        elif self.confidentiality_level == 'confidential':
            return user.has_group('mgt_documents.group_doc_manager') or user.has_group('mgt_documents.group_doc_admin')
        elif self.confidentiality_level == 'top_secret':
            return user.has_group('mgt_documents.group_doc_admin')
        return False
    
    @api.model
    def auto_archive_expired_documents(self):
        """أرشفة الوثائق المنتهية الصلاحية تلقائياً"""
        today = fields.Date.today()
        expired_docs = self.search([
            ('auto_archive_date', '<=', today),
            ('processing_state', '!=', 'archived')
        ])
        
        archived_count = 0
        for doc in expired_docs:
            try:
                old_state = doc.processing_state
                doc.write({
                    'processing_state': 'archived',
                    'archived_date': fields.Datetime.now(),
                    'archived_by': self.env.user.id,
                    'archive_location': f'AUTO_ARCHIVE_{today.strftime("%Y%m%d")}'
                })
                doc._create_history_record('أرشفة الوثيقة', 'تم الأرشفة التلقائية', old_state, 'archived')
                archived_count += 1
            except Exception as e:
                _logger.warning(f"فشل في أرشفة الوثيقة {doc.id}: {str(e)}")
                continue
        
        _logger.info(f"تم أرشفة {archived_count} وثيقة تلقائياً")
        return archived_count

    @api.model
    def notify_pre_archive_candidates(self):
        """إشعار الوثائق المرشحة للأرشفة قبل موعدها بناءً على إعدادات الفئة.

        - تبحث عن الوثائق التي لديها `auto_archive_date` محددة وليست مؤرشفة بعد.
        - إن كانت فئتها تفعل `notify_before_archive`، تُرسل إشعاراً عندما يكون الفرق بين اليوم و`auto_archive_date`
          أقل أو يساوي `notification_days` المحددة على الفئة.
        """
        try:
            today = fields.Date.today()
            # جلب نطاق أولي: وثائق لها تاريخ أرشفة تلقائي وليست مؤرشفة
            docs = self.search([
                ('auto_archive_date', '!=', False),
                ('processing_state', '!=', 'archived')
            ], limit=500)
            notified = 0
            for doc in docs:
                cat = getattr(doc, 'category_id', False)
                if not cat or not getattr(cat, 'notify_before_archive', False):
                    continue
                try:
                    days = int(getattr(cat, 'notification_days', 7) or 7)
                except Exception:
                    days = 7
                threshold_date = today + timedelta(days=days)
                # إذا كان auto_archive_date خلال الفترة المعلنة
                if doc.auto_archive_date and doc.auto_archive_date <= threshold_date:
                    try:
                        msg = _(
                            "تنبيه: سيتم أرشفة هذه الوثيقة تلقائياً في %(date)s.",
                            date=doc.auto_archive_date.strftime('%Y-%m-%d') if hasattr(doc.auto_archive_date, 'strftime') else str(doc.auto_archive_date)
                        )
                    except Exception:
                        msg = _('تنبيه: هذه الوثيقة مرشحة للأرشفة التلقائية قريباً.')
                    try:
                        doc.message_post(body=msg, message_type='notification')
                    except Exception:
                        pass
                    notified += 1
            _logger.info("[DOC][cron][notify_pre_archive] notified=%s", notified)
            return notified
        except Exception as e:
            _logger.warning("[DOC][cron][notify_pre_archive][error] %s", str(e))
            return 0

    @api.model
    def update_performance_metrics(self):
        """تحديث مؤشرات الأداء"""

        total_docs = self.search_count([])
        pending_approvals = self.search_count([('has_pending_approvals', '=', True)])
        archived_docs = self.search_count([('processing_state', '=', 'archived')])
        
        metrics = {
            'total_documents': total_docs,
            'pending_approvals': pending_approvals,
            'archived_documents': archived_docs,
            'last_update': fields.Datetime.now()
        }
        
        _logger.info(f"مؤشرات الأداء: {metrics}")
        

        return metrics

    @api.model
    def cleanup_temporary_data(self):
        """تنظيف البيانات المؤقتة"""

        old_date = fields.Datetime.now() - timedelta(days=365)
        old_history = self.env['document.history'].search([
            ('timestamp', '<', old_date)
        ])
        
        deleted_count = 0
        if old_history:
            deleted_count = len(old_history)
            old_history.unlink()


        very_old_date = fields.Datetime.now() - timedelta(days=1825) 
        very_old_docs = self.search([
            ('archived_date', '<', very_old_date),
            ('processing_state', '=', 'archived')
        ])
        
        if very_old_docs:
            deleted_count += len(very_old_docs)
            very_old_docs.unlink()
        
        _logger.info(f"تم تنظيف {deleted_count} سجل قديم")
        return deleted_count


class DocumentKeyword(models.Model):
    """نموذج الكلمات المفتاحية للوثائق"""
    
    _name = 'document.keyword'
    _description = 'الكلمات المفتاحية'
    _order = 'name'
    
    name = fields.Char(
        string='الكلمة المفتاحية',
        required=True
    )
    
    description = fields.Text(
        string='الوصف'
    )
    
    color = fields.Integer(
        string='اللون',
        default=0
    )
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'الكلمة المفتاحية يجب أن تكون فريدة!')
    ]
# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class DocumentDocument(models.Model):
    _name = 'document.document'
    _description = 'Documents and Messages'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'display_name'
    

    name = fields.Char(
        string='Document Title',
        required=True,
        tracking=True
    )
    
    reference_number = fields.Char(
        string='Reference Number',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True
    )
    
    display_name = fields.Char(
        string='Document Name',
        compute='_compute_display_name',
        store=True
    )
    
    date = fields.Datetime(
        string='Document Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    

    document_direction = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'),
        ('internal', 'Internal')
    ], string='Document Direction', compute='_compute_document_direction', store=True, tracking=True)

    document_type = fields.Selection([
        ('incoming', 'Incoming'),
        ('outgoing', 'Outgoing'), 
        ('internal', 'Internal'),
        ('circular', 'Circular'),
        ('memo', 'Memo'),
        ('request', 'Request'),
        ('report', 'Report'),
        ('letter', 'Letter'),
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('other', 'Other'),
    ], string='Document Type', default='incoming', tracking=True)
    
    document_category = fields.Selection([
        ('incoming_official', 'Official Incoming'),
        ('outgoing_official', 'Official Outgoing'),
        ('internal_memo', 'Internal Memo'),
        ('employee_request', 'Employee Request'),
        ('external_inquiry', 'External Inquiry'),
        ('decision_request', 'Decision Request'),
        ('administrative_order', 'Administrative Order'),
        ('financial_document', 'Financial Document'),
        ('legal_document', 'Legal Document'),
        ('technical_report', 'Technical Report')
    ], string='Document Category', tracking=True, help='Document category based on BPM standards')
    
    routing_priority = fields.Selection([
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('very_urgent', 'Very Urgent'),
        ('confidential', 'Confidential')
    ], string='Routing Priority', default='routine', tracking=True, help='Routing priority for document processing')
    
    processing_state = fields.Selection([
        ('received', 'Received'),
        ('registered', 'Registered'),
        ('routed', 'Routed'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('in_execution', 'In Execution'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold')
    ], string='Processing State', default='received', tracking=True, help='Processing state of the document')
    
    document_type_id = fields.Many2one(
        'document.category',
        string='Document Category',
        tracking=True,
        help='Detailed document category'
    )
    
    

    workflow_id = fields.Many2one(
        'document.workflow.instance',
        string='Workflow Instance',
        help='Workflow instance associated with this document'
    )
    
    current_step = fields.Char(
        string='Current Step',
        help='Current step in the workflow'
    )
    
    received_date = fields.Datetime(
        string='Received Date',
        default=fields.Datetime.now,
        tracking=True,
        help='Date when the document was received'
    )
    
    target_completion_date = fields.Datetime(
        string='Target Completion Date',
        tracking=True,
        help='Target completion date for the document'
    )
    
    actual_completion_date = fields.Datetime(
        string='Actual Completion Date',
        tracking=True,
        help='Actual completion date for the document'
    )
    
    handling_instructions = fields.Text(
        string='Handling Instructions',
        help='Special instructions for processing this document'
    )
    
    escalation_notes = fields.Text(
        string='Escalation Notes',
        help='Notes about document escalation'
    )
    
    related_tasks = fields.One2many(
        'admin.task',
        'request_document_id',
        string='Related Tasks',
        help='All tasks generated from this document'
    )
    
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_overdue_status',
        store=True,
        help='Has the document exceeded its target completion date'
    )
    
    processing_duration = fields.Float(
        string='Processing Duration (Hours)',
        compute='_compute_processing_duration',
        store=True,
        help='Actual processing duration for the document'
    )
    
    current_version_id = fields.Many2one(
        'document.version',
        string='Current Version'
    )
    

    task_ids = fields.One2many(
        'admin.task',
        'request_document_id',
        string='Related Tasks'
    )
    
    active_tasks_count = fields.Integer(
        string='Active Tasks Count',
        compute='_compute_tasks_count'
    )
    
    approval_requests = fields.One2many(
        'approval.request',
        'document_id',
        string='Approval Requests'
    )
    
    approval_count = fields.Integer(
        string='Approval Count',
        compute='_compute_approval_count'
    )
    
    has_pending_approvals = fields.Boolean(
        string='Has Pending Approvals',
        compute='_compute_has_pending_approvals'
    )
    
    history_ids = fields.One2many(
        'document.history',
        'document_id',
        string='History'
    )
    
    version_count = fields.Integer(
        string='Version Count',
        compute='_compute_version_count'
    )
    history_count = fields.Integer(
        string='History Count',
        compute='_compute_history_count'
    )
    related_documents_count = fields.Integer(
        string='Related Documents Count',
        compute='_compute_related_documents_count'
    )
    
    needs_approval = fields.Boolean(
        string='Needs Approval',
        compute='_compute_needs_approval',
        store=True
    )
    
    has_pending_approvals = fields.Boolean(
        string='Has Pending Approvals',
        compute='_compute_has_pending_approvals',
        store=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By'
    )
    
    approved_date = fields.Datetime(
        string='Approved Date'
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason'
    )
    
    is_archived = fields.Boolean(
        string='Archived',
        compute='_compute_is_archived'
    )
    
    archived_by = fields.Many2one(
        'res.users',
        string='Archived By'
    )
    
    archived_date = fields.Datetime(
        string='Archived Date'
    )
    
    archive_location = fields.Char(
        string='Archive Location'
    )
    
    

    workflow_state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('in_progress', 'In Progress'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('archived', 'Archived')
    ], string='Workflow State', default='draft', tracking=True)
    
    subject = fields.Char(
        string='Subject',
        required=True,
        tracking=True
    )
    
    summary = fields.Text(
        string='Summary',
        tracking=True
    )
    
    content = fields.Html(
        string='Document Content'
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
            }
            rec.document_direction = mapping.get(rec.document_type or 'incoming', 'incoming')


    @api.depends('task_ids.state')
    def _compute_tasks_count(self):
        """Compute active tasks count - optimized for performance"""
        
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
        """Compute overdue status"""
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
        """Compute actual processing duration"""
        for doc in self:
            if doc.received_date and doc.actual_completion_date:
                delta = doc.actual_completion_date - doc.received_date
                doc.processing_duration = delta.total_seconds() / 3600  
            else:
                doc.processing_duration = 0.0
    
    def _compute_approval_count(self):
        for doc in self:
            doc.approval_count = len(doc.approval_requests)
    
    def _compute_version_count(self):
        """Compute document version count"""
        for doc in self:
            doc.version_count = self.env['document.version'].search_count([('document_id', '=', doc.id)])
    
    def _compute_related_documents_count(self):
        """Compute related documents count"""
        for doc in self:
            doc.related_documents_count = len(doc.related_documents)
    @api.depends('workflow_state', 'state')
    def _compute_needs_approval_state_deprecated(self):
        
        return
    
    

    def action_submit_for_processing(self):
        """Submit document for processing"""
        for doc in self:
            if doc.workflow_state != 'draft':
                raise UserError(_('Only draft documents can be submitted for processing'))
            
            doc.write({'workflow_state': 'submitted'})
            
            doc._trigger_workflow()
            
    def action_start_review(self):
        """Start document review"""
        for doc in self:
            if doc.workflow_state not in ['submitted', 'in_review'] or doc.processing_state not in ['routed']:
                raise UserError(_('Only routed documents can be started for review'))
            
            doc.write({
                'workflow_state': 'in_review',
                'processing_state': 'under_review'
            })
            doc._create_review_task()
            doc._create_history_record('Start review document', 'The document review process has started', 'routed', 'under_review')
            
    def action_start_execution(self):
        """Start document execution"""
        for doc in self:
            if doc.processing_state not in ['approved'] or doc.workflow_state not in ['approved']:
                raise UserError(_('Only approved documents can be started for execution'))
            
            doc.write({
                'workflow_state': 'in_progress',
                'processing_state': 'in_execution'
            })
            doc._create_execution_task()
            doc._create_history_record('Start execution document', 'The document execution process has started', 'approved', 'in_execution')
            
    def action_complete(self):
        """Complete document processing"""
        for doc in self:
            
            pending_tasks = self.env['admin.task'].search([
                ('request_document_id', '=', doc.id),
                ('state', 'not in', ['completed', 'cancelled'])
            ])
            
            if pending_tasks:
                raise UserError(_('All tasks must be completed first'))
            
            with doc.env.cr.savepoint():
                doc.write({
                    'workflow_state': 'completed',
                    'processing_state': 'completed',
                    'actual_completion_date': fields.Datetime.now()
                })
                
                if doc.workflow_id:
                    doc.workflow_id.action_complete()
                
    def action_register(self):
        """Register document in the system"""
        for doc in self:
            if doc.processing_state != 'received':
                raise UserError(_('Only received documents can be registered'))
            
            doc.write({
                'processing_state': 'registered',
                'workflow_state': 'submitted'
            })
            
            doc._create_history_record('Register document', 'The document has been registered in the system', 'received', 'registered')
    
    def action_route(self):
        """Route document to the appropriate department"""
        for doc in self:
            if doc.processing_state not in ['registered', 'received']:
                raise UserError(_('Only registered documents can be routed'))
            
            doc._trigger_workflow()
            
            doc.write({
                'processing_state': 'routed',
                'workflow_state': 'in_review'
            })
            
            doc._create_history_record('Route document', 'The document has been routed to the appropriate department', 'registered', 'routed')
    
    def action_approve(self):
        """Approve document"""
        for doc in self:
            if doc.processing_state != 'under_review':
                raise UserError(_('Only documents under review can be approved'))
            
            doc.write({
                'processing_state': 'approved',
                'workflow_state': 'approved'
            })
            
            doc._create_execution_tasks()
            
            doc._create_history_record('Document approval', 'The document has been approved', 'under_review', 'approved')
    
    def action_start_execution_processing(self):
        """Start document execution processing"""
        for doc in self:
            if doc.processing_state != 'approved':
                raise UserError(_('Only approved documents can be started for execution'))
            
            doc.write({
                'processing_state': 'in_execution',
                'workflow_state': 'in_progress'
            })
            
            doc._create_history_record('Start document execution processing', 'The document execution process has started', 'approved', 'in_execution')
    
    def action_reject(self):
        """Reject document"""
        for doc in self:
            old_state = doc.processing_state
            doc.write({
                'processing_state': 'rejected',
                'workflow_state': 'cancelled'
            })
            
            active_tasks = doc.task_ids.filtered(
                lambda t: t.state not in ['completed', 'cancelled']
            )
            active_tasks.write({'state': 'cancelled'})
            
            doc._create_history_record('Reject document', 'The document has been rejected and processing has been cancelled', old_state, 'rejected')
    
    def action_archive(self):
        """Archive document"""
        for doc in self:
            if doc.processing_state != 'completed':
                raise UserError(_('Only completed documents can be archived'))
            
            doc.write({
                'processing_state': 'archived',
                'workflow_state': 'archived'
            })
            
            doc._create_history_record('Archive document', 'The document has been archived in the system', 'completed', 'archived')
    
    def action_hold(self):
        """Hold document processing"""
        for doc in self:
            old_state = doc.processing_state
            doc.write({
                'processing_state': 'on_hold'
            })
            
            doc._create_history_record('Hold document processing', 'The document processing has been held temporarily', old_state, 'on_hold')
    

        
    def _create_execution_tasks(self):
        """Create execution tasks after approval"""
        self.ensure_one()
        
        task_data = {
            'name': f'Execute document: {self.name}',
            'description': f'Execute requirements for document number {self.reference_number}',
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
                
    def _trigger_workflow(self):
        """Activate the automatic workflow - updated for new models"""
        self.ensure_one()
        
        suitable_process = self._find_suitable_business_process()
        
        if suitable_process:
            workflow_instance = suitable_process.create_instance(
                document_id=self.id,
                trigger_data={
                    'document_type': self.document_type,
                    'document_category': self.document_category,
                    'routing_priority': self.routing_priority,
                    'category_id': self.document_type_id.id if self.document_type_id else False,
                    'department_id': self.department_id.id if hasattr(self, 'department_id') and self.department_id else False
                }
            )
            
            if workflow_instance:
                self.workflow_id = workflow_instance.id
                self.processing_state = 'routed'
                self._update_target_completion_date(suitable_process)
                
    def _find_suitable_business_process(self):
        """Find suitable business process"""
        self.ensure_one()
        
        domain = [
            ('state', '=', 'active'),
            ('applicable_to', 'in', ['all_documents', 'specific_categories'])
        ]
        
        if self.document_type_id:
            domain.append(('applicable_category_ids', 'in', [self.document_type_id.id]))
            
        process_type_mapping = {
            'incoming': 'document_routing',
            'request': 'task_assignment',
            'internal': 'approval_flow'
        }
        
        if self.document_type in process_type_mapping:
            domain.append(('process_type', '=', process_type_mapping[self.document_type]))
            
        processes = self.env['workflow.process'].search(domain, limit=1)
        return processes[0] if processes else False
        
    def _update_target_completion_date(self, process):
        """Update target completion date based on the process"""
        if process and process.expected_duration:
            self.target_completion_date = self.received_date + timedelta(
                hours=process.expected_duration
            )
                
    def _find_suitable_process(self):

        self.ensure_one()
        
        domain = [
            ('state', '=', 'active'),
            ('applicable_to', 'in', ['all_documents', 'specific_categories'])
        ]
        
        if hasattr(self, 'category_id') and self.category_id:
            domain.append(('applicable_category_ids', 'in', [self.category_id.id]))
        elif self.document_type_id:
            domain.append(('applicable_category_ids', 'in', [self.document_type_id.id]))
            
        processes = self.env['workflow.process'].search(domain, limit=1)
        return processes[0] if processes else False
        
    def _create_review_task(self):
        """Create review task"""
        self.ensure_one()
        
        reviewer = self._get_default_reviewer()
        
        if reviewer:
            task_data = {
                'name': f'Review document: {self.name}',
                'description': f'Review and evaluate document number {self.reference_number}',
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
                _logger.warning(f'Failed to assign review task: {str(e)}')
            
            return task
        else:
            
            task_data = {
                'name': f'Review document: {self.name}',
                'description': f'Review and evaluate document number {self.reference_number} - needs reviewer assignment',
                'task_type': 'review_document',
                'request_document_id': self.id,
                'priority': '1',
                'due_date': fields.Datetime.now() + timedelta(days=2),
                'state': 'draft'
            }
            
            if self.department_id:
                task_data['assigned_department_id'] = self.department_id.id
            
            task = self.env['admin.task'].create(task_data)
            _logger.info(f'Created review task without reviewers assigned for document {self.reference_number}')
            return task
            
    def _create_execution_task(self):
        """Create execution task"""
        self.ensure_one()
        
        executor = self._get_default_executor()
        
        if executor:
            task_data = {
                'name': f'Execute document: {self.name}',
                'description': f'Execute requirements for document number {self.reference_number}',
                'task_type': 'execute_action',
                'request_document_id': self.id,
                'assigned_employee_id': executor.id,
                'priority': '2',
                'due_date': fields.Datetime.now() + timedelta(days=5),
                'state': 'assigned'
            }
            
            if executor.department_id:
                task_data['assigned_department_id'] = executor.department_id.id
            
            task = self.env['admin.task'].create(task_data)
            
            try:
                if hasattr(task, 'action_assign'):
                    task.action_assign()
            except Exception as e:
                _logger.warning(f'Failed to assign execution task: {str(e)}')
            
            return task
        else:
            task_data = {
                'name': f'Execute document: {self.name}',
                'description': f'Execute requirements for document number {self.reference_number} - needs executor assignment',
                'task_type': 'execute_action',
                'request_document_id': self.id,
                'priority': '2',
                'due_date': fields.Datetime.now() + timedelta(days=5),
                'state': 'draft'
            }
            
            if self.department_id:
                task_data['assigned_department_id'] = self.department_id.id
            
            task = self.env['admin.task'].create(task_data)
            _logger.info(f'Created execution task without executor assigned for document {self.reference_number}')
            return task
            
    def _get_default_reviewer(self):
        """Get default reviewer"""
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
            
        current_user = self.env.user
        if current_user.employee_id:
            employee = current_user.employee_id
            if employee.parent_id:
                return employee.parent_id
            
            if employee.department_id and employee.department_id.manager_id:
                return employee.department_id.manager_id
                
        approvers_group = self.env.ref('mgt_documents.group_document_approver', raise_if_not_found=False)
        if approvers_group and approvers_group.users:
            for user in approvers_group.users:
                if user.employee_id:
                    return user.employee_id
                
        return False
        
    def _get_default_executor(self):
        """Get default executor"""

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
        string='Category',
        required=True,
        tracking=True,
        default=lambda self: self._get_default_category()
    )
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Urgent'),
        ('3', 'Very Urgent')
    ], string='Priority', default='0', tracking=True)
    
    urgency_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Urgency Level', compute='_compute_urgency_level', store=True)
    

    sender_id = fields.Many2one(
        'res.partner',
        string='Sender Partner',
        tracking=True,
        default=lambda self: self._get_default_sender_partner(),
        readonly=True,
        help="Automatically set based on the current user's department"
    )
    
    sender_employee_id = fields.Many2one(
        'hr.employee',
        string='Sender Employee',
        tracking=True,
        default=lambda self: self._get_default_sender_employee(),
        readonly=True,
        help='Automatically set based on the logged-in user'
    )
    
    recipient_id = fields.Many2one(
        'res.partner',
        string='Recipient Partner',
        tracking=True
    )
    
    recipient_employee_id = fields.Many2one(
        'hr.employee',
        string='Recipient Employee',
        tracking=True
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        tracking=True
    )
    
    
    due_date = fields.Date(
        string='Due Date',
        tracking=True,
        help='The date required to complete the document transaction'
    )
    
    completion_percentage = fields.Float(
        string='Completion Percentage',
        compute='_compute_completion_percentage'
    )


    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True, copy=False)
    
    approval_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Approval Status', default='pending', tracking=True)
    
    
    

    submitted_date = fields.Datetime(
        string='Submitted Date',
        readonly=True,
        copy=False
    )
    
    reviewed_date = fields.Datetime(
        string='Reviewed Date',
        readonly=True,
        copy=False
    )
    

    auto_archive_date = fields.Date(
        string='Auto Archive Date',
        compute='_compute_auto_archive_date',
        store=True
    )
    
    retention_period = fields.Integer(
        string='Retention Period (in days)',
        default=365,
        help='Number of days to keep the document before automatic archiving'
    )
    

    keywords = fields.Many2many(
        'document.keyword',
        string='Keywords'
    )
    
    confidentiality_level = fields.Selection([
        ('public', 'Public'),
        ('internal', 'Internal'),
        ('confidential', 'Confidential'),
        ('top_secret', 'Top Secret')
    ], string='Confidentiality Level', default='internal', tracking=True)
    
    related_documents = fields.Many2many(
        'document.document',
        'document_related_rel',
        'document1_id',
        'document2_id',
        string='Related Documents'
    )
    
    notes = fields.Text(
        string='Internal Notes'
    )
    

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        """Set document type based on document_type_id"""
        if self.document_type_id:
            doc_type_name = self.document_type_id.name.lower()
            if 'incoming' in doc_type_name:
                self.document_type = 'incoming'
            elif 'outgoing' in doc_type_name:
                self.document_type = 'outgoing'
            elif 'internal' in doc_type_name:
                self.document_type = 'internal'
            elif 'report' in doc_type_name:
                self.document_type = 'report'
            elif 'memo' in doc_type_name:
                self.document_type = 'memo'
            elif 'circular' in doc_type_name:
                self.document_type = 'circular'
            else:
                self.document_type = 'incoming'
    
    @api.onchange('document_type')
    def _onchange_document_type(self):
        """Set document category based on document type"""
        if self.document_type:
            type_category_map = {
                'incoming': 'mgt_documents.category_incoming',
                'outgoing': 'mgt_documents.category_outgoing',
                'internal': 'mgt_documents.category_internal',
                'circular': 'mgt_documents.category_circulars',

                'memo': 'mgt_documents.category_memos',
                'report': 'mgt_documents.category_reports'
            }
            
            category_ref = type_category_map.get(self.document_type)
            if category_ref:
                category = self.env.ref(category_ref, raise_if_not_found=False)
                if category and category.is_active:
                    self.document_type_id = category.id
                    self.category_id = category.parent_id.id if category.parent_id else category.id

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

    def _generate_reference_number(self, vals):
        """Generate auto reference number"""
        doc_type = vals.get('document_type', 'incoming')
        category_id = vals.get('document_type_id')
        

        prefix_map = {
            'incoming': 'IN',
            'outgoing': 'OUT', 
            'internal': 'INT',
            'circular': 'CIR',
            'memo': 'MEM',
            'request': 'REQ',
            'report': 'RPT'
        }
        
        prefix = prefix_map.get(doc_type, 'DOC')
        
        if category_id:
            category = self.env['document.category'].browse(category_id)
            if category.code:
                prefix = f"{prefix}-{category.code}"
        
        sequence = self.env['ir.sequence'].next_by_code('document.document') or '001'
        
        return f"{prefix}/{fields.Date.today().year}/{sequence}"
    
    def _auto_trigger_workflow_on_create(self):
        """Auto trigger workflow on create"""
        self.ensure_one()
        
        auto_trigger_types = ['incoming', 'request', 'memo']
        auto_trigger_categories = ['incoming_official', 'employee_request', 'decision_request']
        
        should_trigger = (
            self.document_type in auto_trigger_types or
            self.document_category in auto_trigger_categories or
            (self.routing_priority in ['urgent', 'very_urgent', 'confidential'])
        )
        
        if should_trigger:
            try:

                if self.workflow_state == 'draft':
                    self.write({
                        'workflow_state': 'submitted',
                        'processing_state': 'registered'
                    })
                    
                    self._trigger_workflow()
                    
                    self._create_history_record(
                        'Auto trigger workflow',
                        'Workflow triggered automatically',
                        'draft',
                        'submitted'
                    )
                    
            except Exception as e:
                _logger.warning(f'Auto trigger workflow failed for document {self.id}: {str(e)}')
    
    @api.depends('name', 'reference_number')
    def _compute_display_name(self):
        """Compute display name for document"""
        for record in self:
            if record.reference_number and record.reference_number != _('New'):
                record.display_name = f"[{record.reference_number}] {record.name}"
            else:
                record.display_name = record.name or _('New Document')
    



    
    @api.depends('approval_requests')
    def _compute_approval_count(self):
        """Compute approval count"""
        for record in self:
            record.approval_count = len(record.approval_requests)
    
    @api.depends('approval_requests.request_status')
    def _compute_has_pending_approvals(self):
        """Compute pending approvals"""
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
        """Compute history count"""
        for record in self:
            record.history_count = len(record.history_ids)
    
    @api.depends('current_version_id')
    def _compute_version_count(self):
        """Compute version count"""
        for record in self:
            version_count = self.env['document.version'].search_count([
                ('document_id', '=', record.id)
            ])
            record.version_count = version_count
    
    @api.depends('related_documents')
    def _compute_related_documents_count(self):
        """Compute related documents count"""
        for record in self:
            record.related_documents_count = len(record.related_documents)
    
    @api.depends('date', 'approved_date', 'retention_period', 'category_id', 'category_id.auto_archive_enabled', 'category_id.auto_archive_days', 'category_id.archive_condition')
    def _compute_auto_archive_date(self):
        """Compute auto archive date based on category settings.

        Priority:
        - If the category is enabled for auto archiving:
          - after_days: Depends on (approved_date or date) + auto_archive_days
          - after_approval: Depends on approved_date only
          - manual: no auto archive date
        - Otherwise: fallback to retention_period at document level
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
        """Compute if the document needs approval"""
        for record in self:
            needs_by_type = record.document_type in ['outgoing', 'circular', 'memo', 'report']
            needs_by_category = bool(record.category_id and record.category_id.requires_approval)
            record.needs_approval = needs_by_type or needs_by_category
    
    @api.depends('workflow_state', 'processing_state')
    def _compute_is_archived(self):
        """Compute if the document is archived"""
        for record in self:
            record.is_archived = (
                (record.workflow_state == 'archived') or
                (record.processing_state == 'archived')
            )
    


    @api.depends('priority', 'workflow_state', 'date')
    def _compute_urgency_level(self):
        """Compute urgency level based on priority, workflow state, and date"""
        for record in self:
            urgency = 'low'  
            

            if record.priority == '3': 
                urgency = 'critical'
            elif record.priority == '2': 
                urgency = 'high'
            elif record.priority == '1': 
                urgency = 'medium'
            
            if record.workflow_state in ['submitted', 'in_review'] and urgency != 'critical':
                urgency = 'medium' if urgency == 'low' else 'high'
            
            if record.date:
                days_old = (fields.Datetime.now() - record.date).days
                if days_old > 7 and urgency in ['low', 'medium']:
                    urgency = 'medium' if urgency == 'low' else 'high'
            
            record.urgency_level = urgency

    def write(self, vals):
        """Update document with change history"""
        if 'category_id' in vals or 'document_type' in vals:
            for rec in self:
                new_category_id = vals.get('category_id', rec.category_id.id)
                new_type = vals.get('document_type', rec.document_type)
                if new_category_id:
                    cat = self.env['document.category'].browse(new_category_id)
                    allowed = cat.get_allowed_document_types() if cat else []
                    if allowed and new_type not in allowed:
                        raise ValidationError(_("Document type \"%s\" is not allowed in category \"%s\"") % (new_type, cat.display_name))
        tracked_fields = {
            'state': 'State',
            'approval_status': 'Approval Status',
            'name': 'Name',
            'subject': 'Subject',
            'category_id': 'Category',
            'priority': 'Priority'
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
                                    old_display = _('undefined')
                                
                                if new_value:
                                    try:
                                        new_record = self.env[comodel_name].browse(new_value)
                                        new_display = new_record.display_name if new_record.exists() else str(new_value)
                                    except Exception:
                                        new_display = str(new_value)
                                else:
                                    new_display = _('undefined')
                                
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
        """Delete document with permission checks"""
        for record in self:
            if record.workflow_state not in ('draft', 'cancelled'):
                raise UserError(_('Cannot delete document unless it is in draft or cancelled state'))
            

            record._create_history_record('deleted', _('Document deleted'))
        
        return super().unlink()
    

    def _get_default_document_type(self):
        """Get default document type"""

        default_type = self.env.ref('mgt_documents.category_incoming', raise_if_not_found=False)
        if default_type and default_type.is_active:
            return default_type.id
        

        default_type = self.env['document.category'].search([
            ('parent_id', '!=', False),
            ('is_active', '=', True)
        ], limit=1)
        return default_type.id if default_type else False
    
    def _get_default_category(self):
        """Get default category"""

        default_category = self.env.ref('mgt_documents.category_administrative', raise_if_not_found=False)
        if default_category and default_category.is_active:
            return default_category.id
        

        default_category = self.env['document.category'].search([
            ('is_active', '=', True)
        ], limit=1)
        return default_category.id if default_category else False
    
    def _create_history_record(self, action, description, old_state=None, new_state=None):
        """Create history record for document"""

        action_mapping = {
            'created': 'created',
            'submitted': 'submitted',
            'reviewed': 'reviewed',
            'approved': 'approved',
            'rejected': 'rejected',
            'other': 'other',
            'updated': 'updated',
            'deleted': 'deleted',
        }
        
        mapped_action = action_mapping.get(action, 'other')
        
        try:
            self.env['document.history'].create({
                'document_id': self.id,
                'user_id': self.env.user.id,
                'action': mapped_action,
                'description': description,
                'timestamp': fields.Datetime.now(),
                'previous_state': old_state,
                'new_state': new_state or self.state,
            })
        except Exception as e:
            
            _logger.warning(f'Failed to create history record for document {self.id}: {str(e)}')
    

    def action_submit(self):
        """Submit document for review"""
        for record in self:
            if record.workflow_state != 'draft':
                raise UserError(_('Document can only be submitted from draft state'))
            
            old_state = record.workflow_state
            record.write({
                'workflow_state': 'submitted',
                'submitted_date': fields.Datetime.now()
            })
            
            record._create_history_record('submitted', _('Document submitted for review'), old_state, 'submitted')
            
            if record.document_type in ['outgoing', 'circular', 'memo']:
                record._create_approval_request()
    
    
    def _create_approval_request(self):
        """Create approval request for document"""

        approver = self._get_approver()
        
        if approver:
            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
            if category:
                self.env['approval.request'].create({
                    'name': f'Approval request for document: {self.name}',
                    'category_id': category.id,
                    'request_owner_id': self.env.user.id,
                    'date_start': fields.Datetime.now(),
                    'reason': f'Approval request for document number: {self.reference_number or self.name}',
                    'document_id': self.id,
                })
    
    def _get_approver(self):
        """Get the appropriate approver"""
        if self.department_id and self.department_id.manager_id:
            return self.department_id.manager_id
        
        group = self.env.ref('mgt_documents.group_document_manager', raise_if_not_found=False)
        if group and group.users:
            return group.users[0]
        
        return False
    
    def _get_approval_category(self):
        """Get the appropriate approval category based on document type"""
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
    
    @api.onchange('sender_id', 'sender_employee_id')
    def _compute_sender_info(self):
        """Get the appropriate sender information"""
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
        """View approval requests"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approval Requests'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
            'target': 'current',
        }

    def action_view_tasks(self):
        """View related tasks"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Tasks'),
            'res_model': 'admin.task',
            'view_mode': 'list,form,kanban',
            'domain': [('request_document_id', '=', self.id)],
            'context': {'default_request_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_history(self):
        """View change history"""
        return {
            'name': _('Change History'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.history',
            'view_mode': 'list,form',
            'domain': [('document_id', 'in', self.ids)],
            'context': {'default_document_id': self.id if len(self) == 1 else False}
        }
    
    def action_view_versions(self):
        """View document versions"""
        self.ensure_one()
        return {
            'name': _('Document Versions'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.version',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {
                'default_document_id': self.id,
                'search_default_document_id': self.id
            }
        }
    
    def action_view_workflow_instances(self):
        """View related workflow instances"""
        self.ensure_one()
        if not self.workflow_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No workflow instance found for this document',
                    'type': 'info'
                }
            }
        
        return {
            'name': _('Workflow Instances'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.workflow.instance',
            'res_id': self.workflow_id.id,
            'view_mode': 'form',
            'target': 'current'
        }
    

    @api.constrains('date')
    def _check_date(self):
        """Check document date"""
        for record in self:
            if record.date and record.date > fields.Datetime.now():
                raise ValidationError(_('Document date cannot be in the future'))
    
    @api.constrains('retention_period')
    def _check_retention_period(self):
        """Check retention period"""
        for record in self:
            if record.retention_period and record.retention_period < 1:
                raise ValidationError(_('Retention period must be greater than zero'))
    
    @api.model
    def _update_existing_document_types(self):
        """Update document type for existing documents"""
        try:
            domain = ['|', ('document_type', '=', False), ('document_type', '=', 'other')]
            documents = self.search(domain)
            
            for doc in documents:
                try:
                    if not doc.name or not doc.subject:
                        continue
                        
                    if doc.document_type_id and doc.document_type_id.name:
                        doc_type_name = doc.document_type_id.name.lower()
                        new_type = 'other'  
                        
                        if 'وارد' in doc_type_name:
                            new_type = 'incoming'
                        elif 'صادر' in doc_type_name:
                            new_type = 'outgoing'
                        elif 'داخلي' in doc_type_name:
                            new_type = 'internal'
                        elif 'تقرير' in doc_type_name:
                            new_type = 'report'
                        elif 'مذكرة' in doc_type_name:
                            new_type = 'memo'
                        elif 'تعميم' in doc_type_name:
                            new_type = 'circular'
                        elif 'رسالة' in doc_type_name:
                            new_type = 'letter'
                        elif 'عقد' in doc_type_name:
                            new_type = 'contract'
                        elif 'فاتورة' in doc_type_name:
                            new_type = 'invoice'
                        
                        doc.with_context(skip_validation=True).write({'document_type': new_type})
                        
                    elif not doc.document_type:
                        doc.with_context(skip_validation=True).write({'document_type': 'incoming'})
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
            
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """Create new document with correct numbering"""
        for vals in vals_list:
            document_type = vals.get('document_type', 'incoming')
            
            if vals.get('reference_number', _('جديد')) == _('جديد'):

                sequence_mapping = {
                    'incoming': 'document.incoming',
                    'outgoing': 'document.outgoing', 
                    'internal': 'document.internal',
                    'report': 'document.report',
                    'memo': 'document.memo',

                    'circular': 'document.circular',
                    'letter': 'document.letter',
                    'contract': 'document.contract',
                    'invoice': 'document.invoice',
                    'other': 'document.other'
                }
                
                sequence_code = sequence_mapping.get(document_type, 'document.other')
                reference_number = self.env['ir.sequence'].next_by_code(sequence_code)
                
                if reference_number:
                    vals['reference_number'] = reference_number
                else:
                    vals['reference_number'] = f"{document_type.upper()}-{fields.Datetime.now().year}-001"

            category_id = vals.get('category_id') or vals.get('document_type_id')
            if category_id and not vals.get('priority'):
                cat = self.env['document.category'].browse(category_id)
                if cat and cat.default_priority:
                    priority_map = {
                        'low': '0',
                        'normal': '1',
                        'high': '2',
                        'urgent': '3',
                    }
                    vals['priority'] = priority_map.get(cat.default_priority)

            if vals.get('category_id'):
                cat = self.env['document.category'].browse(vals['category_id'])
                allowed = cat.get_allowed_document_types() if cat else []
                if allowed:
                    current_type = vals.get('document_type') or document_type
                    if current_type not in allowed:
                        raise ValidationError(_('Document type "%s" is not allowed in category "%s"') % (current_type, cat.display_name))
        
        documents = super().create(vals_list)
        for doc in documents:
            try:
                doc._auto_trigger_workflow_on_create()
            except Exception:
                pass
        return documents
    
    def action_request_approval(self):
        """Request approval"""
        self.ensure_one()
        
        category = self._get_approval_category()
        suggested_approver = self._get_approver()
        urgency_mapping = {'0': 'normal', '1': 'urgent', '2': 'very_urgent', '3': 'critical'}
        
        return {
            'name': _('Request Approval'),
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_name': f'Approval Request: {self.name}',
                'default_category_id': category.id if category else False,
                'default_request_owner_id': self.env.user.id,
                'default_urgency_level': urgency_mapping.get(self.priority, 'normal'),
                'default_confidentiality_level': getattr(self, 'confidentiality_level', 'internal'),
                'default_department_id': self.department_id.id if self.department_id else False,
                'default_reason': f'Approval Request for document number: {self.reference_number}',
                'transfer_document_attachments': True,
                'suggested_approver_id': suggested_approver.id if suggested_approver else False,
            }
        }

    
    
    @api.depends('workflow_state')
    def _compute_completion_percentage(self):
        """Calculate document completion percentage"""
        for record in self:
            percentages = {
                'draft': 0,
                'submitted': 20,
                'in_review': 40,
                'approved': 100,
                'rejected': 0,
                'archived': 100,
                'cancelled': 0
            }
            record.completion_percentage = percentages.get(record.workflow_state, 0)
    
    
    def action_view_smart_approvals(self):
        """View smart approvals requests"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Smart Approvals'),
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id}
        }
    
    def action_auto_route(self):
        """Auto route document using document router (single result)"""
        self.ensure_one()
        res = self.env['document.router'].process_document(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto routing result') if res.get('success') else _('No matching routing rule'),
                'message': res.get('message', ''),
                'type': 'success' if res.get('success') else 'warning'
            }
        }
    
    def action_view_workflow_instances(self):
        """View related workflow instances"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Workflow Instances'),
            'res_model': 'document.workflow.instance',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_tasks(self):
        """View related tasks"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Tasks'),
            'res_model': 'admin.task',
            'view_mode': 'list,form',
            'domain': [('request_document_id', '=', self.id)],
            'context': {'default_request_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_history(self):
        """View change history"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change History'),
            'res_model': 'document.history',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_versions(self):
        """View document versions"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Document Versions'),
            'res_model': 'document.version',
            'view_mode': 'list,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
            'target': 'current',
        }
    
    def action_view_related_documents(self):
        """View related documents"""
        self.ensure_one()
        if not self.related_documents:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No related documents'),
                    'message': _('No related documents found for this document'),
                    'type': 'info'
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Related Documents for {self.name}',
            'res_model': 'document.document',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.related_documents.ids)],
            'context': {
                'search_default_group_by_state': 1,
            },
            'target': 'current',
        }
    
    def _map_urgency_to_approval_urgency(self):
        """Convert document urgency level to approval urgency level"""
        priority_mapping = {
            '0': 'normal',     
            '1': 'urgent',     
            '2': 'very_urgent', 
            '3': 'critical'     
        }
        return priority_mapping.get(self.priority, 'normal')
    
    
    
    
    
    @api.onchange('document_direction')
    def _onchange_smart_classification(self):
        """Placeholder for automatic classification without hidden fields"""
        return

    def action_auto_route(self):
        """Auto route document"""
        self.ensure_one()
        res = self.env['document.router'].process_document(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto routing result') if res.get('success') else _('No matching routing rule'),
                'message': res.get('message', ''),
                'type': 'success' if res.get('success') else 'warning'
            }
        }
    
    def _get_default_sender_employee(self):
        """Get default sender employee"""
        current_user = self.env.user
        if current_user.employee_id:
            return current_user.employee_id.id
        return False
    
    def _get_default_sender_partner(self):
        """Get default sender partner"""
        current_user = self.env.user
        

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
    def _onchange_recipient_employee_filter(self):
        """Apply dynamic employee filter"""
        allowed_employee_ids = self._get_allowed_employee_ids()
        return {
            'domain': {
                'recipient_employee_id': [('id', 'in', allowed_employee_ids)]
            }
        }
    
    @api.onchange('department_id')
    def _onchange_department_filter(self):
        """Apply dynamic department filter"""
        allowed_department_ids = self._get_allowed_department_ids()
        return {
            'domain': {
                'department_id': [('id', 'in', allowed_department_ids)]
            }
        }
    
    def _get_allowed_employee_ids(self):
        """Get list of employees allowed to access"""
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_document_manager') or 
            current_user.has_group('mgt_documents.group_document_admin')):
            return self.env['hr.employee'].search([]).ids
        

        elif current_user.has_group('mgt_documents.group_document_approver'):
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
        """Prevent using a category that the user does not have access to"""
        for rec in self:
            if rec.category_id and not rec.category_id.is_accessible_by_user(self.env.user):
                raise ValidationError(_('You do not have access to the document category: %s') % rec.category_id.display_name)
    
    def _get_allowed_department_ids(self):
        """Get list of departments allowed to access"""
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_document_manager') or 
            current_user.has_group('mgt_documents.group_document_admin')):
            return self.env['hr.department'].search([]).ids
        

        elif current_user.has_group('mgt_documents.group_document_approver'):
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
        """Get list of child departments for a given department"""
        child_departments = self.env['hr.department'].search([
            ('parent_id', '=', parent_department.id)
        ])
        
        all_children = child_departments
        for child in child_departments:
            all_children |= self._get_child_departments(child)
        
        return all_children
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        """Custom search to filter documents based on user permissions"""
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_document_manager') or 
            current_user.has_group('mgt_documents.group_document_admin')):
            if count:
                return super().search_count(args)
            return super().search(args, offset=offset, limit=limit, order=order)
        

        elif current_user.has_group('mgt_documents.group_document_approver'):
            if current_user.employee_id and current_user.employee_id.department_id:
                user_department = current_user.employee_id.department_id
                child_departments = self._get_child_departments(user_department)
                allowed_departments = [user_department.id] + child_departments.ids
                
                department_filter = ['|', 
                    ('create_uid', '=', current_user.id),
                    ('department_id', 'in', allowed_departments)
                ]
                args = args + department_filter
            else:

                args = args + [('create_uid', '=', current_user.id)]
        
        

        else:
            args = args + [('create_uid', '=', current_user.id)]
        
        if count:
            return super().search_count(args)
        return super().search(args, offset=offset, limit=limit, order=order)
    
    def _check_access_rights(self, operation, raise_exception=True):
        """Check access rights for operations"""
        result = super()._check_access_rights(operation, raise_exception=raise_exception)
        
        current_user = self.env.user
        
        if operation == 'unlink':
            if not (current_user.has_group('mgt_documents.group_document_manager') or 
                   current_user.has_group('mgt_documents.group_document_admin')):
                if raise_exception:
                    raise UserError(_('You do not have permission to delete documents'))
                return False
        
        return result
    
    @api.model
    def get_user_permissions_info(self):
        """Get user permissions information"""
        current_user = self.env.user
        
        permissions = {
            'is_admin': current_user.has_group('mgt_documents.group_document_admin'),
            'is_manager': current_user.has_group('mgt_documents.group_document_manager'),
            'is_approver': current_user.has_group('mgt_documents.group_document_approver'),
            'can_see_all_documents': (
                current_user.has_group('mgt_documents.group_document_manager') or 
                current_user.has_group('mgt_documents.group_document_admin')
            ),
            'can_delete_documents': (
                current_user.has_group('mgt_documents.group_document_manager') or 
                current_user.has_group('mgt_documents.group_document_admin')
            ),
            'employee_name': current_user.employee_id.name if current_user.employee_id else current_user.name,
            'department_name': (
                current_user.employee_id.department_id.name 
                if current_user.employee_id and current_user.employee_id.department_id 
                else 'Not specified'
            )
        }
        
        return permissions
    
    @api.model
    def get_accessible_documents_count(self):
        """Get count of accessible documents for the current user"""
        return self.search_count([])
    
    def check_document_access(self, operation='read'):
        """Check document access permissions"""
        self.ensure_one()
        current_user = self.env.user
        

        if (current_user.has_group('mgt_documents.group_document_manager') or 
            current_user.has_group('mgt_documents.group_document_admin')):
            return True
        

        if self.create_uid == current_user:
            return True
        

        if current_user.has_group('mgt_documents.group_document_approver'):
            if (current_user.employee_id and 
                current_user.employee_id.department_id and 
                self.department_id == current_user.employee_id.department_id):
                return True
        

        if self.confidentiality_level in ['confidential', 'top_secret']:
            return (current_user.has_group('mgt_documents.group_document_approver') or
                   current_user.has_group('mgt_documents.group_document_manager') or
                   current_user.has_group('mgt_documents.group_document_admin'))
        
        return False
    
    _sql_constraints = [
        ('reference_number_unique', 'UNIQUE(reference_number, company_id)', 'The reference number must be unique!'),
        ('retention_period_positive', 'CHECK(retention_period > 0)', 'Retention period must be greater than zero!'),
    ]
    

    
    def _build_hierarchical_approvers(self, max_levels=None, include_dept_manager=True):
        """
        Build the hierarchical approvers list based on the organizational structure
        
        :param max_levels: The maximum number of approval levels
        :param include_dept_manager: Include department manager at the beginning of the list
        :return: List of user IDs sorted by hierarchical order
        """
        self.ensure_one()
        
        employee = self.sender_employee_id
        if not employee:
            _logger.warning(f"No sender employee specified for document {self.reference_number}")
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
                    dept_manager.user_id.has_group('mgt_documents.group_document_approver') or
                    dept_manager.user_id.has_group('mgt_documents.group_document_manager') or
                    dept_manager.user_id.has_group('mgt_documents.group_document_admin') or
                    dept_manager.user_id.has_group('mgt_documents.group_document_supervisor')
                ) and
                dept_manager.id != employee.id
            ):
                chain_users.append(dept_manager.user_id)
                visited_emp_ids.add(dept_manager.id)
                _logger.info(f"Added department manager {dept_manager.name} to the approval chain")
        

        while current and current.parent_id and current.parent_id.id not in visited_emp_ids:
            manager = current.parent_id
            

            if (
                manager.user_id and
                (
                    manager.user_id.has_group('mgt_documents.group_document_approver') or
                    manager.user_id.has_group('mgt_documents.group_document_manager') or
                    manager.user_id.has_group('mgt_documents.group_document_admin') or
                    manager.user_id.has_group('mgt_documents.group_document_supervisor')
                ) and
                manager.id != employee.id
            ):
                

                if self._can_approve_confidentiality_level(manager.user_id):
                    chain_users.append(manager.user_id)
                    _logger.info(f"Added manager {manager.name} to the approval chain")
                else:
                    _logger.warning(f"Manager {manager.name} does not have permission to view confidentiality level {self.confidentiality_level}")
            
            visited_emp_ids.add(manager.id)
            current = manager
            

            if max_levels and len(chain_users) >= max_levels:
                _logger.info(f"Reached maximum approval levels: {max_levels}")
                break
        

        dedup_users = []
        seen_user_ids = set()
        for user in chain_users:
            if user.id not in seen_user_ids:
                dedup_users.append(user)
                seen_user_ids.add(user.id)
        
        _logger.info(f"Built approval chain with {len(dedup_users)} levels for document {self.reference_number}")
        return dedup_users
    
    def _can_approve_confidentiality_level(self, user):
        """
        Check if the user has permission to approve the specified confidentiality level
        
        :param user: The user to check
        :return: True if the user can approve the confidentiality level, False otherwise
        """
        if self.confidentiality_level == 'public':
            return True
        elif self.confidentiality_level == 'internal':
            return user.has_group('base.group_user') or user.has_group('mgt_documents.group_document_user')
        elif self.confidentiality_level == 'confidential':
            return user.has_group('mgt_documents.group_document_manager') or user.has_group('mgt_documents.group_document_admin')
        elif self.confidentiality_level == 'top_secret':
            return user.has_group('mgt_documents.group_document_admin')
        return False
    
    def _get_approval_category_by_document_type(self):
        """
        Determine the approval category based on the document type
        
        :return: approval.category record or False
        """
        category_mapping = {
            'incoming': 'INCOMING_DOCS',
            'outgoing': 'OUTGOING_DOCS', 
            'internal': 'INTERNAL_DOCS',
            'memo': 'MEMO_APPROVAL',
            'contract': 'CONTRACT_APPROVAL',
            'report': 'REPORT_APPROVAL',
            'circular': 'CIRCULAR_APPROVAL',
        }
        
        category_code = category_mapping.get(self.document_type or 'other', 'GENERAL')
        category = self.env['approval.category'].search([('name', '=', category_code)], limit=1)
        
        if not category:

            category = self.env['approval.category'].search([('name', '=', 'GENERAL')], limit=1)
            if not category:
                category = self.env['approval.category'].create({
                    'name': 'GENERAL',
                    'approver_sequence': 'ordered',
                })
            
        return category


    
    @api.model
    def auto_archive_expired_documents(self):
        """Automatically archive expired documents"""
        today = fields.Date.today()
        expired_docs = self.search([
            ('auto_archive_date', '<=', today),
            ('workflow_state', '!=', 'archived'),
            ('processing_state', '!=', 'archived')
        ])
        
        archived_count = 0
        for doc in expired_docs:
            try:
                old_state = doc.workflow_state
                doc.write({
                    'workflow_state': 'archived',
                    'processing_state': 'archived',
                    'archived_date': fields.Datetime.now(),
                    'archived_by': self.env.user.id,
                    'archive_location': f'AUTO_ARCHIVE_{today.strftime("%Y%m%d")}'
                })
                doc._create_history_record('Archive Document', 'Auto archived', old_state, 'archived')
                archived_count += 1
            except Exception as e:
                _logger.warning(f"Failed to archive document {doc.id}: {str(e)}")
                continue
        
        _logger.info(f"Archived {archived_count} documents automatically")
        return archived_count

    @api.model
    def update_performance_metrics(self):
        """Update performance metrics"""

        total_docs = self.search_count([])
        pending_approvals = self.search_count([('has_pending_approvals', '=', True)])
        archived_docs = self.search_count(['|', ('workflow_state', '=', 'archived'), ('processing_state', '=', 'archived')])
        
        metrics = {
            'total_documents': total_docs,
            'pending_approvals': pending_approvals,
            'archived_documents': archived_docs,
            'last_update': fields.Datetime.now()
        }
        
        _logger.info(f"Updated performance metrics: {metrics}")
        

        return metrics

    @api.model
    def cleanup_temporary_data(self):
        """Cleanup temporary data"""

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
            ('workflow_state', '=', 'archived')
        ])
        
        if very_old_docs:
            deleted_count += len(very_old_docs)
            very_old_docs.unlink()
        
        _logger.info(f"Deleted {deleted_count} old records")
        return deleted_count


class DocumentKeyword(models.Model):
    """Document Keyword Model"""
    
    _name = 'document.keyword'
    _description = 'Document Keyword'
    _order = 'name'
    
    name = fields.Char(
        string='Keyword',
        required=True
    )
    
    description = fields.Text(
        string='Description'
    )
    
    color = fields.Integer(
        string='Color',
        default=0
    )
    
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Keyword must be unique!')
    ]


    
 
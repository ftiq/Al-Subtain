# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DocumentCategory(models.Model):
    """Document Category Model for Document Classification and Organization"""
    
    _name = 'document.category'
    _description = 'Document Categories'
    _inherit = ['mail.thread']
    _order = 'sequence, name'
    _parent_store = True
    _rec_name = 'complete_name'
    
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True
    )
    
    code = fields.Char(
        string='Code',
        help='Unique code for the category'
    )
    
    description = fields.Text(
        string='Description',
        tracking=True
    )
    
    is_active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order categories in lists'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color of the category in interfaces'
    )
    

    parent_id = fields.Many2one(
        'document.category',
        string='Parent Category',
        index=True,
        ondelete='cascade',
        tracking=True
    )
    
    parent_path = fields.Char(
        index=True
    )
    
    child_ids = fields.One2many(
        'document.category',
        'parent_id',
        string='Subcategories'
    )
    
    complete_name = fields.Char(
        string='Complete Name',
        compute='_compute_complete_name',
        recursive=True,
        store=True
    )
    

    allowed_document_types = fields.Char(
        string='Allowed Document Types',
        help='Document types allowed for this category (separated by commas)',
        tracking=True
    )
    
    specific_document_types = fields.Text(
        string='Specific Document Types',
        help='Specific document types allowed when "Specific" is selected (separated by commas)'
    )
    

    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count',
        store=True
    )
    

    allowed_department_ids = fields.Many2many(
        'hr.department',
        string='Allowed Departments',
        help='Departments allowed to use this category'
    )
    
    allowed_user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
        help='Users allowed to use this category'
    )
    
    is_public = fields.Boolean(
        string='Public',
        default=True,
        help='If enabled, all users can use this category'
    )
    
    @api.model
    def get_allowed_categories(self, user_id=None):
        """Get allowed categories for the user"""
        if not user_id:
            user_id = self.env.user.id
            
        user = self.env['res.users'].browse(user_id)
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        
        domain = ['|', ('is_public', '=', True)]
        

        auth_conditions = []
        if employee and employee.department_id:
            auth_conditions.append(('allowed_department_ids', 'in', [employee.department_id.id]))
        auth_conditions.append(('allowed_user_ids', 'in', [user_id]))
        
        if auth_conditions:
            domain.extend(['|'] * (len(auth_conditions) - 1))
            domain.extend(auth_conditions)
            
        return self.search(domain)
    
    def check_user_access(self, user_id=None):
        """Check user access to this category"""
        if not user_id:
            user_id = self.env.user.id
            
        if self.is_public:
            return True
            
        user = self.env['res.users'].browse(user_id)
        employee = self.env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
        

        if user_id in self.allowed_user_ids.ids:
            return True
            

        if employee and employee.department_id and employee.department_id.id in self.allowed_department_ids.ids:
            return True
            
        return False
    

    auto_archive_enabled = fields.Boolean(
        string='Enable Auto Archiving',
        default=False,
        help='Enable auto archiving for documents in this category'
    )
    
    auto_archive_days = fields.Integer(
        string='Auto Archive Days',
        default=365,
        help='Number of days before auto archiving'
    )
    
    archive_condition = fields.Selection([
        ('after_approval', 'After Approval'),
        ('after_days', 'After a specific number of days'),
        ('manual', 'Manual only')
    ], string='Archive Condition', default='after_days')
    
    notify_before_archive = fields.Boolean(
        string='Notify before archiving',
        default=False,
        help='Notify before archiving documents')
    
    notification_days = fields.Integer(
        string='Notification Days',
        default=7,
        help='Number of days before archiving to notify')
    
    default_priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Default Priority', default='normal')
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='Does this category require approval?'
    )
    

    default_sla_hours = fields.Float(
        string='Default SLA Hours',
        default=72.0,
        help='Default SLA hours for documents in this category'
    )
    
    priority_sla_hours = fields.Json(
        string='SLA Hours by Priority',
        default=lambda self: {
            '0': 168,  
            '1': 72,   
            '2': 24,   
            '3': 4     
        },
        help='SLA hours by priority'
    )
    
    department_sla_hours = fields.Json(
        string='Department SLA Hours',
        default=lambda self: {},
        help='Department-specific SLA hours (department_id: hours)'
    )
    
    escalation_enabled = fields.Boolean(
        string='Enable Escalation',
        default=True,
        help='Enable automatic escalation when SLA is exceeded'
    )
    
    escalation_percentage = fields.Float(
        string='Escalation Percentage',
        default=80.0,
        help='Percentage of time spent before escalation'
    )
    
    notification_schedule = fields.Json(
        string='Notification Schedule',
        default=lambda self: {
            'first_reminder': 50,    
            'second_reminder': 75,   
            'final_warning': 90      
        },
        help='Notification schedule'
    )
    
    working_hours_only = fields.Boolean(
        string='Working Hours Only',
        default=True,
        help='Account SLA in working hours only (excluding weekends)'
    )
    
    allowed_group_ids = fields.Many2many(
        'res.groups',
        string='Allowed Groups',
        help='Groups that can use this category'
    )
    
    active_document_count = fields.Integer(
        string='Active Document Count',
        compute='_compute_document_counts',
        store=True
    )
    
    archived_document_count = fields.Integer(
        string='Archived Document Count',
        compute='_compute_document_counts',
        store=True
    )
    

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        """Compute the complete name of the category"""
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name
    
    @api.depends('document_ids', 'document_ids.state', 'document_type_ids', 'document_type_ids.state')
    def _compute_document_count(self):
        """Compute the document count for the category"""
        for category in self:

            category.document_count = len(category.document_ids) + len(category.document_type_ids)
    
    @api.depends('document_ids', 'document_ids.state', 'document_type_ids', 'document_type_ids.state')
    def _compute_document_counts(self):
        """Compute the active and archived document counts for the category"""
        for category in self:
            all_docs = category.document_ids + category.document_type_ids
            category.active_document_count = len(all_docs.filtered(lambda d: d.state != 'archived'))
            category.archived_document_count = len(all_docs.filtered(lambda d: d.state == 'archived'))
    

    document_ids = fields.One2many(
        'document.document',
        'category_id',
        string='Documents'
    )
    
    document_type_ids = fields.One2many(
        'document.document',
        'document_type_id',
        string='Documents of this type'
    )
    

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """Check for recursion in the hierarchy"""
        for record in self:
            if record.parent_id:
                if not record._check_recursion():
                    raise ValidationError(_('Cannot create a subcategory of itself'))
    
    @api.constrains('auto_archive_days')
    def _check_auto_archive_days(self):
        """Check the validity of the number of archive days"""
        for category in self:
            if category.auto_archive_enabled and category.auto_archive_days < 1:
                raise ValidationError(_('The number of archive days must be greater than zero'))
    
    def get_sla_hours(self, priority='1', department_id=None):
        """Calculate SLA duration based on priority and department"""
        self.ensure_one()
        
        if department_id and self.department_sla_hours:
            dept_hours = self.department_sla_hours.get(str(department_id))
            if dept_hours:
                return float(dept_hours)
        
        if self.priority_sla_hours:
            priority_hours = self.priority_sla_hours.get(str(priority))
            if priority_hours:
                return float(priority_hours)
        
        return self.default_sla_hours or 72.0
    
    def calculate_due_date(self, start_date, priority='1', department_id=None):

        self.ensure_one()
        
        if not start_date:
            start_date = fields.Datetime.now()
        
        sla_hours = self.get_sla_hours(priority, department_id)
        
        if self.working_hours_only:
            working_days_needed = sla_hours / 8.0
            due_date = self._add_working_days(start_date, working_days_needed)
        else:
            due_date = start_date + timedelta(hours=sla_hours)
        
        return due_date
    
    def _add_working_days(self, start_date, working_days):

        current_date = start_date
        days_added = 0
        
        while days_added < working_days:
            current_date += timedelta(days=1)

            if current_date.weekday() < 5: 
                days_added += 1
        
        return current_date
    
    def get_escalation_date(self, start_date, priority='1', department_id=None):
        self.ensure_one()
        
        if not self.escalation_enabled:
            return False
        
        due_date = self.calculate_due_date(start_date, priority, department_id)
        total_duration = due_date - start_date
        escalation_duration = total_duration * (self.escalation_percentage / 100.0)
        
        return start_date + escalation_duration
    
    def get_notification_dates(self, start_date, priority='1', department_id=None):
        
        self.ensure_one()
        
        if not self.notification_schedule:
            return {}
        
        due_date = self.calculate_due_date(start_date, priority, department_id)
        total_duration = due_date - start_date
        
        notification_dates = {}
        for reminder_type, percentage in self.notification_schedule.items():
            reminder_duration = total_duration * (percentage / 100.0)
            notification_dates[reminder_type] = start_date + reminder_duration
        
        return notification_dates
    

    @api.model_create_multi
    def create(self, vals_list):
        """Create a new category"""
        categories = super().create(vals_list)
        return categories
    
    def write(self, vals):
        """Update the category"""

        if 'color' in vals and vals['color']:
            color_value = vals['color']
            if isinstance(color_value, str):
                if color_value.startswith('#'):
                    try:
                        vals['color'] = int(color_value[1:], 16)
                    except ValueError:
                        vals['color'] = 0
                else:
                    try:
                        vals['color'] = int(color_value)
                    except ValueError:
                        vals['color'] = 0
        
        result = super().write(vals)
        
        if 'parent_id' in vals:
            self._compute_complete_name()
        
        return result
    
    def unlink(self):
        """Delete the category with document check"""
        for category in self:
            total_docs = len(category.document_ids) + len(category.document_type_ids)
            if total_docs > 0:
                raise ValidationError(
                    _('Cannot delete category "%s" as it contains %d documents') % 
                    (category.name, total_docs)
                )
        
        return super().unlink()
    

    def action_view_documents(self):
        """View documents of the category"""
        return {
            'name': _('Documents of category: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'document.document',
            'view_mode': 'list,kanban,form',
            'domain': ['|', ('category_id', 'child_of', self.ids), ('document_type_id', 'child_of', self.ids)],
            'context': {
                'default_category_id': self.id,
                'search_default_category_id': self.id,
            }
        }
    
    def action_archive_documents(self):
        """Archive all documents of the category"""
        documents = self.env['document.document'].search([
            '|', 
            ('category_id', 'child_of', self.ids),
            ('document_type_id', 'child_of', self.ids),
            ('state', 'in', ['approved', 'rejected'])
        ])
        
        if documents:
            documents.action_archive()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Archived %d documents') % len(documents),
                    'type': 'success',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No documents found to archive in this category'),
                    'type': 'warning',
                }
            }
    

    def get_allowed_document_types(self):
        """Get the allowed document types for the category"""
        if not self.allowed_document_types:
            return []
        
        types = [t.strip() for t in self.allowed_document_types.split(',') if t.strip()]
        return types
    
    def is_accessible_by_user(self, user=None):
        """Check if the user has access to the category"""
        if not user:
            user = self.env.user
        
        if self.is_public:
            return True
        
        if user in self.allowed_user_ids:
            return True
        
        if user.employee_id and user.employee_id.department_id in self.allowed_department_ids:
            return True
        
        return False
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'The category code must be unique'),
        ('archive_days_positive', 'CHECK(auto_archive_days > 0)', 'The number of archive days must be greater than zero'),
    ]
    
    def calculate_sla_deadline(self, priority='1', department_id=None, document_type='incoming', user_id=None, company_id=None):

        self.ensure_one()
        
        sla_hours = self.get_sla_hours(priority, department_id)
        
        multiplier = 1.0
        
        if self.document_type_multipliers:
            type_multiplier = self.document_type_multipliers.get(document_type, 1.0)
            multiplier *= type_multiplier
        
        if self.consider_working_hours:
           
            company = self.env['res.company'].browse(company_id) if company_id else self.env.company
            work_hours_per_day = self._get_work_hours_per_day(company)
            
            work_days = sla_hours / work_hours_per_day if work_hours_per_day > 0 else sla_hours / 8
            
            deadline = self._calculate_business_deadline(work_days, company)
            
        else:
            adjusted_hours = sla_hours * multiplier
            deadline = fields.Datetime.now() + timedelta(hours=adjusted_hours)
        
        return deadline
    
    def _get_work_hours_per_day(self, company):
        """Compute the number of working hours per day"""
        try:
            if hasattr(company, 'resource_calendar_id') and company.resource_calendar_id:
                calendar = company.resource_calendar_id

                total_hours = sum(attendance.hour_to - attendance.hour_from 
                                for attendance in calendar.attendance_ids 
                                if not attendance.date_from)
                working_days = len(set(calendar.attendance_ids.mapped('dayofweek')))
                return total_hours / working_days if working_days > 0 else 8.0
        except Exception:
            pass
        return 8.0 
    
    def _calculate_business_deadline(self, work_days, company):
        """Calculate final deadline based on working days"""
        start_date = fields.Datetime.now()
        
        try:
            if hasattr(company, 'resource_calendar_id') and company.resource_calendar_id:
                calendar = company.resource_calendar_id
                
                end_date = calendar.plan_hours(
                    work_days * self._get_work_hours_per_day(company),
                    start_date
                )
                return end_date
        except Exception:
            pass
        
        
        current_date = start_date
        days_added = 0
        
        while days_added < work_days:
            current_date += timedelta(days=1)
            
            if current_date.weekday() not in [4, 5]: 
                days_added += 1
        
        return current_date
    
    @api.model
    def get_sla_recommendations(self, document_data):
        """Give SLA recommendations based on document data"""
        category_id = document_data.get('category_id')
        priority = document_data.get('priority', '1')
        department_id = document_data.get('department_id')
        document_type = document_data.get('document_type', 'incoming')
        
        if not category_id:
            return {
                'recommended_hours': 72,
                'deadline': fields.Datetime.now() + timedelta(hours=72),
                'confidence': 'low',
                'reason': 'Category not specified'
            }
        
        category = self.browse(category_id)
        
        recommended_hours = category.get_sla_hours(priority, department_id)
        deadline = category.calculate_sla_deadline(
            priority=priority,
            department_id=department_id,
            document_type=document_type
        )
        
        confidence = 'high'
        reason = 'SLA calculated based on category settings'
        
        if not category.priority_sla_hours:
            confidence = 'medium'
            reason = 'Default SLA used for the category'
        
        return {
            'recommended_hours': recommended_hours,
            'deadline': deadline,
            'confidence': confidence,
            'reason': reason,
            'category_name': category.name
        } 
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError
from datetime import timedelta
import logging


_logger = logging.getLogger(__name__)


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = 'فئة الموافقات الداخلية'
    _order = 'sequence, id'

    name = fields.Char(string='الاسم', required=True, index=True)
    description = fields.Text(string='الوصف')
    approver = fields.Many2one(
        'hr.employee',
        string='الموافق الرئيسي',
        help='موظف افتراضي كموافق رئيسي لهذه الفئة (للتوافق مع إضافات أخرى)'
    )
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        default=lambda self: self.env.company,
        help='الشركة المرتبطة بهذه الفئة'
    )
    automated_sequence = fields.Boolean(
        string='تسلسل تلقائي',
        default=True,
        help='تمكين إنشاء تسلسل تلقائي للفئة (حقل للتوافق مع بيانات XML)'
    )
    sequence_code = fields.Char(
        string='رمز التسلسل',
        help='رمز تسلسل للفئة (حقل للتوافق مع بيانات XML)'
    )
    approval_type = fields.Selection([
        ('content_review', 'مراجعة المحتوى'),
        ('legal_review', 'مراجعة قانونية'),
        ('financial_approval', 'موافقة مالية'),
        ('publication_approval', 'موافقة النشر'),
        ('archiving_approval', 'موافقة الأرشفة'),
        ('access_permission', 'إذن الوصول'),
        ('signature_authority', 'صلاحية التوقيع'),
        ('security_clearance', 'تصريح أمني')
    ], string='نوع الموافقة', help='تصنيف نوع الموافقة لهذه الفئة')
    manager_approval = fields.Selection([
        ('approver', 'حسب الموافق'),
        ('required', 'مطلوبة')
    ], string='موافقة المدير', default='approver')
    approver_sequence = fields.Selection([
        ('unordered', 'بدون ترتيب'),
        ('ordered', 'متسلسلة')
    ], string='ترتيب الموافقين', default='unordered')
    sequence = fields.Integer(string='الترتيب', default=10)


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'طلب موافقة داخلي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='الموضوع', required=True, tracking=True)
    category_id = fields.Many2one('approval.category', string='الفئة', tracking=True)
    request_owner_id = fields.Many2one('res.users', string='طالب الموافقة', default=lambda self: self.env.user, tracking=True)
    date_start = fields.Datetime(string='تاريخ الطلب', default=fields.Datetime.now, tracking=True)
    reason = fields.Text(string='السبب/التفاصيل')

    document_id = fields.Many2one('document.document', string='الوثيقة المرتبطة', ondelete='cascade', index=True)

    request_status = fields.Selection([
        ('new', 'جديد'),
        ('pending', 'قيد الموافقة'),
        ('under_approval', 'تحت الاعتماد'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('cancelled', 'ملغى'),
    ], string='الحالة', default='pending', tracking=True)

    approver_ids = fields.One2many('approval.approver', 'request_id', string='الموافقون')


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

    department_id = fields.Many2one('hr.department', string='القسم المختص', tracking=True,
                                    default=lambda self: self.env.user.employee_id.department_id.id if self.env.user.employee_id else False)

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

    expected_response_date = fields.Datetime(string='تاريخ الرد المتوقع')
    date_confirmed = fields.Datetime(string='تاريخ الاعتماد')
    location = fields.Char(string='الموقع', help='موقع الاجتماع أو المعالجة (للتوافق مع العروض)')

    date_end = fields.Datetime(string='تاريخ الانتهاء', related='expected_response_date', store=False)
    
    
    requester_id = fields.Many2one('hr.employee', string='طالب الموافقة', related='request_owner_id.employee_id', store=False)
    approver_id = fields.Many2one('hr.employee', string='الموافق الأول', compute='_compute_first_approver', store=False)
    auto_escalation = fields.Boolean(string='التصعيد التلقائي', default=True)
    escalation_period = fields.Integer(string='فترة التصعيد (ساعات)', default=24)

    is_overdue = fields.Boolean(string='متأخر', compute='_compute_is_overdue', store=False)
    days_since_request = fields.Integer(string='أيام منذ الطلب', compute='_compute_days_since_request', store=False)
    approval_chain_progress = fields.Float(string='تقدم سلسلة الموافقة (%)', compute='_compute_approval_chain_progress', store=False)
    next_approver_info = fields.Char(string='الموافق التالي', compute='_compute_next_approver_info', store=False)

    related_documents = fields.Many2many('document.document', 'approval_document_rel', 'approval_id', 'document_id', string='وثائق ذات صلة')
    related_task_ids = fields.One2many('admin.task', 'approval_request_id', string='المهام المرتبطة')
    tasks_count = fields.Integer(string='عدد المهام', compute='_compute_tasks_count')
    
    is_my_turn = fields.Boolean(string='دوري للموافقة', compute='_compute_is_my_turn')

    ai_recommended_approvers = fields.Text(string='الموافقون المقترحون')
    risk_assessment = fields.Selection([
        ('low', 'مخاطر منخفضة'),
        ('medium', 'مخاطر متوسطة'),
        ('high', 'مخاطر عالية'),
        ('critical', 'مخاطر حرجة')
    ], string='تقييم المخاطر', compute='_compute_risk_assessment', store=False)
    complexity_score = fields.Float(string='درجة التعقيد', compute='_compute_complexity_score', store=False)

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(
            f"[APPROVAL][create][start] user=%s count=%s docs=%s",
            self.env.user.login,
            len(vals_list),
            [v.get('document_id') for v in vals_list]
        )
        for vals in vals_list:
            if not vals.get('name'):
                seq = self.env['ir.sequence'].next_by_code('approval.request') or _('طلب موافقة')
                vals['name'] = seq

            vals.setdefault('request_status', 'pending')
        try:
            requests = super().create(vals_list)
        except AccessError as ae:
            _logger.error(
                f"[APPROVAL][create][access_error] user=%s groups user=%s proc=%s appr=%s mgr=%s err=%s",
                self.env.user.login,
                self.env.user.has_group('mgt_documents.group_doc_contributor'),
                self.env.user.has_group('mgt_documents.group_doc_contributor'),
                self.env.user.has_group('mgt_documents.group_doc_approver'),
                self.env.user.has_group('mgt_documents.group_doc_manager'),
                str(ae)
            )
            raise
        except Exception as e:
            _logger.exception(f"[APPROVAL][create][error] err=%s", str(e))
            raise
        _logger.info(f"[APPROVAL][create][ok] ids=%s", requests.ids)
        return requests

    @api.model
    def default_get(self, fields_list):
        """ملء الموافقين تلقائياً عند فتح نموذج طلب الموافقة من زر الوثيقة.
        - يعتمد على default_request_owner_id / default_department_id / default_document_id من السياق.
        - يضيف مدير القسم أولاً ثم سلسلة المديرين للموظف المالك (أو مرسل الوثيقة) بدون تكرار.
        """
        res = super().default_get(fields_list)
        try:
            ctx = dict(self.env.context or {})
            # إن كان هناك موافقون محددون مسبقاً فلا نتدخل
            if res.get('approver_ids'):
                return res

            users = []
            seen = set()

            # مدير القسم أولاً
            dept_id = ctx.get('default_department_id')
            if dept_id:
                dept = self.env['hr.department'].browse(dept_id)
                if dept and dept.manager_id and dept.manager_id.user_id:
                    u = dept.manager_id.user_id
                    if u.id not in seen:
                        users.append(u)
                        seen.add(u.id)

            # موافق مقترح (موظف) من سياق الوثيقة إن وُجد
            sugg_emp_id = ctx.get('suggested_approver_id')
            if sugg_emp_id:
                emp = self.env['hr.employee'].browse(sugg_emp_id)
                if emp and emp.user_id and emp.user_id.id not in seen:
                    users.append(emp.user_id)
                    seen.add(emp.user_id.id)

            # سلسلة المديرين starting from owner employee أو مرسل الوثيقة
            employee = None
            owner_uid = ctx.get('default_request_owner_id') or self.env.user.id
            if owner_uid:
                owner = self.env['res.users'].browse(owner_uid)
                employee = owner.employee_id if owner else None
            if not employee:
                doc_id = ctx.get('default_document_id')
                if doc_id:
                    doc = self.env['document.document'].browse(doc_id)
                    if doc and getattr(doc, 'sender_employee_id', False):
                        employee = doc.sender_employee_id

            level = 0
            max_levels = 7
            current = employee
            while current and current.parent_id and level < max_levels:
                manager = current.parent_id
                if manager.user_id and manager.user_id.id not in seen:
                    users.append(manager.user_id)
                    seen.add(manager.user_id.id)
                current = manager
                level += 1

            if users:
                seq = 10
                commands = []
                for u in users:
                    commands.append((0, 0, {
                        'user_id': u.id,
                        'employee_id': u.employee_id.id if u.employee_id else False,
                        'sequence': seq,
                        'status': 'new',
                    }))
                    seq += 10
                res['approver_ids'] = commands
                # ضمن التوافق، تأكد أن الحالة مبدئياً pending
                if 'request_status' in fields_list and not res.get('request_status'):
                    res['request_status'] = 'pending'
        except Exception as e:
            _logger.warning('[APPROVAL][default_get][skip] err=%s', str(e))
        return res

    @api.depends('approver_ids')
    def _compute_first_approver(self):
        """حساب أول موافق للتوافق مع قوالب البريد"""
        for rec in self:
            first_approver = rec.approver_ids.sorted('sequence')[:1]
            rec.approver_id = first_approver.employee_id if first_approver else False
    
    @api.depends('expected_response_date', 'request_status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.expected_response_date and rec.expected_response_date < now and rec.request_status in ['new', 'pending', 'under_approval'])

    @api.depends('create_date')
    def _compute_days_since_request(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.create_date:
                rec.days_since_request = (now - rec.create_date).days
            else:
                rec.days_since_request = 0

    @api.depends('approver_ids.status')
    def _compute_approval_chain_progress(self):
        for rec in self:
            total = len(rec.approver_ids)
            approved = len(rec.approver_ids.filtered(lambda a: a.status == 'approved'))
            rec.approval_chain_progress = (approved / total) * 100 if total else 0.0

    @api.depends('approver_ids.status', 'approver_ids.sequence')
    def _compute_next_approver_info(self):
        for rec in self:
            pending = rec.approver_ids.filtered(lambda a: a.status in ['new', 'pending']).sorted('sequence')
            if pending:
                rec.next_approver_info = _('الموافق التالي: %s') % (pending[0].user_id.name or '')
            else:
                rec.next_approver_info = _('اكتملت الموافقات')

    @api.depends('approver_ids.status', 'approver_ids.user_id', 'approver_ids.sequence')
    def _compute_is_my_turn(self):
        uid = self.env.user.id
        for rec in self:
            turn = False
            my_lines = rec.approver_ids.filtered(lambda a: a.user_id.id == uid and a.status in ['new', 'pending'])
            for line in my_lines:
                previous = rec.approver_ids.filtered(lambda a: (a.sequence or 0) < (line.sequence or 0))
                if all(l.status == 'approved' for l in previous):
                    turn = True
                    break
            rec.is_my_turn = turn

    @api.depends('related_task_ids')
    def _compute_tasks_count(self):
        for rec in self:
            rec.tasks_count = len(rec.related_task_ids)


    def _get_my_pending_line(self):
        self.ensure_one()
        uid = self.env.user.id
        
        candidates = self.approver_ids.filtered(lambda a: a.user_id.id == uid and a.status in ['new', 'pending']).sorted('sequence')
        for line in candidates:
            previous = self.approver_ids.filtered(lambda a: (a.sequence or 0) < (line.sequence or 0))
            if all(l.status == 'approved' for l in previous):
                return line
        return False

    def action_open_my_approve_wizard(self):
        self.ensure_one()
        line = self._get_my_pending_line()
        if not line:
            raise UserError(_('لا يوجد دور موافقة لك حالياً'))
        _logger.info(
            f"[APPROVAL][open_my_wizard] req=%s line=%s user=%s",
            self.id, line.id, self.env.user.login
        )
        # فتح معالج الموافقة مع التعيين وفق الدليل
        return {
            'type': 'ir.actions.act_window',
            'name': _('تعيين مهمة بعد الموافقة'),
            'res_model': 'approval.task.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approver_id': line.id,
                'default_request_id': self.id,
                'default_document_id': self.document_id.id if self.document_id else False,
            }
        }

    def action_my_refuse(self):
        self.ensure_one()
        line = self._get_my_pending_line()
        if not line:
            raise UserError(_('لا يوجد دور موافقة لك حالياً'))
        line.write({'status': 'refused', 'approval_date': fields.Datetime.now()})
        self.write({'request_status': 'rejected'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('تم رفض الطلب.'),
                'type': 'warning',
                'sticky': False,
            }
        }

    @api.depends('urgency_level', 'confidentiality_level', 'approval_type_detailed')
    def _compute_risk_assessment(self):
        for rec in self:
            urgency_risk = {'normal': 1, 'urgent': 2, 'very_urgent': 3, 'critical': 4}.get(rec.urgency_level, 1)
            conf_risk = {'public': 1, 'internal': 2, 'confidential': 3, 'top_secret': 4}.get(rec.confidentiality_level, 1)
            type_risk = {
                'content_review': 1, 'legal_review': 3, 'financial_approval': 3, 'publication_approval': 2,
                'archiving_approval': 1, 'access_permission': 2, 'signature_authority': 4, 'security_clearance': 4
            }.get(rec.approval_type_detailed, 2)
            avg = (urgency_risk + conf_risk + type_risk) / 3
            rec.risk_assessment = 'low' if avg <= 1.5 else 'medium' if avg <= 2.5 else 'high' if avg <= 3.5 else 'critical'

    @api.depends('approver_ids', 'urgency_level', 'confidentiality_level')
    def _compute_complexity_score(self):
        for rec in self:
            complexity = 0
            complexity += len(rec.approver_ids) * 0.5
            complexity += {'normal': 1, 'urgent': 2, 'very_urgent': 3, 'critical': 4}.get(rec.urgency_level, 1)
            complexity += {'public': 1, 'internal': 2, 'confidential': 3, 'top_secret': 4}.get(rec.confidentiality_level, 1)
            rec.complexity_score = min(max(complexity, 1), 10)

    def action_smart_assign_approvers(self):
        for rec in self:
            _logger.info(
                f"[APPROVAL][smart_assign][start] req=%s dept=%s doc=%s",
                rec.id,
                rec.department_id.display_name if rec.department_id else None,
                rec.document_id.id if rec.document_id else None,
            )
            suggested = []
            if rec.department_id and rec.department_id.manager_id and rec.department_id.manager_id.user_id:
                suggested.append(rec.department_id.manager_id.user_id)
            doc_type = rec.document_id.document_type if rec.document_id else False
            if doc_type in ['contract', 'financial']:
                finance_dept = self.env['hr.department'].search([('name', 'ilike', 'مالي')], limit=1)
                if finance_dept and finance_dept.manager_id and finance_dept.manager_id.user_id:
                    suggested.append(finance_dept.manager_id.user_id)

            seen = set()
            sequence = 10
            created = 0
            for user in suggested:
                if user and user.id not in seen:
                    seen.add(user.id)
                    self.env['approval.approver'].create({
                        'request_id': rec.id,
                        'user_id': user.id,
                        'employee_id': user.employee_id.id if user.employee_id else False,
                        'sequence': sequence,
                        'status': 'new'
                    })
                    sequence += 10
                    created += 1
            _logger.info(
                f"[APPROVAL][smart_assign][done] req=%s created=%s users=%s",
                rec.id, created, list(seen)
            )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('تم تعيين الموافقين بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _get_hierarchy_users(self, max_levels=5):
        """إرجاع قائمة مستخدمين تمثل سلسلة المديرين حسب هيكل HR للموظف مالك الطلب.
        - تبدأ من مدير الموظف ثم تصعد للأعلى حتى max_levels أو القمة.
        - تتجنب التكرارات، وتستبعد الموظفين بلا مستخدم.
        - تُدرِج مدير القسم إن كان موجوداً وغير مكرر في بداية السلسلة.
        """
        self.ensure_one()
        users = []
        seen = set()

        # تحديد الموظف الأساس
        employee = self.request_owner_id.employee_id if self.request_owner_id else False
        if not employee and self.document_id and hasattr(self.document_id, 'sender_employee_id'):
            employee = self.document_id.sender_employee_id

        # إدراج مدير القسم أولاً (إن وُجد)
        if self.department_id and self.department_id.manager_id and self.department_id.manager_id.user_id:
            dept_user = self.department_id.manager_id.user_id
            if dept_user.id not in seen:
                users.append(dept_user)
                seen.add(dept_user.id)

        # الصعود في سلسلة المديرين
        level = 0
        current = employee
        while current and current.parent_id and level < max_levels:
            manager = current.parent_id
            if manager.user_id and manager.user_id.id not in seen:
                users.append(manager.user_id)
                seen.add(manager.user_id.id)
            current = manager
            level += 1

        return users

    def action_assign_hierarchical_approvers(self):
        """إضافة سلسلة الموافقين تلقائياً حسب الهيكلية الوظيفية في الموارد البشرية.
        - تُضاف السلسلة إلى الموجود بدون تكرار.
        - تُرتَّب بالsequence 10,20,30...
        - تُحدَّث حالة الطلب إلى 'pending' إذا كانت 'new'.
        """
        for rec in self:
            try:
                users_chain = rec._get_hierarchy_users(max_levels=7)
                if not users_chain:
                    continue
                existing_user_ids = set(rec.approver_ids.mapped('user_id').ids)
                seq = (max(rec.approver_ids.mapped('sequence') or [0]) // 10) * 10 + 10
                created = 0
                for user in users_chain:
                    if user.id in existing_user_ids:
                        continue
                    rec.env['approval.approver'].create({
                        'request_id': rec.id,
                        'user_id': user.id,
                        'employee_id': user.employee_id.id if user.employee_id else False,
                        'sequence': seq,
                        'status': 'new',
                    })
                    seq += 10
                    created += 1

                if created and rec.request_status == 'new':
                    rec.request_status = 'pending'

                if created:
                    rec.message_post(body=_('تم إنشاء سلسلة موافقات هرمية تلقائياً (%s عنصر).') % created,
                                     message_type='notification', subtype_xmlid='mail.mt_note')
            except Exception as e:
                _logger.exception('[APPROVAL][hierarchy_assign][error] req=%s err=%s', rec.id, str(e))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('تمت إضافة سلسلة الموافقات الهرمية'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_escalate_approval(self):
        for rec in self:
            current = rec.approver_ids.filtered(lambda a: a.status == 'pending')
            for approver in current:
                emp = approver.user_id.employee_id
                if emp and emp.parent_id and emp.parent_id.user_id:
                    manager_user = emp.parent_id.user_id
                    self.env['approval.approver'].create({
                        'request_id': rec.id,
                        'user_id': manager_user.id,
                        'employee_id': manager_user.employee_id.id if manager_user.employee_id else False,
                        'sequence': (approver.sequence or 0) + 5,
                        'status': 'new'
                    })
                    rec.message_post(body=_('تم تصعيد الموافقة إلى %s') % manager_user.name, message_type='notification', subtype_xmlid='mail.mt_note')

    def action_view_document(self):
        self.ensure_one()
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

    @api.constrains('escalation_period')
    def _check_escalation_period(self):
        for rec in self:
            if rec.escalation_period and rec.escalation_period < 1:
                raise ValidationError(_('فترة التصعيد يجب أن تكون ساعة واحدة على الأقل'))

    @api.model
    def _cron_auto_escalate_overdue_approvals(self):
        overdue = self.search([('request_status', '=', 'pending'), ('auto_escalation', '=', True), ('is_overdue', '=', True)])
        for appr in overdue:
            try:
                appr.action_escalate_approval()
                appr.message_post(body=_('تم التصعيد التلقائي بسبب تجاوز الوقت المحدد'), message_type='notification')
            except Exception:
                continue

    @api.model
    def _cron_send_approval_reminders(self):
        pending = self.search([('request_status', '=', 'pending'), ('create_date', '<=', fields.Datetime.now() - timedelta(hours=12))])
        for appr in pending:
            pass  # بعدين راح اضيفة


class ApprovalApprover(models.Model):
    _name = 'approval.approver'
    _description = 'موافق داخلي'
    _order = 'sequence, id'

    request_id = fields.Many2one('approval.request', string='طلب الموافقة', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='المستخدم', required=True, index=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف')
    status = fields.Selection([
        ('new', 'جديد'),
        ('pending', 'قيد الانتظار'),
        ('approved', 'معتمد'),
        ('refused', 'مرفوض')
    ], string='الحالة', default='pending')
    sequence = fields.Integer(string='الترتيب', default=10)
    comment = fields.Text(string='ملاحظات الموافقة')
    approval_date = fields.Datetime(string='تاريخ الموافقة', readonly=True)
    expected_approval_date = fields.Datetime(string='تاريخ الموافقة المتوقع')
    is_overdue = fields.Boolean(string='متأخر', compute='_compute_is_overdue', store=False)

    @api.depends('expected_approval_date', 'status')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = bool(rec.expected_approval_date and rec.expected_approval_date < now and rec.status in ['new', 'pending'])

    def action_approve(self):
        self.ensure_one()
        _logger.info(
            f"[APPROVER][approve_click] line=%s req=%s user=%s",
            self.id, self.request_id.id if self.request_id else None, self.env.user.login
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('تعيين مهمة بعد الموافقة'),
            'res_model': 'approval.task.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_approver_id': self.id,
                'default_request_id': self.request_id.id,
                'default_document_id': self.request_id.document_id.id if self.request_id.document_id else False,
            }
        }

    def action_approve_final(self):
        self.ensure_one()
        _logger.info(
            f"[APPROVER][approve_final] line=%s req=%s user=%s",
            self.id, self.request_id.id if self.request_id else None, self.env.user.login
        )
        self.write({'status': 'approved', 'approval_date': fields.Datetime.now()})

        req = self.request_id
        if req and not req.approver_ids.filtered(lambda a: a.status not in ['approved']):
            req.write({'request_status': 'approved', 'date_confirmed': fields.Datetime.now()})
            # Upon full approval, attempt to mark the linked document as approved
            try:
                if req.document_id:
                    # Prefer the document's own approval action to keep history/tasks consistent
                    if hasattr(req.document_id, 'action_approve'):
                        try:
                            req.document_id.action_approve()
                        except Exception:
                            # Fallback: set states directly if constraints block action
                            req.document_id.write({
                                'processing_state': 'approved',
                                'approved_date': fields.Datetime.now(),
                                'approved_by': self.env.user.id,
                            })
            except Exception as e:
                _logger.warning('[APPROVER][approve_final][doc_sync_warn] req=%s doc=%s err=%s', req.id, getattr(req.document_id, 'id', False), str(e))
        return True

    def action_refuse(self):
        self.ensure_one()
        _logger.info(
            f"[APPROVER][refuse] line=%s req=%s user=%s",
            self.id, self.request_id.id if self.request_id else None, self.env.user.login
        )
        self.write({'status': 'refused', 'approval_date': fields.Datetime.now()})
        if self.request_id:
            self.request_id.write({'request_status': 'rejected'})
            # Reflect refusal on the linked document
            try:
                if self.request_id.document_id:
                    if hasattr(self.request_id.document_id, 'action_reject'):
                        try:
                            self.request_id.document_id.action_reject()
                        except Exception:
                            self.request_id.document_id.write({
                                'processing_state': 'rejected',
                            })
            except Exception as e:
                _logger.warning('[APPROVER][refuse][doc_sync_warn] req=%s doc=%s err=%s', self.request_id.id, getattr(self.request_id.document_id, 'id', False), str(e))
        return True

# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import logging
import time
from odoo import tools

_logger = logging.getLogger(__name__)


class LabResultSet(models.Model):
    """مجموعة نتائج الفحص - تجميع كل النتائج المتعلقة بطلب فحص واحد"""
    _name = 'lab.result.set'
    _description = 'مجموعة نتائج الفحص'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'



    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )
    

    _sql_constraints = [

        ('sample_template_unique_non_concrete', 
         'unique(sample_id, template_id) WHERE (is_concrete_sample IS FALSE OR is_concrete_sample IS NULL)', 
         'لا يمكن إنشاء أكثر من مجموعة نتائج واحدة لنفس العينة والقالب (باستثناء عينات الخرسانة)!'),
        ('positive_samples', 
         'check(number_of_samples > 0)', 
         'عدد العينات يجب أن يكون أكبر من الصفر!'),

        ('concrete_groups_unique',
         'unique(sample_id, template_id, concrete_group_no, concrete_age_days) WHERE is_concrete_sample IS TRUE',
         'لا يمكن تكرار نفس مجموعة الخرسانة في نفس العينة!'),
    ]

    name = fields.Char(
        string='رقم مجموعة النتائج',
        required=True,
        copy=False,
        default=lambda self: _('جديد'),
        tracking=True
    )
    
    sample_id = fields.Many2one(
        'lab.sample',
        string='العينة',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True 
    )
    
    template_id = fields.Many2one(
        'lab.test.template',
        string='قالب الفحص',
        required=True,
        ondelete='restrict',
        tracking=True,
        index=True  
    )
    
    number_of_samples = fields.Integer(
        string='عدد العينات',
        default=1,
        required=True,
        help='عدد العينات الفردية المفحوصة (مثل: 10 حبات طابوق)'
    )
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد التنفيذ'),
        ('calculated', 'تم الحساب'),
        ('review', 'قيد المراجعة'),
        ('approved', 'معتمد'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغية')
    ], string='الحالة', default='draft', tracking=True, index=True) 
    
    start_date = fields.Datetime(
        string='تاريخ البدء',
        tracking=True
    )
    

    concrete_group_no = fields.Integer(
        string='رقم مجموعة الخرسانة',
        default=0,
        help='رقم المجموعة إذا كانت عينة خرسانة'
    )
    
    concrete_age_days = fields.Selection([
        ('7', '7 أيام'),
        ('28', '28 يوم'),
        ('reserve', 'احتياط')
    ], string='عمر الخرسانة',
       help='عمر عينة الخرسانة بالأيام عند الفحص')
    
    concrete_field_code = fields.Char(
        string='الرمز المختبري',
        help='الرمز المختبري لعينة الخرسانة'
    )
    
    concrete_field_serial = fields.Char(
        string='الرمز الحقلي',
        help='الرمز الحقلي لعينة الخرسانة'
    )
    
    is_concrete_sample = fields.Boolean(
        string='عينة خرسانة',
        default=False,
        help='هل هذه عينة خرسانة؟'
    )
    

    is_concrete_core = fields.Boolean(
        string='كور خرساني',
        compute='_compute_is_concrete_core',
        store=True,
        help='مؤشر يفيد بأن نوع العينة هو كور خرساني'
    )
    
    testing_temperature = fields.Float(
        string='درجة حرارة الفحص (°C)',
        help='درجة الحرارة أثناء إجراء الفحص بالدرجة المئوية',
        default=31.0,
        digits=(5, 2)
    )
    
    uncertainty_stress_value = fields.Float(
        string='قيمة عدم التأكد في الإجهاد',
        help='قيمة عدم التأكد في قياس مقاومة الانضغاط حسب المعايير الدولية',
        digits=(5, 3)
    )
    
    casting_date = fields.Date(
        string='تاريخ الصب',
        help='تاريخ صب العينة الخرسانية'
    )
    
    testing_date = fields.Date(
        string='تاريخ الفحص',
        help='تاريخ إجراء فحص الانضغاط'
    )
    
    required_age_days = fields.Selection([
        ('7', '7 أيام'),
        ('28', '28 يوم'),
        ('reserve', 'احتياط')
    ], string='العمر المطلوب للفحص',
       help='العمر المطلوب للعينة عند الفحص')
    
    batch_number = fields.Char(
        string='رقم الدفعة',
        help='رقم دفعة العينات'
    )
    
    cube_factor = fields.Float(
        string='معامل المكعب',
        help='معامل تصحيح للمكعب حسب الحجم',
        default=1.0,
        digits=(3, 2)
    )


    reference_general_limit = fields.Float(
        string='المعيار العام',
        help='قيمة مرجعية عامة (تُقبل الأرقام الكسرية) للاستخدام في مقارنة النتائج.'
    )
    
    core_compaction_ratio_reference = fields.Float(
        string='نسبة الحدل (%)',
        help='النسبة المرجعية المطلوبة للحدل لعينة الكور الخرساني - يتم مقارنة معدل نسبة الحدل من النتائج معها'
    )
    reference_min_limit = fields.Float(
        related='sample_id.task_id.reference_min_limit',
        string='المعيار الأدنى',
        readonly=True
    )
    
    softening_warning = fields.Text(
        string='تحذير فحص الليونة',
        readonly=True,
        help='تحذير يظهر عند وجود فرق كبير بين قراءات الليونة'
    )
    
    
    days_remaining = fields.Integer(
        string='الأيام المتبقية',
        compute='_compute_days_remaining',
        store=True,
        help='عدد الأيام المتبقية حتى موعد الفحص (يتوقف عند بدء الفحص)'
    )
    
    factor = fields.Integer(
        string='Factor',
        compute='_compute_days_remaining',
        store=True,
        help='عدد الأيام المتجاوزة بعد انتهاء الموعد المحدد (يظهر فقط عند التجاوز)'
    )
    
    @api.depends('sample_id.concrete_sample_type_id.code')
    def _compute_is_concrete_core(self):
        """تحديد إن كانت العينة كور خرساني بناءً على نوع العينة في السجل الأب للعينة"""
        for record in self:
            code = ''
            try:
                if record.sample_id and getattr(record.sample_id, 'concrete_sample_type_id', False):
                    code = (record.sample_id.concrete_sample_type_id.code or '').upper()
            except Exception:
                code = ''
            record.is_concrete_core = (code == 'CONCRETE_CORE')
    
    @api.depends('casting_date', 'required_age_days', 'state')
    def _compute_days_remaining(self):
        """حساب عدد الأيام المتبقية حتى موعد الفحص وعدد الأيام المتجاوزة (يتوقف عند بدء الفحص)"""
        for record in self:
            if record.state in ('in_progress', 'calculated', 'review', 'approved', 'completed'):
                continue
                
            if not record.casting_date or not record.required_age_days:
                record.days_remaining = 0
                record.factor = 0
                continue
                
            if record.required_age_days == '7':
                target_days = 7
            elif record.required_age_days == '28':
                target_days = 28
            else:  
                target_days = 28
                
            from datetime import timedelta
            target_date = record.casting_date + timedelta(days=target_days)
            today = fields.Date.today()
            
            remaining = (target_date - today).days
            
            if remaining >= 0:
                record.days_remaining = remaining
                record.factor = 0
            else:
                record.days_remaining = 0
                record.factor = abs(remaining)  
    
    end_date = fields.Datetime(
        string='تاريخ الانتهاء',
        tracking=True
    )


    
    technician_id = fields.Many2one(
        'res.users',
        string='الفني المسؤول',
        tracking=True,
        index=True
    )
    
    result_line_ids = fields.One2many(
        'lab.result.line',
        'result_set_id',
        string='أسطر النتائج'
    )
    
    completed_criteria = fields.Integer(
        string='المعايير المكتملة',
        compute='_compute_statistics',
        store=True 
    )
    
    progress_percentage = fields.Float(
        string='نسبة الإنجاز',
        compute='_compute_statistics',
        store=True  
    )
    
    overall_result = fields.Selection([
        ('pass', 'نجح'),
        ('fail', 'فشل'),
        ('pending', 'في الانتظار')
    ], string='النتيجة العامة', compute='_compute_overall_result', store=True, tracking=True)
    
    notes = fields.Html(string='ملاحظات')
    
    sample_count = fields.Integer(
        string='عدد العينات',
        compute='_compute_sample_count',
        help='عدد العينات المفحوصة'
    )
    
    overall_conformity = fields.Selection([
        ('pass', 'مطابق'),
        ('fail', 'غير مطابق'),
        ('pending', 'في الانتظار')
    ], string='حالة المطابقة العامة', compute='_compute_overall_conformity', store=True, tracking=True)
    
    overall_result_with_avg = fields.Char(
        string='النتيجة العامة مع المتوسط',
        compute='_compute_overall_result_with_avg'
    )

    quality_check_id = fields.Many2one(
        'quality.check',
        string='فحص الجودة',
        help='فحص الجودة المرتبط بهذه المجموعة'
    )
    

    quality_alert_id = fields.Many2one(
        'quality.alert',
        string='تنبيه الجودة',
        help='تنبيه الجودة المرتبط بهذه المجموعة'
    )
    
    total_criteria_count = fields.Integer(
        string='إجمالي المعايير',
        compute='_compute_criteria_statistics',
        store=True
    )
    passed_criteria_count = fields.Integer(
        string='المعايير المطابقة',
        compute='_compute_criteria_statistics',
        store=True
    )
    failed_criteria_count = fields.Integer(
        string='المعايير غير المطابقة',
        compute='_compute_criteria_statistics',
        store=True
    )
    compliance_percentage = fields.Float(
        string='نسبة المطابقة %',
        compute='_compute_criteria_statistics',
        store=True
    )
    critical_criteria_count = fields.Integer(
        string='المعايير الحرجة',
        compute='_compute_criteria_statistics',
        store=True
    )
    critical_passed_count = fields.Integer(
        string='المعايير الحرجة المطابقة',
        compute='_compute_criteria_statistics',
        store=True
    )
    critical_compliance_percentage = fields.Float(
        string='نسبة مطابقة المعايير الحرجة %',
        compute='_compute_criteria_statistics',
        store=True
    )
    
    analysis_notes = fields.Text(
        string='ملاحظات التحليل',
        tracking=True
    )
    test_conditions = fields.Text(
        string='ظروف الفحص',
        tracking=True
    )
    environmental_conditions = fields.Text(
        string='الظروف البيئية',
        tracking=True
    )
    equipment_used = fields.Text(
        string='المعدات المستخدمة',
        tracking=True
    )
    
    # --- Signature fields 
    calibration_date = fields.Date(
        string='تاريخ المعايرة',
        tracking=True
    )
    reference_standard = fields.Char(
        string='المعيار المرجعي',
        tracking=True
    )
    uncertainty_analysis = fields.Text(
        string='تحليل عدم اليقين',
        tracking=True
    )



    timer_start = fields.Datetime(string='بداية المؤقّت')
    timer_ready = fields.Datetime(string='نهاية المؤقّت', compute='_compute_timer_ready', store=True)

    def _compute_is_manager(self):
        """حساب ما إذا كان المستخدم الحالي مدير مختبر"""
        for record in self:
            record.is_manager = self.env.user.has_group('appointment_products.group_lab_manager')
    
    def _check_record_access(self, operation="الوصول"):
        """فحص إمكانية الوصول للسجل مع رسائل خطأ واضحة"""
        if not self:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تحذير',
                    'message': 'لم يتم تحديد أي سجل للعمل عليه',
                    'type': 'warning',
                }
            }
            
        for record in self:
            if not record.exists():
                return {
                    'type': 'ir.actions.client', 
                    'tag': 'display_notification',
                    'params': {
                        'title': 'خطأ',
                        'message': f'السجل المطلوب ({record.id}) غير موجود أو تم حذفه',
                        'type': 'danger',
                    }
                }
            
            # فحص الصلاحيات (للفنيين)
            if self.env.user.has_group('appointment_products.group_lab_technician') and \
               not self.env.user.has_group('appointment_products.group_lab_manager'):
                if self.env.user.id not in record.testers_ids.ids:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification', 
                        'params': {
                            'title': 'تحذير',
                            'message': f'ليس لديك صلاحية {operation} هذا السجل. يجب أن تكون مُسنداً إليه كفني مختبر.',
                            'type': 'warning',
                        }
                    }
        return None

    @api.depends('timer_start', 'timer_ready')
    def _compute_set_timer_state(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.timer_start and rec.timer_ready:
                if now >= rec.timer_ready:
                    rec.timer_remaining = 0
                    rec.timer_status = 'completed'
                else:
                    rec.timer_remaining = (rec.timer_ready - now).total_seconds()
                    rec.timer_status = 'running'
            else:
                rec.timer_remaining = 0
                rec.timer_status = 'not_started'

    timer_remaining = fields.Float(
        string='الوقت المتبقي (ثواني)',
        compute='_compute_set_timer_state',
        store=False
    )

    timer_status = fields.Selection([
        ('not_started', 'لم يبدأ'),
        ('running', 'يعمل'),
        ('completed', 'انتهى')
    ], string='حالة المؤقّت', compute='_compute_set_timer_state', store=False)

    @api.depends('timer_remaining')
    def _compute_timer_remaining_display(self):
        """عرض الوقت المتبقي بصيغة مقروءة"""
        for record in self:
            if record.timer_remaining > 0:
                hours = int(record.timer_remaining // 3600)
                minutes = int((record.timer_remaining % 3600) // 60)
                seconds = int(record.timer_remaining % 60)
                record.timer_remaining_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                record.timer_remaining_display = "00:00:00"

    timer_remaining_display = fields.Char(
        string='الوقت المتبقي (عرض)',
        compute='_compute_timer_remaining_display',
        help='عرض الوقت المتبقي بصيغة HH:MM:SS'
    )


    
    def _check_timer_lock_before_save(self):
        """التحقق من قفل المؤقت قبل الحفظ"""
        for record in self:
            if record.timer_start and record.timer_status == 'running':
                locked_criteria = record.template_id.criterion_ids.filtered(
                    lambda c: c.timer_scope == 'per_set' and c.lock_during_wait
                )
                if locked_criteria:
                    raise ValidationError(
                        _("⏰ لا يمكن حفظ البيانات أثناء تشغيل المؤقت!\n\n"
                          "🕒 الوقت المتبقي: %s\n"
                          "🔒 المعايير المقفلة: %s\n\n"
                          "⏳ يرجى الانتظار حتى انتهاء المؤقت قبل إدخال القيم الرقمية.") % (
                            record.timer_remaining_display,
                            ', '.join(locked_criteria.mapped('name'))
                        )
                    )


    @api.depends('timer_start', 'template_id.criterion_ids.timer_scope', 'template_id.criterion_ids.waiting_unit', 'template_id.criterion_ids.waiting_value')
    def _compute_timer_ready(self):
        """يحسب موعد جاهزية الإدخال بناءً على أطول فترة انتظار للمعايير بنطاق per_set."""
        for rs in self:
            if not rs.timer_start:
                rs.timer_ready = False
                continue

            timer_criteria = rs.template_id.criterion_ids.filtered(
                lambda c: c.timer_scope == 'per_set' and c.waiting_unit and c.waiting_value
            )
            
            _logger.info(f"Timer criteria found for {rs.name}: {len(timer_criteria)} criteria")
            for crit in timer_criteria:
                _logger.info(f"- {crit.name}: {crit.waiting_value} {crit.waiting_unit}")

            if not timer_criteria:
                rs.timer_ready = rs.timer_start + relativedelta(minutes=5)
                _logger.info(f"No timer criteria found, setting default 5 minutes timer for {rs.name}")
                continue
            max_ready = rs.timer_start
            for crit in timer_criteria:
                delta = relativedelta(**{crit.waiting_unit: crit.waiting_value})
                candidate = rs.timer_start + delta
                if candidate > max_ready:
                    max_ready = candidate
                _logger.info(f"Timer for {crit.name}: {candidate}, max_ready: {max_ready}")

            rs.timer_ready = max_ready
            _logger.info(f"Final timer_ready for {rs.name}: {rs.timer_ready}")


    def action_start_timer(self):
        """بدء المؤقت العام للمجموعة"""

        access_check = self._check_record_access("بدء المؤقت")
        if access_check:
            return access_check
            
        for record in self:
            if record.state != 'in_progress':
                raise ValidationError(
                    _("⚠️ يجب بدء الفحص أولاً قبل تشغيل المؤقت!\n\n"
                      "الحالة الحالية: %s\n"
                      "📋 اضغط على زر 'بدء الفحص' أولاً ثم حاول تشغيل المؤقت.") % 
                    dict(record._fields['state'].selection).get(record.state, record.state)
                )
            
            if not record.has_timer_criteria:
                raise ValidationError(
                    _("⚠️ لا توجد معايير مرتبطة بالمؤقت في هذا القالب!\n\n"
                      "📋 يرجى إضافة معايير مع إعدادات المؤقت في القالب أولاً.")
                )
            
            if record.timer_start:
                raise ValidationError(
                    _("⚠️ المؤقت قد بدأ بالفعل!\n\n"
                      "🕒 وقت البدء: %s\n"
                      "⏰ الحالة: %s") % (
                        record.timer_start.strftime('%Y-%m-%d %H:%M:%S'),
                        dict(record._fields['timer_status'].selection).get(record.timer_status, record.timer_status)
                    )
                )
            
            record.write({'timer_start': fields.Datetime.now(), 'timer_completion_notified': False})
            

            record.message_post(
                body=f"🕐 تم بدء المؤقت للمجموعة {record.name}",
                message_type='notification'
            )
            
            if record.testers_ids:
                timer_duration = ""
                if record.timer_ready:
                    duration = record.timer_ready - record.timer_start
                    hours = int(duration.total_seconds() // 3600)
                    minutes = int((duration.total_seconds() % 3600) // 60)
                    if hours > 0:
                        timer_duration = f" لمدة {hours} ساعة و {minutes} دقيقة"
                    else:
                        timer_duration = f" لمدة {minutes} دقيقة"
                
                for tester in record.testers_ids:
                    record.message_post(
                        body=f"🕐 تم بدء المؤقت لفحصك{timer_duration}<br/>"
                             f"🧪 العينة: {record.sample_id.name}<br/>"
                             f"📋 قالب الفحص: {record.template_id.name}<br/>"
                             f"⏰ موعد الانتهاء: {record.timer_ready.strftime('%Y-%m-%d %H:%M') if record.timer_ready else 'غير محدد'}<br/>"
                             f"⚠️ لا يمكن إدخال القيم حتى انتهاء المؤقت<br/>"
                             f"🔗 <a href='/web#id={record.id}&model=lab.result.set&view_type=form'>متابعة الفحص</a>",
                        message_type='notification',
                        partner_ids=[tester.partner_id.id],
                        subtype_id=self.env.ref('mail.mt_note').id
                    )
        
        return True

    @api.model
    def cron_update_timer_status(self):
        """تحديث حالة المؤقت كل دقيقة
        - لا يمكن البحث على حقل غير مخزّن (timer_status) لذا نعتمد على مقارنة القيم الزمنية.
        - في كل دورة نعيد حساب حالة المؤقّت ونرسل إشعاراً عند اكتماله.
        """
        now = fields.Datetime.now()
        active_timers = self.search([
            ('timer_start', '!=', False),
            ('timer_ready', '>', now),
        ])
        for record in active_timers:
            record._compute_set_timer_state()

        completed_timers = self.search([
            ('timer_start', '!=', False),
            ('timer_ready', '<=', now),
        ])
        for record in completed_timers:
            if record.timer_status != 'completed':
                record._compute_set_timer_state()
            if record.timer_status == 'completed' and not record.timer_completion_notified:

                record.message_post(
                    body=_("⏰ انتهى المؤقت للمجموعة %s - يمكن الآن إدخال القيم") % record.name,
                    message_type='notification'
                )
                

                if record.testers_ids:
                    for tester in record.testers_ids:
                        record.message_post(
                            body=f"⏰ انتهى المؤقت - يمكنك الآن إدخال القيم<br/>"
                                 f"🧪 العينة: {record.sample_id.name}<br/>"
                                 f"📋 قالب الفحص: {record.template_id.name}<br/>"
                                 f"📊 نسبة الإنجاز: {record.progress_percentage:.1%}<br/>"
                                 f"🔗 <a href='/web#id={record.id}&model=lab.result.set&view_type=form'>فتح الفحص</a>",
                            message_type='notification',
                            partner_ids=[tester.partner_id.id],
                            subtype_id=self.env.ref('mail.mt_note').id
                        )
                
                record.timer_completion_notified = True
        return True

    active = fields.Boolean(string='نشط', default=True, help='إلغاء التحديد لأرشفة مجموعة النتائج بدون حذفها.')
    

    has_timer_criteria = fields.Boolean(
        string='يحتوي على معايير مؤقت',
        compute='_compute_has_timer_criteria',
        store=True,
        help='يحدد ما إذا كانت هناك معايير مرتبطة بالمؤقت'
    )
    
    allow_parallel_tests = fields.Boolean(
        string='السماح بالفحوصات المتوازية',
        related='template_id.allow_parallel_tests',
        store=True,
        readonly=True,
        help='عند تفعيله، يتم تجاهل الترتيب المتبع ويمكن العمل على كل الفحوصات دفعة واحدة'
    )
    
    all_timers_completed = fields.Boolean(
        string='جميع المؤقتات مكتملة',
        compute='_compute_all_timers_completed',
        store=True,
        help='يحدد ما إذا كانت جميع المؤقتات قد انتهت'
    )

    @api.depends('template_id.criterion_ids.timer_scope', 'template_id.criterion_ids.waiting_unit', 'template_id.criterion_ids.waiting_value')
    def _compute_has_timer_criteria(self):
        """حساب ما إذا كانت هناك معايير مرتبطة بالمؤقت"""
        for record in self:
            if record.template_id:
                timer_criteria = record.template_id.criterion_ids.filtered(
                    lambda c: c.timer_scope and c.waiting_unit and c.waiting_value
                )
                record.has_timer_criteria = bool(timer_criteria)
            else:
                record.has_timer_criteria = False

    @api.depends('timer_status', 'result_line_ids.is_timer_done')
    def _compute_all_timers_completed(self):
        """حساب ما إذا كانت جميع المؤقتات قد انتهت"""
        for record in self:
            if not record.has_timer_criteria:
                record.all_timers_completed = True
                continue
            

            set_timer_done = record.timer_status == 'completed'
            

            line_timers_done = all(
                line.is_timer_done for line in record.result_line_ids.filtered(
                    lambda l: l.timer_scope == 'per_line' and l.waiting_value
                )
            )
            
            record.all_timers_completed = set_timer_done and line_timers_done
    
    def _compute_concrete_sample_info(self):
        """
        حساب معلومات عينة الخرسانة - تبسيط لاستخدام البيانات المحفوظة
        البيانات محفوظة مباشرة في result_set بدلاً من الحساب من move_lines
        """
        for record in self:

            if hasattr(record, '_origin') and record._origin.concrete_group_no:
                continue
                

            if not record.is_concrete_sample:
                record.concrete_group_no = 0
                record.concrete_age_days = False
                record.concrete_field_code = False
                record.concrete_field_serial = False

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:
            if not vals.get('start_date'):
                vals['start_date'] = fields.Datetime.now()
            if not vals.get('technician_id'):
                vals['technician_id'] = self.env.user.id
            if vals.get('name', _('جديد')) == _('جديد'):
                vals['name'] = self.env['ir.sequence'].next_by_code('lab.result.set') or _('جديد')
            try:
                if 'reference_general_limit' not in vals:
                    sample_id = vals.get('sample_id')
                    if sample_id:
                        sample = self.env['lab.sample'].browse(sample_id)
                        task = getattr(sample, 'task_id', False)
                        if task and getattr(task, 'reference_general_limit', False):
                            vals['reference_general_limit'] = float(task.reference_general_limit)
                        if task and getattr(task, 'core_compaction_ratio', False):
                            vals['core_compaction_ratio_reference'] = float(task.core_compaction_ratio)
                sample_id = vals.get('sample_id')
                if sample_id and 'is_concrete_sample' not in vals:
                    sample = self.env['lab.sample'].browse(sample_id)
                    is_conc = False
                    try:

                        is_conc = bool(getattr(sample, 'is_concrete_sample', False))

                        if not is_conc and sample.concrete_sample_type_id:
                            is_conc = 'CONCRETE' in (sample.concrete_sample_type_id.code or '').upper()

                        if not is_conc and sample.product_id and sample.product_id.product_tmpl_id.sample_type_id:
                            is_conc = 'CONCRETE' in (sample.product_id.product_tmpl_id.sample_type_id.code or '').upper()
                    except Exception:
                        is_conc = False
                    if is_conc:
                        vals['is_concrete_sample'] = True
            except Exception:
                pass
        
        result_sets = super().create(vals_list)
        for result_set in result_sets:
            if result_set.template_id and result_set.number_of_samples:
                result_set._create_result_lines()
        return result_sets
    
    @api.depends('result_line_ids', 'result_line_ids.is_filled', 'result_line_ids.value_numeric', 
                 'result_line_ids.value_text', 'result_line_ids.value_selection', 
                 'result_line_ids.value_boolean', 'result_line_ids.value_date', 'state')
    def _compute_statistics(self):

        for record in self:
            if not record.result_line_ids:
                record.completed_criteria = 0
                record.progress_percentage = 0.0
                continue

            record.result_line_ids._compute_is_filled()
            
            total = len(record.result_line_ids)
            completed = 0
            
            for line in record.result_line_ids:
                test_type = line.criterion_id.test_type
                is_really_filled = False
                
                if test_type == 'numeric':
                    is_really_filled = line.value_numeric is not None
                elif test_type == 'text':
                    is_really_filled = bool(line.value_text and line.value_text.strip())
                elif test_type == 'selection':
                    is_really_filled = bool(line.value_selection)
                elif test_type == 'boolean':
                    is_really_filled = True
                elif test_type == 'date':
                    is_really_filled = bool(line.value_date)
                elif test_type == 'computed':
                    is_really_filled = line.value_numeric is not None
                
                if line.is_filled != is_really_filled:
                    line.with_context(bypass_timer_lock=True).write({'is_filled': is_really_filled})
                
                if is_really_filled:
                    completed += 1
            
            record.completed_criteria = completed
            record.progress_percentage = (completed / total) if total > 0 else 0.0
            
            if record.id and isinstance(record.id, int):
                _logger.debug(
                    f"Progress calculation for {record.name}: {completed}/{total} = {record.progress_percentage:.2%}"
                )
    
    @api.depends('result_line_ids.is_compliant', 'result_line_ids.is_filled', 'result_line_ids.is_critical', 'state')
    def _compute_overall_result(self):
        """حساب النتيجة الإجمالية - محسن لتجنب النتائج المبكرة"""
        for result_set in self:

            if result_set.state in ('draft', 'pending') or not result_set.result_line_ids:
                result_set.overall_result = 'pending'
                continue
                
            input_lines = result_set.result_line_ids.filtered('criterion_id.is_input_field')
            filled_input_lines = input_lines.filtered('is_filled')
            
            if not filled_input_lines and input_lines:
                result_set.overall_result = 'pending'
                continue
            
            if len(filled_input_lines) < len(input_lines):
                result_set.overall_result = 'pending'
                continue
            all_filled_lines = result_set.result_line_ids.filtered('is_filled')
            critical_failed_lines = all_filled_lines.filtered(lambda l: l.is_critical and not l.is_compliant)
            
            if critical_failed_lines:
                result_set.overall_result = 'fail'
                failed_criteria = ', '.join(critical_failed_lines.mapped('criterion_id.name'))
                _logger.info(f"Test failed for {result_set.name} due to critical criteria: {failed_criteria}")
            else:
                result_set.overall_result = 'pass'
                non_critical_failed = all_filled_lines.filtered(lambda l: not l.is_critical and not l.is_compliant)
                if non_critical_failed:
                    failed_non_critical = ', '.join(non_critical_failed.mapped('criterion_id.name'))
                    _logger.info(f"Test passed for {result_set.name} despite non-critical failures: {failed_non_critical}")

            try:
                if result_set.is_concrete_sample:
                    task = getattr(result_set.sample_id, 'task_id', False)
                    ref_min = float(task.reference_min_limit) if task and getattr(task, 'reference_min_limit', False) else None
                    try:
                        min_margin = float(self.env['ir.config_parameter'].sudo().get_param('appointment_products.min_limit_margin', default='3'))
                    except Exception:
                        min_margin = 3.0
                    if ref_min is not None:
                        avg_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE')[:1]
                        has_strength_data = False
                        if avg_line:
                            grp_avg = avg_line[0].value_numeric or avg_line[0].result_value_computed or 0.0
                            has_strength_data = True
                        else:
                            strengths = result_set.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'COMP_STRENGTH_CONCRETE')
                            values = []
                            for l in strengths:
                                v = l.value_numeric
                                if (v is None or v == 0) and getattr(l.criterion_id, 'test_type', '') == 'computed':
                                    v = l.result_value_computed
                                if v is not None:
                                    values.append(float(v))
                            grp_avg = (sum(values)/len(values)) if values else 0.0
                            has_strength_data = bool(values)
                        if has_strength_data and grp_avg < (float(ref_min) - float(min_margin)):
                            result_set.overall_result = 'fail'
                            _logger.info(f"Concrete group {result_set.name} marked as FAIL: avg {grp_avg} < (ref_min {ref_min} - margin {min_margin})")

                sample = getattr(result_set, 'sample_id', False)
                if sample and (getattr(sample.concrete_sample_type_id, 'code', '') or '').upper() == 'CONCRETE_CORE':
                    try:
                        tol = float(self.env['ir.config_parameter'].sudo().get_param('appointment_products.core_thickness_tolerance', default='0.3'))
                    except Exception:
                        tol = 0.3
                    try:
                        req = None

                        if getattr(result_set, 'reference_general_limit', False):
                            req = float(result_set.reference_general_limit)
                        else:
                            tsk = getattr(sample, 'task_id', False)
                            if tsk and getattr(tsk, 'reference_general_limit', False):
                                req = float(tsk.reference_general_limit)
                        if req is not None:
                            th_line = result_set.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'CORE_THICKNESS_OVERALL_AVG')[:1]
                            if th_line:
                                avg_val = th_line[0].value_numeric or th_line[0].result_value_computed or 0.0
                                if avg_val < (req - tol):
                                    result_set.overall_result = 'fail'
                                    _logger.info(f"Core test {result_set.name} marked as FAIL: overall thickness {avg_val} < required {req} - tol {tol}")
                    except Exception:
                        pass
                    

                    try:
                        ref_compaction = getattr(result_set, 'core_compaction_ratio_reference', False)
                        if ref_compaction and ref_compaction > 0:
                            compaction_line = result_set.result_line_ids.filtered(
                                lambda l: l.criterion_id and l.criterion_id.code == 'COMPACTION_RATIO_AVG'
                            )[:1]
                            
                            if compaction_line:
                                actual_compaction = compaction_line[0].value_numeric or compaction_line[0].result_value_computed or 0.0
                                if actual_compaction < ref_compaction:
                                    result_set.overall_result = 'fail'
                                    _logger.info(f"Core test {result_set.name} marked as FAIL: compaction ratio avg {actual_compaction}% < required {ref_compaction}%")
                                else:
                                    _logger.info(f"Core test {result_set.name} compaction ratio check PASSED: {actual_compaction}% >= required {ref_compaction}%")
                    except Exception:
                        pass
            except Exception:
                pass

    @api.depends('overall_result', 'is_concrete_sample', 'result_line_ids.result_value_numeric', 'result_line_ids.result_value_computed')
    def _compute_overall_result_with_avg(self):
        for rec in self:
            status = dict(rec._fields['overall_result'].selection).get(rec.overall_result, '')
            rec.overall_result_with_avg = status
            if not rec.is_concrete_sample:
                continue
            avg_line = rec.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE')[:1]
            val = None
            if avg_line:
                val = avg_line[0].value_numeric or avg_line[0].result_value_computed
            else:
                values = []
                for l in rec.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'COMP_STRENGTH_CONCRETE'):
                    v = l.value_numeric
                    if (v is None or v == 0) and getattr(l.criterion_id, 'test_type', '') == 'computed':
                        v = l.result_value_computed
                    if v is not None:
                        values.append(float(v))
                if values:
                    val = sum(values)/len(values)
            if val is None:
                continue
            try:
                text = ('{0:.2f}'.format(float(val))).rstrip('0').rstrip('.')
            except Exception:
                text = str(val)

            if status:
                if rec.overall_result == 'pass':
                    rec.overall_result_with_avg = f"نجح\n{text}"
                elif rec.overall_result == 'fail':
                    rec.overall_result_with_avg = f"فشل\n{text}"
                else:
                    rec.overall_result_with_avg = f"{status}\n{text}"
            else:
                rec.overall_result_with_avg = text
    
    def _create_result_lines(self):

        start_time = time.time()
        
        if not self.template_id or not self.number_of_samples:
            return

        self.result_line_ids.unlink()

        lines_to_create = []

        non_summary_criteria = self.template_id.criterion_ids.filtered(lambda c: not c.is_summary_field and not c.is_global)
        for sample_no in range(1, self.number_of_samples + 1):
            for criterion in non_summary_criteria:
                lines_to_create.append({
                    'result_set_id': self.id,
                    'sample_no': sample_no,
                    'criterion_id': criterion.id,
                    'sequence': criterion.sequence,
                })

        global_criteria = self.template_id.criterion_ids.filtered(lambda c: c.is_global and not c.is_summary_field)
        for criterion in global_criteria:
            lines_to_create.append({
                'result_set_id': self.id,
                'sample_no': 1,
                'criterion_id': criterion.id,
                'sequence': criterion.sequence,
            })

        summary_criteria = self.template_id.criterion_ids.filtered(lambda c: c.is_summary_field)
        for criterion in summary_criteria:
            lines_to_create.append({
                'result_set_id': self.id,
                'sample_no': 1,
                'criterion_id': criterion.id,
                'sequence': criterion.sequence,
            })

        if lines_to_create:

            self.env['lab.result.line'].create(lines_to_create)

        area_comp_lines = self.result_line_ids.filtered(lambda l: l.criterion_id.code == 'AREA_COMP' and not l.value_numeric)
        if area_comp_lines:
            area_source_line = self.env['lab.result.line'].search([
                ('criterion_id.code', '=', 'AREA'),
                ('result_set_id', '!=', self.id),
                ('result_set_id.sample_id', '=', self.sample_id.id),
                ('value_numeric', '>', 0),
            ], order='result_set_id.id desc', limit=1)
            if area_source_line:
                for acl in area_comp_lines:
                    acl.value_numeric = area_source_line.value_numeric


        execution_time = time.time() - start_time
        _logger.info(
            "إنشاء أسطر النتائج للمجموعة %s: %d أسطر في %.3f ثانية", 
            self.name, 
            len(lines_to_create) if lines_to_create else 0, 
            execution_time
        )

    def action_generate_result_lines(self):
        """دالة عامة لإنشاء أسطر النتائج - للتوافق مع الكود القديم"""
        return self._create_result_lines()
    
    def action_start(self):
        """بدء التنفيذ - محسن لتحديث حالة المرحلة في Flow"""
        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now()
        })
        
        if self.sample_id.state in ('received', 'draft'):
            self.sample_id.state = 'testing'
            self.sample_id.message_post(body=_('🧪 تم بدء الفحص - تحولت العينة إلى حالة "قيد الفحص"'))
        
        FlowLine = self.env['lab.test.flow.line']
        flow_line = FlowLine.search([('result_set_id', '=', self.id)], limit=1)
        if flow_line and flow_line.state == 'pending':
            flow_line.state = 'running'
            flow_line.flow_id.message_post(
                body=f"▶️ تم بدء المرحلة {flow_line.sequence}: {flow_line.test_template_id.name}"
            )

        self.message_post(body=_('▶️ تم بدء تنفيذ الفحوصات'))
        

        if self.testers_ids:
            for tester in self.testers_ids:
                self.message_post(
                    body=(
                        "▶️ <b>بدء فحص العينة</b>"
                        "<div style='margin-top:6px'>"
                        f"🧪 <b>العينة:</b> {self.sample_id.display_name}<br/>"
                        f"📋 <b>قالب الفحص:</b> {self.template_id.display_name}<br/>"
                        f"📅 <b>تاريخ البدء:</b> {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        "</div>"
                        f"<div style='margin-top:8px;'><a href='/web#id={self.id}&model=lab.result.set&view_type=form'>🔗 فتح الفحص</a></div>"
                    ),
                    message_type='notification',
                    partner_ids=[tester.partner_id.id],
                    subtype_id=self.env.ref('mail.mt_note').id
                )
    
    def action_complete(self):
        """إكمال المجموعة - محسن للأداء"""

        incomplete_criteria = []
        for line in self.result_line_ids:
            if not line._is_value_complete():
                incomplete_criteria.append(line.criterion_id.name)
        
        if incomplete_criteria:
            raise UserError(_('لا يمكن إكمال الفحص قبل إدخال جميع القيم المطلوبة للمعايير التالية:\n%s') % 
                          ', '.join(incomplete_criteria))


        self._compute_calculated_criteria()


        end_time = fields.Datetime.now()
        
        state_to_set = 'completed'
            
        self.write({
            'state': state_to_set,
            'end_date': end_time
        })
        
        completion_message = _('تم إكمال جميع الفحوصات بنجاح في %s') % end_time.strftime('%Y-%m-%d %H:%M:%S')
        self.message_post(body=completion_message)
    
        self._update_flow_state()
    
    def _compute_calculated_criteria(self):
        """حساب قيم المعايير المحسوبة - محسن للأداء"""

        computed_lines = self.result_line_ids.filtered('criterion_id.is_computed_field')
        if not computed_lines:
            return
            

        series_data = {}
        for line in self.result_line_ids:
            code = line.criterion_id.code
            if code:
                series_data.setdefault(code, [])
                value = line.get_numeric_value()
                if value is not None:
                    series_data[code].append(value)


        global_context = {}
        if self.sample_id:
            if self.sample_id.sample_subtype_id and self.sample_id.sample_subtype_id.hole_count:
                global_context['HOLE_COUNT'] = self.sample_id.sample_subtype_id.hole_count
            elif self.sample_id.product_id:

                global_context['HOLE_COUNT'] = self.sample_id.product_id.product_tmpl_id.hole_count or 0


        lines_by_sample = {}
        for line in self.result_line_ids:
            sample_no = line.sample_no
            if sample_no not in lines_by_sample:
                lines_by_sample[sample_no] = []
            lines_by_sample[sample_no].append(line)



        for sample_no, sample_lines in lines_by_sample.items():
            calculation_context = global_context.copy()
            for dep_line in sample_lines:
                if dep_line.criterion_id.code:
                    calculation_context[dep_line.criterion_id.code] = dep_line.get_numeric_value()


            computed_criteria = sorted(
                [line for line in sample_lines if line.criterion_id.is_computed_field and not line.criterion_id.is_summary_field],
                key=lambda l: (l.criterion_id.sequence or 999, l.criterion_id.id)
            )
            
            for line in computed_criteria:
                try:
                    if line.criterion_id.computation_formula:

                        _logger.debug(
                            "حساب معيار %s (عينة %s) - الصيغة: %s - calculation_context: %s", 
                            line.criterion_id.code,
                            sample_no, 
                            line.criterion_id.computation_formula,
                            {k: v for k, v in calculation_context.items() if not k.startswith('__')}
                        )
                        
                        result = self.env['lab.computation.engine'].execute_formula(
                            line.criterion_id.computation_formula,
                            calculation_context,
                            series_data=series_data,
                            context_result_set=self
                        )
                        line.value_numeric = result

                        calculation_context[line.criterion_id.code] = result
                        

                        if line.criterion_id.code not in series_data:
                            series_data[line.criterion_id.code] = []
                        

                        while len(series_data[line.criterion_id.code]) < sample_no:
                            series_data[line.criterion_id.code].append(0)
                        
                        if len(series_data[line.criterion_id.code]) >= sample_no:
                            series_data[line.criterion_id.code][sample_no - 1] = result
                        else:
                            series_data[line.criterion_id.code].append(result)
                        

                        _logger.info(
                            "نتيجة المعيار %s (عينة %s): %s - series_data محدث: %s", 
                            line.criterion_id.code,
                            sample_no, 
                            result,
                            series_data.get(line.criterion_id.code, [])
                        )
                        
                except Exception as e:
                    _logger.error(
                        "خطأ في حساب المعيار %s للعينة %s في مجموعة النتائج %s: %s", 
                        line.criterion_id.code, 
                        sample_no, 
                        self.name, 
                        str(e),
                        exc_info=True 
                    )

                    line.value_numeric = 0.0
        

        updated_series_data = series_data.copy()

        for sample_no in range(1, self.number_of_samples + 1):
            for line in self.result_line_ids.filtered(lambda l: l.sample_no == sample_no and not l.criterion_id.is_summary_field):
                code = line.criterion_id.code
                if code:
                    if code not in updated_series_data:
                        updated_series_data[code] = []

                    while len(updated_series_data[code]) < sample_no:
                        updated_series_data[code].append(0)

                    updated_series_data[code][sample_no - 1] = line.value_numeric or 0
                        

        # حساب المعايير التلخيصية
        summary_criteria = self.result_line_ids.filtered(lambda l: l.criterion_id.is_computed_field and l.criterion_id.is_summary_field)
        for line in summary_criteria:
            try:
                if line.criterion_id.computation_formula:

                    _logger.debug(
                        "حساب معيار تلخيصي %s - الصيغة: %s", 
                        line.criterion_id.code, 
                        line.criterion_id.computation_formula
                    )
                    _logger.debug(
                        "بيانات السياق المتاحة: %s", 
                        list(updated_series_data.keys())
                    )
                    
                    result = self.env['lab.computation.engine'].execute_formula(
                        line.criterion_id.computation_formula,
                        updated_series_data,
                        series_data=updated_series_data,
                        context_result_set=self
                    )
                    
                    if result is not None:
                        line.value_numeric = result
                        
                        _logger.debug(
                            "تم تحديث المعيار التلخيصي %s بالقيمة: %s", 
                            line.criterion_id.code, 
                            result
                        )

                    _logger.debug(
                        "نتيجة المعيار التلخيصي %s: %s", 
                        line.criterion_id.code, 
                        result
                    )
                    
            except Exception as e:
                _logger.error(
                    "خطأ في حساب المعيار التلخيصي %s: %s", 
                    line.criterion_id.code, 
                    str(e),
                    exc_info=True 
                )
                line.value_numeric = 0.0
    
    def _compute_summary_criteria(self):

        for record in self:

            series_data = {}
            for line in record.result_line_ids.filtered(lambda l: not l.criterion_id.is_summary_field):
                code = line.criterion_id.code
                if code:
                    if code not in series_data:
                        series_data[code] = []
                    
                    while len(series_data[code]) < line.sample_no:
                        series_data[code].append(0)
                    
                    series_data[code][line.sample_no - 1] = line.value_numeric or 0
            

            summary_criteria = record.result_line_ids.filtered(lambda l: l.criterion_id.is_computed_field and l.criterion_id.is_summary_field)
            for line in summary_criteria:
                try:
                    if line.criterion_id.computation_formula:
                        _logger.info(
                            "حساب معيار تلخيصي تلقائي %s - الصيغة: %s", 
                            line.criterion_id.code, 
                            line.criterion_id.computation_formula
                        )
                        
                        global_context = {}
                        if record.sample_id and record.sample_id.sample_subtype_id and record.sample_id.sample_subtype_id.hole_count:
                            global_context['HOLE_COUNT'] = record.sample_id.sample_subtype_id.hole_count
                        
                        summary_context = global_context.copy()
                        for criteria_code, values_list in series_data.items():
                            if values_list: 
                                summary_context[criteria_code] = values_list[-1] if len(values_list) == 1 else values_list[0]
                        
                        result = record.env['lab.computation.engine'].execute_formula(
                            line.criterion_id.computation_formula,
                            summary_context,
                            series_data=series_data,
                            context_result_set=record
                        )
                        line.value_numeric = result
                        
                        _logger.info(
                            "نتيجة المعيار التلخيصي التلقائي %s: %s", 
                            line.criterion_id.code, 
                            result
                        )
                        
                except Exception as e:
                    _logger.error(
                        "خطأ في حساب المعيار التلخيصي التلقائي %s: %s", 
                        line.criterion_id.code, 
                        str(e),
                        exc_info=True 
                    )
                    line.value_numeric = 0.0
    
    @api.depends('number_of_samples')
    def _compute_sample_count(self):
        for record in self:
            record.sample_count = record.number_of_samples
    
    
    @api.depends('overall_result', 'result_line_ids.is_compliant', 'result_line_ids.is_critical', 'result_line_ids.is_filled', 'state')
    def _compute_overall_conformity(self):
        """حساب المطابقة الإجمالية - محسن لتجنب النتائج المبكرة"""
        for result_set in self:
            if result_set.state in ('draft', 'pending') or not result_set.result_line_ids:
                result_set.overall_conformity = 'pending'
                continue
                
            input_lines = result_set.result_line_ids.filtered('criterion_id.is_input_field')
            filled_input_lines = input_lines.filtered('is_filled')
            
            if not filled_input_lines or len(filled_input_lines) < len(input_lines):
                result_set.overall_conformity = 'pending'
                continue
                
            filled_lines = result_set.result_line_ids.filtered('is_filled')
            critical_non_compliant = filled_lines.filtered(lambda l: l.is_critical and not l.is_compliant)
            if critical_non_compliant:
                result_set.overall_conformity = 'fail'
            else:
                result_set.overall_conformity = 'pass'

    @api.depends('result_line_ids.is_compliant', 'result_line_ids.is_critical')
    def _compute_criteria_statistics(self):

        for result_set in self:
            if not result_set.result_line_ids:

                result_set.update({
                    'total_criteria_count': 0,
                    'passed_criteria_count': 0,
                    'failed_criteria_count': 0,
                    'compliance_percentage': 0.0,
                    'critical_criteria_count': 0,
                    'critical_passed_count': 0,
                    'critical_compliance_percentage': 0.0,
                })
                continue


            if not isinstance(result_set.id, int):
                filled_lines = result_set.result_line_ids.filtered('is_filled')
                total_count = len(filled_lines)
                passed_count = len(filled_lines.filtered(lambda l: l.is_compliant))
                failed_count = total_count - passed_count
                critical_lines = filled_lines.filtered('is_critical')
                critical_count = len(critical_lines)
                critical_passed_count = len(critical_lines.filtered(lambda l: l.is_compliant))

                compliance_percentage = (passed_count / total_count * 100) if total_count else 0.0
                critical_compliance_percentage = (critical_passed_count / critical_count * 100) if critical_count else 0.0

                result_set.update({
                    'total_criteria_count': total_count,
                    'passed_criteria_count': passed_count,
                    'failed_criteria_count': failed_count,
                    'compliance_percentage': compliance_percentage,
                    'critical_criteria_count': critical_count,
                    'critical_passed_count': critical_passed_count,
                    'critical_compliance_percentage': critical_compliance_percentage,
                })
                continue
            

            self.env.cr.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN is_filled AND is_compliant THEN 1 END) as passed_count,
                    COUNT(CASE WHEN is_filled AND NOT is_compliant THEN 1 END) as failed_count,
                    COUNT(CASE WHEN is_critical THEN 1 END) as critical_count,
                    COUNT(CASE WHEN is_critical AND is_filled AND is_compliant THEN 1 END) as critical_passed_count
                FROM lab_result_line 
                WHERE result_set_id = %s AND is_filled = true
            """, (result_set.id,))
            
            stats = self.env.cr.fetchone()
            if stats:
                total_count, passed_count, failed_count, critical_count, critical_passed_count = stats
                

                compliance_percentage = (passed_count / total_count * 100) if total_count > 0 else 0
                critical_compliance_percentage = (critical_passed_count / critical_count * 100) if critical_count > 0 else 0
                
                result_set.update({
                    'total_criteria_count': total_count,
                    'passed_criteria_count': passed_count,
                    'failed_criteria_count': failed_count,
                    'compliance_percentage': compliance_percentage,
                    'critical_criteria_count': critical_count,
                    'critical_passed_count': critical_passed_count,
                    'critical_compliance_percentage': critical_compliance_percentage,
                })
            else:

                result_set.update({
                    'total_criteria_count': 0,
                    'passed_criteria_count': 0,
                    'failed_criteria_count': 0,
                    'compliance_percentage': 0.0,
                    'critical_criteria_count': 0,
                    'critical_passed_count': 0,
                    'critical_compliance_percentage': 0.0,
                })

    def get_test_result_details(self):
        """📊 الحصول على تفاصيل شاملة لنتائج الفحص"""
        self.ensure_one()
        
        filled_lines = self.result_line_ids.filtered('is_filled')
        if not filled_lines:
            return {
                'status': 'pending',
                'message': 'لم يتم إدخال أي قيم بعد',
                'details': {}
            }
        
        critical_lines = filled_lines.filtered('is_critical')
        non_critical_lines = filled_lines.filtered(lambda l: not l.is_critical)
        
        critical_passed = critical_lines.filtered('is_compliant')
        critical_failed = critical_lines.filtered(lambda l: not l.is_compliant)
        
        non_critical_passed = non_critical_lines.filtered('is_compliant')
        non_critical_failed = non_critical_lines.filtered(lambda l: not l.is_compliant)
        
        final_result = 'pass' if not critical_failed else 'fail'
        
        result_details = {
            'status': final_result,
            'overall_result': self.overall_result,
            'overall_conformity': self.overall_conformity,
            'summary': {
                'total_criteria': len(filled_lines),
                'critical_count': len(critical_lines),
                'non_critical_count': len(non_critical_lines),
                'total_passed': len(critical_passed) + len(non_critical_passed),
                'total_failed': len(critical_failed) + len(non_critical_failed),
            },
            'critical_criteria': {
                'total': len(critical_lines),
                'passed': len(critical_passed),
                'failed': len(critical_failed),
                'passed_names': critical_passed.mapped('criterion_id.name'),
                'failed_names': critical_failed.mapped('criterion_id.name'),
                'compliance_rate': (len(critical_passed) / len(critical_lines) * 100) if critical_lines else 100,
            },
            'non_critical_criteria': {
                'total': len(non_critical_lines),
                'passed': len(non_critical_passed),
                'failed': len(non_critical_failed),
                'passed_names': non_critical_passed.mapped('criterion_id.name'),
                'failed_names': non_critical_failed.mapped('criterion_id.name'),
                'compliance_rate': (len(non_critical_passed) / len(non_critical_lines) * 100) if non_critical_lines else 100,
            }
        }
        
        if final_result == 'pass':
            if critical_failed:
                result_details['message'] = " خطأ: الفحص يجب أن يفشل لوجود معايير حرجة غير مطابقة!"
            elif non_critical_failed:
                result_details['message'] = f" نجح الفحص رغم فشل {len(non_critical_failed)} معايير غير حرجة"
            else:
                result_details['message'] = " نجح الفحص - جميع المعايير مطابقة"
        else:
            result_details['message'] = f" فشل الفحص بسبب {len(critical_failed)} معايير حرجة غير مطابقة"
        
        return result_details



    def action_calculate_results(self):
        """ حساب جميع النتائج تلقائياً"""

        access_check = self._check_record_access("حساب النتائج")
        if access_check:
            return access_check
            
        for record in self:

            current_set_running_timers = []
            

            if record.timer_status == 'running':
                current_set_running_timers.append(f"مؤقت هذا الفحص - متبقي: {record.timer_remaining_display}")
            

            line_timers = record.result_line_ids.filtered(
                lambda l: l.timer_scope == 'per_line' and l.timer_status == 'running'
            )
            

            if current_set_running_timers or line_timers:
                running_timers = current_set_running_timers.copy()
                for line in line_timers:
                    remaining = line.timer_remaining if line.timer_remaining else 0
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    seconds = int(remaining % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    running_timers.append(f"مؤقت {line.criterion_id.name} - متبقي: {time_str}")
                
                timers_text = '\n'.join(running_timers) if running_timers else "المؤقتات قيد التشغيل"
                
                raise ValidationError(
                    _(" لا يمكن حساب النتائج قبل انتهاء جميع المؤقتات!\n\n"
                      " المؤقتات الجارية:\n%s\n\n"
                      " يرجى الانتظار حتى انتهاء جميع المؤقتات قبل حساب النتائج.") % timers_text
                )
            
            for line in record.result_line_ids:
                line._compute_compliance_and_deviation()
                line._compute_conformity_status()
            
            record._compute_overall_result()
            record._compute_overall_conformity()
            
            record.state = 'calculated'
            

            auto_filled_fields = []
            if record.is_concrete_sample and not record.testing_date:
                record.testing_date = fields.Date.today()
                auto_filled_fields.append("📅 تاريخ الفحص")
            
            total_tests = len(record.result_line_ids.filtered(lambda l: not l.criterion_id.is_computed_field))
            computed_tests = len(record.result_line_ids.filtered(lambda l: l.criterion_id.is_computed_field))
            
            message_html = (
                "✅ <b>تم حساب النتائج بنجاح</b>"
                "<ul style='margin:6px 0 0 18px;padding:0;'>"
                f"<li>📊 إجمالي الفحوصات: {total_tests}</li>"
                f"<li>🧮 النتائج المحسوبة: {computed_tests}</li>"
                f"<li>📈 نسبة الإنجاز: {record.progress_percentage:.1%}</li>"
                + (f"<li>🔄 تم ملء الحقول تلقائياً: {', '.join(auto_filled_fields)}</li>" if auto_filled_fields else "")
                + "</ul>"
            )
            record.message_post(
                body=message_html,
                message_type='notification'
            )
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_show_test_details(self):
        """ عرض تفاصيل شاملة عن نتائج الفحص"""
        access_check = self._check_record_access("عرض التفاصيل")
        if access_check:
            return access_check
            
        details = self.get_test_result_details()
        result_icon = "" if details['status'] == 'pass' else "" if details['status'] == 'fail' else "⏳"

        message_lines = [
            f"🔬 مجموعة النتائج: {self.name}",
            f"{result_icon} النتيجة النهائية: {details['message']}",
            "",
            " الإحصائيات:",
            f"• إجمالي المعايير: {details['summary']['total_criteria']}",
            f"• المعايير المطابقة: {details['summary']['total_passed']} ({(details['summary']['total_passed']/details['summary']['total_criteria']*100):.1f}%)" if details['summary']['total_criteria'] > 0 else "• لا توجد معايير",
        ]

        if details['critical_criteria']['total'] > 0:
            message_lines.append("")
            message_lines.append(f" المعايير الحرجة: {details['critical_criteria']['passed']}/{details['critical_criteria']['total']} مطابقة ({details['critical_criteria']['compliance_rate']:.1f}%)")
            if details['critical_criteria']['failed'] > 0:
                message_lines.append(f" معايير حرجة فاشلة: {', '.join(details['critical_criteria']['failed_names'])}")

        if details['non_critical_criteria']['total'] > 0:
            message_lines.append(f" المعايير غير الحرجة: {details['non_critical_criteria']['passed']}/{details['non_critical_criteria']['total']} مطابقة ({details['non_critical_criteria']['compliance_rate']:.1f}%)")
            if details['non_critical_criteria']['failed'] > 0:
                message_lines.append(f" معايير غير حرجة فاشلة: {', '.join(details['non_critical_criteria']['failed_names'])}")

        message_text = "\n".join(message_lines)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f" تفاصيل الفحص",
                'message': message_text,
                'type': 'success' if details['status'] == 'pass' else 'warning' if details['status'] == 'fail' else 'info',
            }
        }

    def action_approve_results(self):
        """ اعتماد النتائج نهائياً مع التحقق من التوقيع"""
        access_check = self._check_record_access("اعتماد النتائج")
        if access_check:
            return access_check
        

        if self.state not in ['calculated', 'review']:
            raise ValidationError(_('يجب حساب النتائج أولاً قبل الاعتماد'))
        

        if not self.signature:

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('يتطلب توقيع إلكتروني'),
                    'message': _('يجب إضافة توقيع إلكتروني قبل اعتماد النتائج. يرجى الانتقال إلى تبويب "التوقيع الإلكتروني" وإضافة توقيعك.'),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        

        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now(),
            'approved_by': self.env.user.id,
            'signer_name': self.env.user.name
        })
        
        self._notify_customer_results_ready()
        
        self._update_flow_state()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_retest(self):
        """إعادة الفحص في حال عدم المطابقة. يبقى نفس السجل والارتباطات."""
        for record in self:
            if record.overall_result != 'fail':
                continue
            record.state = 'in_progress'
            record.overall_result = 'pending'

            for line in record.result_line_ids:
                line.is_compliant = False
                line.is_filled = False if line.criterion_id.is_input_field else True
                line.conformity_status = 'pending'

            FlowLine = record.env['lab.test.flow.line']
            flow_line = FlowLine.search([('result_set_id', '=', record.id)], limit=1)
            if flow_line:
                flow_line.state = 'running'

                following_lines = flow_line.flow_id.line_ids.filtered(lambda l: l.sequence > flow_line.sequence)
                for fl in following_lines:
                    if fl.result_set_id and fl.result_set_id.state in ('draft', 'in_progress'):
                        fl.result_set_id.unlink()
                    fl.result_set_id = False
                    fl.state = 'pending'

                flow_line.flow_id.current_step = flow_line.sequence
                flow_line.flow_id.state = 'in_progress'

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }



    def _notify_customer_results_ready(self):
        """إشعار العميل بجاهزية النتائج"""
        if self.sample_id and getattr(self.sample_id, 'partner_id', False):
            customer = self.sample_id.partner_id
            
            template = self.env.ref('appointment_products.email_template_lab_results_ready', raise_if_not_found=False)
            if template:
                template.send_mail(self.id, force_send=True)

    def _update_flow_state(self):
        """عند اكتمال/اعتماد مجموعة النتائج: وضع المرحلة كمنتهية واستدعاء المرحلة التالية"""
        FlowLine = self.env['lab.test.flow.line']
        for rs in self:
            flow_line = FlowLine.search([('result_set_id', '=', rs.id)], limit=1)
            if not flow_line:
                continue

            if flow_line.state != 'done':
                flow_line.mark_done()

            flow = flow_line.flow_id
            if flow:
                all_done = all(line.state == 'done' for line in flow.line_ids)
                if all_done:
                    flow.state = 'completed'
                    flow.message_post(body=_('تم إنهاء جميع المراحل 🎉'))
                elif flow.state != 'completed':
                    try:
                        flow.action_next_step()
                    except Exception:

                        pass

    def unlink(self):
        blocked_states = ('calculated', 'review', 'approved', 'completed')
        if any(rec.state in blocked_states for rec in self):
            raise UserError(_('لا يمكن حذف مجموعة النتائج بعد تأكيد الفحص. يمكنك أرشفتها بدلاً من ذلك.'))
        return super(LabResultSet, self).unlink()





    @api.constrains('result_line_ids')
    def _check_timer_constraints(self):
        """التحقق من قيود المؤقت قبل الحفظ"""
        for record in self:
            if record.timer_start and record.timer_status == 'running':
                locked_criteria = record.template_id.criterion_ids.filtered(
                    lambda c: c.timer_scope == 'per_set' and c.lock_during_wait
                )
                if locked_criteria:
                    raise ValidationError(
                        _("لا يمكن حفظ البيانات أثناء تشغيل المؤقت.\n"
                          "الوقت المتبقي: %s\n"
                          "المعايير المقفلة: %s") % (
                            record.timer_remaining_display,
                            ', '.join(locked_criteria.mapped('name'))
                        )
                    )

    def write(self, vals):
        """منع تعديل الحقول المقفلة أثناء المؤقت"""
        
        if 'result_line_ids' in vals or any(k.startswith('value_') for k in vals.keys()):
            self._check_timer_lock_before_save()
        
        if 'result_line_ids' in vals:
            for record in self:
                if record.timer_start and record.timer_status == 'running':
                    locked_criteria = record.template_id.criterion_ids.filtered(
                        lambda c: c.timer_scope == 'per_set' and c.lock_during_wait
                    )
                    
                    if locked_criteria:
                        for line_vals in vals.get('result_line_ids', []):
                            if isinstance(line_vals, (list, tuple)) and len(line_vals) >= 3:
                                line_data = line_vals[2] if line_vals[0] in (0, 1) else line_vals[1]
                                if isinstance(line_data, dict) and 'value_numeric' in line_data:
                                    if line_vals[0] == 1:
                                        line_id = line_vals[1]
                                        line = self.env['lab.result.line'].browse(line_id)
                                        if line.criterion_id in locked_criteria:
                                            raise ValidationError(
                                                _(" لا يمكن تعديل القيمة الرقمية للمعيار '%s' أثناء تشغيل المؤقت!\n\n"
                                                  " الوقت المتبقي: %s\n"
                                                  " يرجى الانتظار حتى انتهاء المؤقت.") % (
                                                    line.criterion_id.name,
                                                    record.timer_remaining_display
                                                )
                                            )
                                    elif line_vals[0] == 0:
                                        criterion_id = line_data.get('criterion_id')
                                        if criterion_id:
                                            criterion = self.env['lab.test.criterion'].browse(criterion_id)
                                            if criterion in locked_criteria:
                                                raise ValidationError(
                                                    _(" لا يمكن إدخال القيمة الرقمية للمعيار '%s' أثناء تشغيل المؤقت!\n\n"
                                                      " الوقت المتبقي: %s\n"
                                                      " يرجى الانتظار حتى انتهاء المؤقت.") % (
                                                        criterion.name,
                                                        record.timer_remaining_display
                                                    )
                                                )
        
        value_fields = ['result_line_ids']
        if any(field in vals for field in value_fields):
            if not self.start_date:
                vals['start_date'] = fields.Datetime.now()
            if not self.technician_id:
                vals['technician_id'] = self.env.user.id
        
        res = super().write(vals)
        
        if 'testers_ids' in vals:
            for record in self:
                old_testers = set()
                if hasattr(record, '_origin') and record._origin.exists():
                    old_testers = set(record._origin.testers_ids.ids)
                
                current_testers = set(record.testers_ids.ids)
                added_testers = current_testers - old_testers
                
                if added_testers:
                    added_users = self.env['res.users'].browse(list(added_testers))
                    for user in added_users:
                        record.message_post(
                            body=f"🔔 تم تكليف {user.name} بفحص العينة: {record.sample_id.name}<br/>"
                                 f"📋 قالب الفحص: {record.template_id.name}<br/>"
                                 f"📍 حالة الفحص: {dict(record._fields['state'].selection).get(record.state, record.state)}<br/>"
                                 f"📊 نسبة الإنجاز: {record.progress_percentage:.1%}",
                            message_type='comment',
                            subtype_id=self.env.ref('mail.mt_note').id
                        )
                        
                        record.message_post(
                            body=f"🔬 <strong>تكليف مخبري شخصي</strong><br/>"
                                 f"تم تكليفك بفحص العينة: <strong>{record.sample_id.name}</strong><br/>"
                                 f"📋 قالب الفحص: {record.template_id.name}<br/>"
                                 f"📍 حالة الفحص: {dict(record._fields['state'].selection).get(record.state, record.state)}<br/>"
                                 f"📊 نسبة الإنجاز: {record.progress_percentage:.1%}<br/>"
                                 f"🔗 <a href='/web#id={record.id}&model=lab.result.set&view_type=form'>عرض الفحص</a>",
                            message_type='notification',
                            partner_ids=[user.partner_id.id],
                            subject=f"تكليف مخبري: {record.sample_id.name}",
                            subtype_id=self.env.ref('mail.mt_comment').id
                        )
        
        if 'result_line_ids' in vals or 'state' in vals or any(k.startswith('value_') for k in vals.keys()):
            for record in self:
                record._compute_calculated_criteria()
                record._compute_summary_criteria()
                record._compute_statistics()
                record._compute_overall_result()
                record._compute_overall_conformity()
                record._compute_criteria_statistics()
        
        return res




        
    def action_return_to_kanban(self):
        """العودة إلى قائمة الفحوصات المرتبطة بنفس خطة الفحص"""

        flow_line = self.env['lab.test.flow.line'].search([('result_set_id', '=', self.id)], limit=1)
        
        if flow_line and flow_line.flow_id:
            flow = flow_line.flow_id
            result_set_ids = flow.line_ids.mapped('result_set_id').ids
            
            return {
                'type': 'ir.actions.act_window',
                'name': f'📊 مجموعات نتائج الفحص: {flow.name}',
                'res_model': 'lab.result.set',
                'view_mode': 'kanban,list,form',
                'domain': [('id', 'in', result_set_ids)],
                'target': 'current',
                'context': {'default_sample_id': flow.sample_id.id},
            }
        else:

            return {
                'type': 'ir.actions.act_window',
                'name': f'📊 مجموعات نتائج العينة: {self.sample_id.name}',
                'res_model': 'lab.result.set',
                'view_mode': 'kanban,list,form',
                'domain': [('sample_id', '=', self.sample_id.id)],
                'target': 'current',
            }
    
    timer_completion_notified = fields.Boolean(
        string='تم إرسال إشعار اكتمال المؤقت',
        default=False,
        copy=False,
        help='يُستخدم داخلياً لمنع تكرار إشعارات اكتمال المؤقت'
    )
    
    testers_ids = fields.Many2many(
        'res.users',
        'lab_result_set_tester_rel',
        'result_set_id',
        'user_id',
        string='المكلفون بالفحص',
        help='المستخدمون المكلّفون بفحص هذه العينة'
    )
    

    signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True,
        help='توقيع المعتمد على هذه النتائج'
    )
    
    signer_name = fields.Char(
        string='اسم الموقع',
        readonly=True,
        help='اسم الشخص الذي وقع على هذه النتائج'
    )
    
    is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_is_signed',
        store=True,
        help='يبين ما إذا كان هناك توقيع على هذه النتائج'
    )
    
    is_manager = fields.Boolean(
        string='مدير المختبر',
        compute='_compute_is_manager',
        help='يحدد إذا كان المستخدم الحالي مدير مختبر أم لا'
    )
    
    bitumen_type = fields.Char(
        string='نوع القير',
        compute='_compute_bitumen_type',
        store=False,
        help='يظهر نوع القير (أساس أو تسطيح) إذا كان المنتج قير'
    )
    
    # --- Approval fields ---
    approval_date = fields.Datetime(
        string='تاريخ الاعتماد',
        readonly=True,
        tracking=True,
        help='تاريخ ووقت اعتماد النتائج'
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='معتمد بواسطة',
        readonly=True,
        tracking=True,
        help='المستخدم الذي اعتمد النتائج'
    )
    
    @api.depends('signature')
    def _compute_is_signed(self):
        """حساب ما إذا كان التوقيع موجود"""
        for record in self:
            record.is_signed = bool(record.signature)
            if record.signature and not record.signer_name:
                record.signer_name = record.env.user.name
    
    @api.depends('sample_id.product_id.default_code', 'sample_id.product_id.name')
    def _compute_bitumen_type(self):
        """تحديد نوع القير من المنتج"""
        for record in self:
            if record.sample_id and record.sample_id.product_id:
                product = record.sample_id.product_id
                product_code = product.default_code or ''
                product_name = product.name or ''
                
                if 'BASE' in product_code or 'أساس' in product_name:
                    record.bitumen_type = 'قير أساس'
                elif 'SURFACE' in product_code or 'تسطيح' in product_name:
                    record.bitumen_type = 'قير تسطيح'
                else:
                    record.bitumen_type = False
            else:
                record.bitumen_type = False
    
    def action_clear_signature(self):
        """مسح التوقيع"""
        if self.state in ('approved', 'completed'):
            raise ValidationError(_('لا يمكن مسح التوقيع بعد اعتماد النتائج.'))
        
        self.write({
            'signature': False,
            'signer_name': self.env.user.name
        })
        return True

    def action_return_to_sample_results(self):
        """العودة لعرض جميع نتائج العينة الأم"""
        if not self.sample_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'تحذير',
                    'message': 'هذه النتيجة غير مرتبطة بعينة',
                    'type': 'warning',
                }
            }
        
        return self.sample_id.action_view_result_sets()

    def write(self, vals):
        """تخصيص دالة الكتابة للتحقق من قيم الليونة"""
        _logger.info(f"LabResultSet.write called: vals={vals}")
        
        result = super(LabResultSet, self).write(vals)
        

        if 'result_line_ids' in vals:
            for rec in self:
                rec._check_softening_values()
        
        return result
    
    def _check_softening_values(self):
        """التحقق من قيم الليونة في جميع الأسطر"""
        _logger.info(f"_check_softening_values called for result_set {self.id}")
        
        softening_lines = self.result_line_ids.filtered(
            lambda line: line.criterion_id.code in ['SOFTENING_1', 'SOFTENING_2'] and line.value_numeric
        )
        
        _logger.info(f"Found {len(softening_lines)} softening lines with values")
        
        if len(softening_lines) >= 2:

            softening_1 = softening_lines.filtered(lambda l: l.criterion_id.code == 'SOFTENING_1')
            softening_2 = softening_lines.filtered(lambda l: l.criterion_id.code == 'SOFTENING_2')
            
            if softening_1 and softening_2:
                val1 = softening_1[0].value_numeric
                val2 = softening_2[0].value_numeric
                diff = abs(val1 - val2)
                
                _logger.info(f"Softening values: val1={val1}, val2={val2}, diff={diff}")
                
                if diff > 1.0:
                    warning_text = _(
                        "⚠️ تحذير فحص الليونة: الفرق بين القراءتين يتجاوز الحد المسموح!\n\n"
                        "🌡️ القراءة الأولى (درجة 1): %s°م\n"
                        "🌡️ القراءة الثانية (درجة 2): %s°م\n"
                        "📏 الفرق: %s°م (الحد الأقصى: 1.0°م)\n\n"
                        "⚠️ يُرجى مراجعة القراءات والتأكد من دقتها."
                    ) % (val1, val2, diff)
                    
                    _logger.warning(f"Softening warning set: {warning_text}")
                    self.softening_warning = warning_text
                else:
                    _logger.info(f"Softening validation passed - difference {diff} is within acceptable limit")
                    self.softening_warning = False


class LabResultLine(models.Model):
    """سطر نتيجة الفحص - يمثل فحصاً واحداً على عينة واحدة"""
    _name = 'lab.result.line'
    _description = 'سطر نتيجة الفحص'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'result_set_id, summary_sort_key, criterion_sort_type, criterion_timer_sequence, sequence, criterion_id, id'



    def init(self):
        """إنشاء الفهرس المركّب (result_set_id, is_filled, is_compliant) مرة واحدة فقط"""
        tools.create_index(
            self._cr,
            'lab_result_line_set_filled_cmp_idx',
            self._table,
            ['result_set_id', 'is_filled', 'is_compliant']
        )

    _check_company_auto = True

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
        index=True
    )
    

    _sql_constraints = [
        ('unique_result_line', 
         'unique(result_set_id, sample_no, criterion_id)', 
         'لا يمكن تكرار نفس المعيار لنفس العينة في نفس مجموعة النتائج!'),
        ('positive_sample_no', 
         'check(sample_no > 0)', 
         'رقم العينة يجب أن يكون أكبر من الصفر!'),
    ]

    result_set_id = fields.Many2one(
        'lab.result.set',
        string='مجموعة النتائج',
        required=True,
        ondelete='cascade',
        index=True  
    )
    
    sample_no = fields.Integer(
        string='رقم العينة',
        required=True,
        help='رقم العينة في المجموعة (1، 2، 3...)',
        index=True  
    )
    
    criterion_id = fields.Many2one(
        'lab.test.criterion',
        string='معيار الفحص',
        required=True,
        ondelete='restrict',
        index=True  
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10
    )
    
    value_numeric = fields.Float(string='القيمة الرقمية')
    value_text = fields.Text(string='القيمة النصية')
    value_selection = fields.Char(string='الاختيار')
    value_boolean = fields.Boolean(string='صح/خطأ')
    value_date = fields.Date(string='التاريخ')


    timer_scope = fields.Selection(related='criterion_id.timer_scope', store=True)
    waiting_unit = fields.Selection(related='criterion_id.waiting_unit', store=True)
    waiting_value = fields.Integer(related='criterion_id.waiting_value', store=True)
    lock_during_wait = fields.Boolean(related='criterion_id.lock_during_wait', store=True)

    criterion_timer_sequence = fields.Integer(
        string='تسلسل مؤقّت المعيار',
        related='criterion_id.timer_sequence',
        store=True,
        readonly=True,
    )

    line_timer_start = fields.Datetime(string='بداية مؤقّت السطر')
    line_timer_ready = fields.Datetime(string='نهاية مؤقّت السطر', compute='_compute_line_timer_ready', store=True)

    def _compute_line_timer_ready(self):
        for line in self:
            if line.timer_scope != 'per_line' or not line.line_timer_start or not line.waiting_unit or not line.waiting_value:
                line.line_timer_ready = False
                continue
            line.line_timer_ready = line.line_timer_start + relativedelta(**{line.waiting_unit: line.waiting_value})

    def action_start_line_timer(self):
        """بدء مؤقت السطر للمعايير التي تحتاج مؤقت per_line"""
        for line in self:
            if line.timer_scope == 'per_line' and not line.line_timer_start:
                line.write({'line_timer_start': fields.Datetime.now()})
        return True


    is_timer_done = fields.Boolean(string='انتهى المؤقّت', compute='_compute_timer_done', store=True)

    def _compute_timer_done(self):
        now = fields.Datetime.now()
        for line in self:
            if line.waiting_value and line.lock_during_wait:
                if line.timer_scope == 'per_line':
                    ready = line.line_timer_ready
                else:
                    ready = line.result_set_id.timer_ready
                line.is_timer_done = (ready and now >= ready)
            else:
                line.is_timer_done = True

    @api.depends('line_timer_start', 'line_timer_ready', 'result_set_id.timer_start', 'result_set_id.timer_ready')
    def _compute_timer_remaining(self):
        """حساب الوقت المتبقي للمؤقت (للسطر أو للمجموعة)"""
        now = fields.Datetime.now()
        for record in self:
            if record.timer_scope == 'per_line':
                start = record.line_timer_start
                ready = record.line_timer_ready
            else:
                start = record.result_set_id.timer_start
                ready = record.result_set_id.timer_ready

            if start and ready:
                if now >= ready:
                    record.timer_remaining = 0
                    record.timer_status = 'completed'
                else:
                    delta = ready - now
                    record.timer_remaining = delta.total_seconds()
                    record.timer_status = 'running'
            else:
                record.timer_remaining = 0
                record.timer_status = 'not_started'

    timer_remaining = fields.Float(
        string='الوقت المتبقي (بالثواني)',
        compute='_compute_timer_remaining',
        help='الوقت المتبقي للمؤقت بالثواني'
    )
    
    timer_status = fields.Selection([
        ('not_started', 'لم يبدأ'),
        ('running', 'يعمل'),
        ('completed', 'انتهى')
    ], string='حالة المؤقت', compute='_compute_timer_remaining')

    def _validate_softening_readings(self, new_value):
        """التحقق من صحة قراءات فحص الليونة"""
        _logger.info(f"_validate_softening_readings called: criterion={self.criterion_id.code}, new_value={new_value}, template={self.result_set_id.template_id.code if self.result_set_id.template_id else 'None'}")
        
        if not new_value or self.criterion_id.code not in ['SOFTENING_1', 'SOFTENING_2']:
            _logger.info(f"_validate_softening_readings: Skipping - new_value={new_value}, criterion_code={self.criterion_id.code}")
            return
            

        other_criteria_codes = ['SOFTENING_1', 'SOFTENING_2']
        other_criteria_codes.remove(self.criterion_id.code)
        
        _logger.info(f"_validate_softening_readings: Looking for other criterion: {other_criteria_codes[0]}, result_set_id={self.result_set_id.id}, sample_no={self.sample_no}")
        
        other_line = self.env['lab.result.line'].search([
            ('result_set_id', '=', self.result_set_id.id),
            ('sample_no', '=', self.sample_no),
            ('criterion_id.code', '=', other_criteria_codes[0])
        ], limit=1)
        
        _logger.info(f"_validate_softening_readings: Found other_line: {other_line.id if other_line else 'None'}, value_numeric={other_line.value_numeric if other_line else 'None'}")
        
        if other_line and other_line.value_numeric:
            diff = abs(new_value - other_line.value_numeric)
            _logger.info(f"_validate_softening_readings: Difference calculated: {diff} (new_value={new_value}, other_value={other_line.value_numeric})")
            
            if diff > 1.0:
                _logger.warning(f"_validate_softening_readings: WARNING - Difference {diff} exceeds limit of 1.0")
                warning_text = _(
                    "⚠️ تحذير فحص الليونة: الفرق بين القراءتين يتجاوز الحد المسموح!\n\n"
                    "🌡️ القراءة الأولى (درجة 1): %s°م\n"
                    "🌡️ القراءة الثانية (درجة 2): %s°م\n"
                    "📏 الفرق: %s°م (الحد الأقصى المسموح: 1.0°م)\n\n"
                    "📋 يرجى مراجعة القيم وإعادة القياس حسب معيار ASTM D36."
                ) % (
                    other_line.value_numeric if self.criterion_id.code == 'SOFTENING_2' else new_value,
                    new_value if self.criterion_id.code == 'SOFTENING_2' else other_line.value_numeric,
                    diff
                )

                self.result_set_id.softening_warning = warning_text
            else:
                _logger.info(f"_validate_softening_readings: Validation passed - difference {diff} is within acceptable limit")
                
                self.result_set_id.softening_warning = False
        else:
            _logger.info("_validate_softening_readings: No validation needed - other reading not found or empty")

    def write(self, vals):
        _logger.info(f"LabResultLine.write called: vals={vals}, context={self.env.context}")
        if vals and not self.env.context.get('bypass_timer_lock'):
            value_fields = ['value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date']
            has_value_changes = any(field in vals for field in value_fields)
            _logger.info(f"write: has_value_changes={has_value_changes}")
            
            if has_value_changes:
                for rec in self:
                    _logger.info(f"write: Processing record {rec.id}, criterion={rec.criterion_id.code if rec.criterion_id else 'None'}")
                    if rec.result_set_id.state != 'in_progress':
                        raise ValidationError(_(
                            'لا يمكن تعديل القيم إلا بعد بدء الفحص!\n\n'
                            'الحالة الحالية: %s\n'
                            'يجب الضغط على زر "بدء الفحص" أولاً لتمكين الكتابة في الجدول.'
                        ) % dict(rec.result_set_id._fields['state'].selection).get(rec.result_set_id.state, rec.result_set_id.state))
                    

                    _logger.info(f"write: Checking softening validation - value_numeric in vals: {'value_numeric' in vals}, criterion_code: {rec.criterion_id.code if rec.criterion_id else 'None'}")
                    if 'value_numeric' in vals and rec.criterion_id.code in ['SOFTENING_1', 'SOFTENING_2']:
                        _logger.info(f"write: Calling _validate_softening_readings for criterion {rec.criterion_id.code} with value: {vals.get('value_numeric')}")
                        rec._validate_softening_readings(vals.get('value_numeric'))

                    if rec.lock_during_wait and not rec.is_timer_done and not rec.result_set_id.template_id.allow_parallel_tests:
                        if rec.timer_scope == 'per_line':
                            timer_type = "مؤقت السطر"
                            remaining_time = rec.line_timer_ready - fields.Datetime.now() if rec.line_timer_ready else None
                        else:
                            timer_type = "مؤقت المجموعة"
                            remaining_time = rec.result_set_id.timer_ready - fields.Datetime.now() if rec.result_set_id.timer_ready else None
                        
                        if remaining_time and remaining_time.total_seconds() > 0:
                            hours = int(remaining_time.total_seconds() // 3600)
                            minutes = int((remaining_time.total_seconds() % 3600) // 60)
                            seconds = int(remaining_time.total_seconds() % 60)
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                            raise ValidationError(_(
                                '🔒 لا يُسمح بتعديل القيم قبل انتهاء %s!\n\n'
                                '⏰ الوقت المتبقي: %s\n'
                                '📋 المعيار: %s\n'
                                '⏳ يرجى الانتظار حتى انتهاء المؤقت قبل إدخال القيم.'
                            ) % (timer_type, time_str, rec.criterion_id.name))
        
        result = super().write(vals)
        

        if vals and not self.env.context.get('bypass_compute'):
            value_fields = ['value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date']
            if any(field in vals for field in value_fields):

                result_sets = self.mapped('result_set_id')
                for result_set in result_sets:
                    result_set.with_context(bypass_compute=True)._compute_calculated_criteria()
        
        return result
    
    is_compliant = fields.Boolean(
        string='مطابق للمواصفة',
        compute='_compute_compliance',
        store=True
    )
    
    is_filled = fields.Boolean(
        string='تم الملء',
        compute='_compute_is_filled',
        store=True
    )
    
    notes = fields.Text(string='ملاحظات')

    technician_id = fields.Many2one(
        'res.users',
        string='الفني'
    )
    
    last_modified_date = fields.Datetime(
        string='تاريخ آخر تعديل',
        readonly=True,
        help='تاريخ ووقت آخر تعديل للقيم الرقمية'
    )




    is_critical = fields.Boolean(
        string='حرج',
        related='criterion_id.is_critical',
        store=True,
        readonly=True,
        help='يشير إلى أن هذا المعيار حرج ويؤثر على النتيجة النهائية'
    )
    
    is_computed = fields.Boolean(
        string='محسوب',
        related='criterion_id.is_computed_field',
        store=True,
        readonly=True
    )
    
    criterion_sort_type = fields.Integer(
        string='نوع الفرز',
        compute='_compute_criterion_sort_type',
        store=True,
        readonly=True,
        help='نوع المعيار للفرز: 0=عام (أولاً)، 1=رقمي، 2=محسوب، 4=تلخيصي (أخيراً)'
    )
    
    summary_sort_key = fields.Integer(
        string='مفتاح فرز التلخيص',
        compute='_compute_summary_sort_key',
        store=True,
        readonly=True,
        help='مفتاح خاص لجعل المعايير التلخيصية تظهر في النهاية'
    )
    
    @api.depends('criterion_id.is_computed_field', 'criterion_id.is_summary_field', 'criterion_id.is_global')
    def _compute_criterion_sort_type(self):
        """حساب نوع المعيار للفرز
        0 = معايير عامة (is_global=True) لتظهر أولاً
        1 = معايير رقمية (غير محسوبة وغير عامة)
        2 = معايير محسوبة
        4 = معايير تلخيصية (محسوبة + تلخيصية) لتظهر أخيراً عبر summary_sort_key أيضاً
        """
        for line in self:
            if line.criterion_id:
                if line.criterion_id.is_summary_field:
                    line.criterion_sort_type = 4
                elif line.criterion_id.is_global:
                    line.criterion_sort_type = 0
                elif line.criterion_id.is_computed_field:
                    line.criterion_sort_type = 2
                else:
                    line.criterion_sort_type = 1
            else:
                line.criterion_sort_type = 1  
    

    @api.depends('criterion_id.is_summary_field', 'sample_no')
    def _compute_summary_sort_key(self):
        """حساب مفتاح فرز خاص لجعل المعايير التلخيصية تظهر في النهاية
        للمعايير العامة: sample_no (فرز عادي)
        للمعايير التلخيصية: 9999 (فرز في النهاية)
        """
        for line in self:
            if line.criterion_id and line.criterion_id.is_summary_field:
                line.summary_sort_key = 9999
            else:
                line.summary_sort_key = line.sample_no or 0
    
    sample_identifier = fields.Char(
        string='معرف العينة',
        compute='_compute_sample_identifier',
        help='معرف العينة (مثل: عينة 1، عينة 2)'
    )
    
    criterion_name = fields.Char(
        string='اسم المعيار',
        related='criterion_id.name',
        readonly=True
    )
    
    data_type = fields.Selection(
        string='نوع البيانات',
        related='criterion_id.test_type',
        readonly=True
    )
    
    unit_of_measure = fields.Char(
        string='وحدة القياس',
        related='criterion_id.uom_id.name',
        readonly=True
    )
    
    criterion_code = fields.Char(
        string='رمز المعيار',
        related='criterion_id.code',
        readonly=True
    )

    test_type = fields.Selection(
        string='نوع الفحص',
        related='criterion_id.test_type',
        readonly=True
    )

    min_limit = fields.Float(
        string='الحد الأدنى',
        related='criterion_id.min_value',
        readonly=True
    )

    max_limit = fields.Float(
        string='الحد الأعلى',
        related='criterion_id.max_value',
        readonly=True
    )

    target_value = fields.Float(
        string='القيمة المستهدفة',
        related='criterion_id.target_value',
        readonly=True
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس (M2O)',
        related='criterion_id.uom_id',
        readonly=True
    )

    deviation_percentage = fields.Float(
        string='نسبة الانحراف %',
        compute='_compute_compliance_and_deviation',
        store=True
    )

    value_computed = fields.Float(
        string='القيمة المحسوبة (Alias)',
        related='result_value_computed',
        readonly=True
    )
    
    reference_standard = fields.Char(
        string='المعيار المرجعي',
        related='criterion_id.standard_code',
        readonly=True
    )
    
    conformity_status = fields.Selection([
        ('pass', 'مطابق'),
        ('fail', 'غير مطابق'),
        ('pending', 'في الانتظار')
    ], string='حالة المطابقة', compute='_compute_conformity_status')
    
    result_value_numeric = fields.Float(
        string='القيمة الرقمية',
        compute='_compute_result_values',
        inverse='_inverse_result_value_numeric'
    )
    
    result_value_text = fields.Text(
        string='القيمة النصية',
        compute='_compute_result_values',
        inverse='_inverse_result_value_text'
    )
    
    result_value_selection = fields.Char(
        string='الاختيار',
        compute='_compute_result_values',
        inverse='_inverse_result_value_selection'
    )
    
    result_value_boolean = fields.Boolean(
        string='صح/خطأ',
        compute='_compute_result_values',
        inverse='_inverse_result_value_boolean'
    )
    
    result_value_date = fields.Date(
        string='التاريخ',
        compute='_compute_result_values',
        inverse='_inverse_result_value_date'
    )
    
    result_value_computed = fields.Float(
        string='القيمة المحسوبة',
        compute='_compute_result_computed'
    )
    
    result_value = fields.Char(
        string='القيمة',
        compute='_compute_result_value'
    )
    
    min_value = fields.Float(
        string='الحد الأدنى',
        related='criterion_id.min_value',
        readonly=True
    )
    
    max_value = fields.Float(
        string='الحد الأعلى',
        related='criterion_id.max_value',
        readonly=True
    )
    
    computation_formula = fields.Text(
        string='معادلة الحساب',
        related='criterion_id.computation_formula',
        readonly=True
    )
    


    @api.depends('sample_no', 'criterion_id.is_summary_field', 'criterion_id.is_global', 'criterion_id.is_computed_field')
    def _compute_sample_identifier(self):
        for line in self:
            if line.criterion_id and line.criterion_id.is_summary_field:
                line.sample_identifier = "النتيجة"
            elif line.criterion_id and line.criterion_id.is_global:
                line.sample_identifier = "عام" 
            elif line.criterion_id and line.criterion_id.is_computed_field:

                line.sample_identifier = f"ن-{line.sample_no}"
            else:
                line.sample_identifier = f"عينة {line.sample_no}"
    


    @api.depends('is_compliant', 'is_filled')
    def _compute_conformity_status(self):
        for line in self:
            if not line.is_filled:
                line.conformity_status = 'pending'
            elif line.is_compliant:
                line.conformity_status = 'pass'
            else:
                line.conformity_status = 'fail'
    
    @api.depends('value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date')
    def _compute_result_values(self):
        for line in self:
            line.result_value_numeric = line.value_numeric
            line.result_value_text = line.value_text
            line.result_value_selection = line.value_selection
            line.result_value_boolean = line.value_boolean
            line.result_value_date = line.value_date
    
    def _inverse_result_value_numeric(self):
        for line in self:
            if line.value_numeric != line.result_value_numeric:
                line.write({
                    'value_numeric': line.result_value_numeric,
                    'technician_id': self.env.user.id,
                    'last_modified_date': fields.Datetime.now()
                })
    
    def _inverse_result_value_text(self):
        for line in self:
            if line.value_text != line.result_value_text:
                line.write({
                    'value_text': line.result_value_text,
                    'technician_id': self.env.user.id,
                    'last_modified_date': fields.Datetime.now()
                })
    
    def _inverse_result_value_selection(self):
        for line in self:
            if line.value_selection != line.result_value_selection:
                line.write({
                    'value_selection': line.result_value_selection,
                    'technician_id': self.env.user.id,
                    'last_modified_date': fields.Datetime.now()
                })
    
    def _inverse_result_value_boolean(self):
        for line in self:
            if line.value_boolean != line.result_value_boolean:
                line.write({
                    'value_boolean': line.result_value_boolean,
                    'technician_id': self.env.user.id,
                    'last_modified_date': fields.Datetime.now()
                })
    
    def _inverse_result_value_date(self):
        for line in self:
            if line.value_date != line.result_value_date:
                line.write({
                    'value_date': line.result_value_date,
                    'technician_id': self.env.user.id,
                    'last_modified_date': fields.Datetime.now()
                })
    
    @api.depends('criterion_id.is_computed_field', 'value_numeric')
    def _compute_result_computed(self):
        for line in self:
            if line.criterion_id.is_computed_field:
                line.result_value_computed = line.value_numeric
            else:
                line.result_value_computed = 0.0
    
    @api.depends('value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date')
    def _compute_result_value(self):
        for line in self:
            line.result_value = line.get_display_value()
    
    @api.depends('value_numeric', 'value_text', 'value_selection', 'value_boolean', 
                 'value_date', 'result_set_id.state', 'criterion_id.test_type')
    def _compute_is_filled(self):
        """حساب حالة اكتمال الإدخال بدقة أكبر"""
        for line in self:
            if line.result_set_id.state in ['completed', 'approved']:
                line.is_filled = True
                continue
                
            test_type = line.criterion_id.test_type
            
            if test_type == 'numeric':
                line.is_filled = line.value_numeric is not None
            elif test_type == 'text':
                line.is_filled = bool(line.value_text and line.value_text.strip())
            elif test_type == 'selection':
                line.is_filled = bool(line.value_selection and line.value_selection.strip())
            elif test_type == 'boolean':
                line.is_filled = True
            elif test_type == 'date':
                line.is_filled = bool(line.value_date)
            elif test_type == 'computed':

                line.is_filled = line.value_numeric is not None and line.value_numeric != 0
            else:
                line.is_filled = False
    
            if not line.is_filled and hasattr(line, '_context') and line._context.get('debug_progress'):
                _logger.debug(
                    f"Line {line.criterion_id.name} (type: {test_type}) is not filled. Values: "
                    f"numeric={line.value_numeric}, text='{line.value_text}', "
                    f"selection='{line.value_selection}', boolean={line.value_boolean}, "
                    f"date={line.value_date}"
                )
    
    @api.depends('value_numeric', 'criterion_id.min_value', 'criterion_id.max_value', 
                 'value_text', 'value_selection', 'value_boolean', 'value_date', 'is_filled',
                 'result_set_id.sample_id.task_id.reference_min_limit')
    def _compute_compliance(self):
        """حساب مطابقة القيم للحدود المسموح بها - مع دعم جميع أنواع البيانات"""
        for line in self:
            
            if line._is_experimental_sample():
                line.is_compliant = True
                continue
                
            if not line.is_filled:
                line.is_compliant = False
                continue
            
            test_type = line.test_type
            
            if test_type == 'numeric':
                if line.criterion_id.code == 'EFFLOR_GRADE' and line.result_set_id.sample_id.sample_subtype_id:
                    sample_subtype = line.result_set_id.sample_id.sample_subtype_id
                    efflorescence_value = line.value_numeric
                    
                    line.is_compliant = sample_subtype.is_efflorescence_value_allowed(efflorescence_value)
                    
                    if hasattr(line.result_set_id, '_log_efflorescence_check'):
                        allowed_values = sample_subtype.get_allowed_efflorescence_values_list()
                        line.result_set_id.message_post(
                            body=f"فحص التزهر: القيمة {efflorescence_value}، المسموح: {allowed_values}، النتيجة: {'مطابق' if line.is_compliant else 'غير مطابق'}",
                            message_type='comment'
                        )
                if line.criterion_id.code in ('FLASH_IGNITION_POINT', 'FLASH_POINT'):
                    line.is_compliant = line._check_flash_point_compliance()
                elif line.criterion_id.code == 'PENTEST_AVG':
                    line.is_compliant = line._check_penetration_compliance()
                elif line.result_set_id.is_concrete_sample and line.criterion_id.code in ['COMP_STRENGTH_CONCRETE', 'AVG_COMP_STRENGTH_CONCRETE']:
                    task = getattr(line.result_set_id.sample_id, 'task_id', False)
                    if task and hasattr(task, 'reference_min_limit') and task.reference_min_limit:
                        try:
                            ref_min = float(task.reference_min_limit)
                            min_margin = float(line.env['ir.config_parameter'].sudo().get_param('appointment_products.min_limit_margin', default='3'))
                            line.is_compliant = line.value_numeric >= (ref_min - min_margin)
                        except Exception:
                            if line.min_limit is not False and line.max_limit is not False:
                                line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                            elif line.min_limit is not False:
                                line.is_compliant = line.value_numeric >= line.min_limit
                            elif line.max_limit is not False:
                                line.is_compliant = line.value_numeric <= line.max_limit
                            else:
                                line.is_compliant = True
                    else:
                        if line.min_limit is not False and line.max_limit is not False:
                            line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                        elif line.min_limit is not False:
                            line.is_compliant = line.value_numeric >= line.min_limit
                        elif line.max_limit is not False:
                            line.is_compliant = line.value_numeric <= line.max_limit
                        else:
                            line.is_compliant = True
                else:
                    if line.min_limit is not False and line.max_limit is not False:
                        line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                    elif line.min_limit is not False:
                        line.is_compliant = line.value_numeric >= line.min_limit
                    elif line.max_limit is not False:
                        line.is_compliant = line.value_numeric <= line.max_limit
                    else:
                        line.is_compliant = True
                        
            elif test_type in ('text', 'selection'):
                line.is_compliant = True
                
            elif test_type == 'boolean':
                line.is_compliant = True
                
            elif test_type == 'date':
                line.is_compliant = True
                
            elif test_type == 'computed':
                if line.criterion_id.code == 'PENTEST_AVG':
                    line.is_compliant = line._check_penetration_compliance()
                    continue
                elif line.criterion_id.code == 'DUCTILITY_TEST_AVG':
                    line.is_compliant = line._check_ductility_compliance()
                    continue
                elif line.criterion_id.code in ['SOFTENING_RESULT', 'PENTEST_RESULT', 'DUCTILITY_RESULT']:
                    if line.value_numeric == -1:
                        line.is_compliant = False
                    else:
                        line.is_compliant = True
                    continue
                elif line.criterion_id.code in ['COMPACTION_RATIO', 'COMPACTION_RATIO_AVG']:
                    try:
                        ref_val = None
                        if getattr(line.result_set_id, 'core_compaction_ratio_reference', False):
                            ref_val = float(line.result_set_id.core_compaction_ratio_reference)
                        else:
                            task = getattr(line.result_set_id.sample_id, 'task_id', False)
                            if task and getattr(task, 'core_compaction_ratio', False):
                                ref_val = float(task.core_compaction_ratio)
                        if ref_val is None:
                            line.is_compliant = True
                        else:
                            val = float(line.value_numeric or 0)
                            line.is_compliant = (val >= ref_val)
                    except Exception:
                        line.is_compliant = True
                    continue
                elif line.criterion_id.code == 'CORE_THICKNESS_OVERALL_AVG':
                    try:
                        ref_val = None
                        if getattr(line.result_set_id, 'reference_general_limit', False):
                            ref_val = float(line.result_set_id.reference_general_limit)
                        else:
                            task = getattr(line.result_set_id.sample_id, 'task_id', False)
                            if task and getattr(task, 'reference_general_limit', False):
                                ref_val = float(task.reference_general_limit)

                        if ref_val is None:
                            line.is_compliant = True
                        else:
                            tol = float(line.env['ir.config_parameter'].sudo().get_param(
                                'appointment_products.core_thickness_tolerance', default='0.3'
                            ))
                            avg_val = float(line.value_numeric or 0)
                            line.is_compliant = (avg_val >= (ref_val - tol))
                    except Exception:
                        line.is_compliant = True
                    continue
                
                if line.result_set_id.is_concrete_sample and line.criterion_id.code in ['COMP_STRENGTH_CONCRETE', 'AVG_COMP_STRENGTH_CONCRETE']:
                    task = getattr(line.result_set_id.sample_id, 'task_id', False)
                    if task and hasattr(task, 'reference_min_limit') and task.reference_min_limit:
                        try:
                            ref_min = float(task.reference_min_limit)
                            min_margin = float(line.env['ir.config_parameter'].sudo().get_param('appointment_products.min_limit_margin', default='3'))
                            line.is_compliant = line.value_numeric >= (ref_min - min_margin)
                        except Exception:
    
                            if line.value_numeric == 0:
                                line.is_compliant = True 
                            elif line.min_limit is not False and line.max_limit is not False:
                                line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                            elif line.min_limit is not False:
                                line.is_compliant = line.value_numeric >= line.min_limit
                            elif line.max_limit is not False:
                                line.is_compliant = line.value_numeric <= line.max_limit
                            else:
                                line.is_compliant = True
                    else:

                        if line.value_numeric == 0:
                            line.is_compliant = True 
                        elif line.min_limit is not False and line.max_limit is not False:
                            line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                        elif line.min_limit is not False:
                            line.is_compliant = line.value_numeric >= line.min_limit
                        elif line.max_limit is not False:
                            line.is_compliant = line.value_numeric <= line.max_limit
                        else:
                            line.is_compliant = True
                else:

                    if line.value_numeric == 0:
                        line.is_compliant = True 
                    elif line.min_limit is not False and line.max_limit is not False:
                        line.is_compliant = line.min_limit <= line.value_numeric <= line.max_limit
                    elif line.min_limit is not False:
                        line.is_compliant = line.value_numeric >= line.min_limit
                    elif line.max_limit is not False:
                        line.is_compliant = line.value_numeric <= line.max_limit
                    else:
                        line.is_compliant = True
            else:
                line.is_compliant = True
    
    def _is_experimental_sample(self):
        """فحص إذا كانت النتيجة من عينة 7 أيام أو احتياط (تجريبية)"""
        self.ensure_one()
        
        if not self.result_set_id or not self.result_set_id.sample_id:
            return False
            
        sample = self.result_set_id.sample_id
        
        if not self.result_set_id.is_concrete_sample:
            return False
            
        move_lines = self.env['stock.move.line']
        
        if sample.lab_code:
            move_lines = self.env['stock.move.line'].search([
                ('field_code', '=', sample.lab_code),
                ('age_days', 'in', ['7', 'reserve'])
            ])
        
        if not move_lines and sample.field_serial:
            move_lines = self.env['stock.move.line'].search([
                ('field_serial', '=', sample.field_serial),
                ('age_days', 'in', ['7', 'reserve'])
            ])
            
        return bool(move_lines)
    
    def get_numeric_value(self):
        """إرجاع القيمة الرقمية حسب نوع البيانات"""
        test_type = self.criterion_id.test_type
        
        if test_type == 'numeric':
            return self.value_numeric or 0
        elif test_type == 'boolean':
            return 1 if self.value_boolean else 0
        else:
            return 0
    
    def get_display_value(self):
        """الحصول على القيمة المعروضة للنتيجة"""
        self.ensure_one()
        if self.test_type == 'numeric':
            value = self.value_numeric

            if self.criterion_id.code == 'EFFLOR_GRADE':
                if self.result_set_id.sample_id.sample_subtype_id:
                    return self.result_set_id.sample_id.sample_subtype_id.get_efflorescence_display_name(value)
                else:
                    if value == 1:
                        return _("لا يوجد")
                    elif value == 2:
                        return _("خفيف")
                    elif value == 3:
                        return _("متوسط")
                    elif value == 4:
                        return _("عالي")
                
            if self.uom_id:
                return f"{value} {self.uom_id.name}"
            return str(value)
        elif self.test_type == 'text':
            return self.value_text or ''
        elif self.test_type == 'computed':
            return str(self.result_value_computed)
        else:
            return ''
    
    def set_value(self, value):
        """تعيين القيمة حسب نوع البيانات"""
        test_type = self.criterion_id.test_type
        
        if test_type == 'numeric':
            self.value_numeric = float(value) if value else 0
        elif test_type == 'text':
            self.value_text = str(value) if value else ''
        elif test_type == 'selection':
            self.value_selection = str(value) if value else ''
        elif test_type == 'boolean':
            self.value_boolean = bool(value)
        elif test_type == 'date':
            self.value_date = value if isinstance(value, (str, type(None))) else str(value)
        else:
            pass
    
    def _is_value_complete(self):
        """فحص اكتمال القيمة حسب نوع الفحص (بعد إزالة المؤقت)"""
        self.ensure_one()

        if self.criterion_id.test_type == 'numeric':
            return self.value_numeric not in (False, None)
        elif self.criterion_id.test_type == 'text':
            return bool(self.value_text and self.value_text.strip())
        elif self.criterion_id.test_type == 'selection':
            return bool(self.value_selection)
        elif self.criterion_id.test_type == 'boolean':

            return self.value_boolean is not None
        elif self.criterion_id.test_type == 'date':
            return bool(self.value_date)
        elif self.criterion_id.test_type == 'computed':
            return bool(self.result_value_computed)
        
        return False

    def _get_display_value_for_table(self):
        """الحصول على القيمة للعرض في الجدول الديناميكي"""
        self.ensure_one()
        
        if self.criterion_id.test_type == 'numeric':
            if self.unit_of_measure:
                return f"{self.value_numeric} {self.unit_of_measure}"
            return str(self.value_numeric) if self.value_numeric is not None else ''
        elif self.criterion_id.test_type == 'text':
            return self.value_text or ''
        elif self.criterion_id.test_type == 'selection':
            return self.value_selection or ''
        elif self.criterion_id.test_type == 'boolean':
            return 'نعم' if self.value_boolean else 'لا'
        elif self.criterion_id.test_type == 'date':
            return self.value_date.strftime('%Y-%m-%d') if self.value_date else ''
        elif self.criterion_id.test_type == 'computed':
            return str(self.result_value_computed) if self.result_value_computed else ''
        
        return ''

    def _compute_compliance_and_deviation(self):
        """حساب المطابقة والانحراف للواجهة"""
        for line in self:
            line._compute_compliance()
            
            if line.criterion_id.test_type in ('numeric', 'computed') and line.value_numeric is not None:
                if line.criterion_id.target_value:
                    deviation = abs(line.value_numeric - line.criterion_id.target_value)
                    line.deviation_percentage = (deviation / line.criterion_id.target_value) * 100 if line.criterion_id.target_value != 0 else 0
                else:
                    line.deviation_percentage = 0
            else:
                line.deviation_percentage = 0 
    
    def _check_flash_point_compliance(self):
        """التحقق من مطابقة نقطة الوميض حسب نوع القير"""
        if not self.value_numeric:
            return True 
            
        if not (self.result_set_id and self.result_set_id.sample_id):
            return True 
            
        sample = self.result_set_id.sample_id
        bitumen_type = getattr(sample, 'bitumen_type', None)
        
        if bitumen_type == 'قير تسطيح':
            min_required = 302 
        elif bitumen_type == 'قير أساس':
            min_required = 232 
        else:
            if self.min_limit is not None and self.min_limit is not False:
                return self.value_numeric >= self.min_limit
            return True
            
        return self.value_numeric >= min_required
    
    def _check_penetration_compliance(self):
        """التحقق من مطابقة متوسط الاختراق حسب نوع القير"""
        if not self.value_numeric:
            return True 
            
        if not (self.result_set_id.sample_id and self.result_set_id.sample_id.product_id):
            return True 
            
        product = self.result_set_id.sample_id.product_id
        product_code = product.default_code or ''
        product_name = product.name or ''
        
        penetration_value = self.value_numeric
        

        if 'SURFACE' in product_code or 'تسطيح' in product_name:

            valid_ranges = [
                (18, 60),
                (15, 35),
                (12, 25),
            ]
        elif 'BASE' in product_code or 'أساس' in product_name:
            valid_ranges = [
                (50, 100),
                (25, 50),
                (20, 40),
            ]
        else:
            if self.min_limit is not False and self.max_limit is not False:
                return self.min_limit <= self.value_numeric <= self.max_limit
            elif self.min_limit is not False:
                return self.value_numeric >= self.min_limit
            elif self.max_limit is not False:
                return self.value_numeric <= self.max_limit
            return True
            

        for min_val, max_val in valid_ranges:
            if min_val <= penetration_value <= max_val:
                return True
                

        return False
    
    def _check_ductility_compliance(self):
        """التحقق من مطابقة متوسط الاستطالة حسب نوع القير"""
        if not self.value_numeric:
            return True 
            
        if not (self.result_set_id.sample_id and self.result_set_id.sample_id.product_id):
            return True 
            
        product = self.result_set_id.sample_id.product_id
        product_code = product.default_code or ''
        product_name = product.name or ''
        
        ductility_value = self.value_numeric
        
        if 'SURFACE' in product_code or 'تسطيح' in product_name:
            min_limits = [10, 3, 2.5, 1.5] 
        elif 'BASE' in product_code or 'أساس' in product_name:
            min_limits = [30, 10, 2] 
        else:
            if self.min_limit is not False and self.max_limit is not False:
                return self.min_limit <= self.value_numeric <= self.max_limit
            elif self.min_limit is not False:
                return self.value_numeric >= self.min_limit
            elif self.max_limit is not False:
                return self.value_numeric <= self.max_limit
            return True
            
        for min_limit in min_limits:
            if ductility_value >= min_limit:
                return True
                
        return False
    
    def write(self, vals):
        value_fields = ['value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date']
        if any(field in vals for field in value_fields):
            vals['technician_id'] = self.env.user.id
            vals['last_modified_date'] = fields.Datetime.now()
        
        res = super().write(vals)
        

        if any(k.startswith('value_') for k in vals.keys()):
            affected_sets = self.filtered(lambda l: l.criterion_id.is_input_field).mapped('result_set_id')
            if affected_sets:
                affected_sets._compute_calculated_criteria()
                affected_sets._compute_statistics()
                affected_sets._compute_overall_result()
                affected_sets._compute_overall_conformity()
        return res



    @api.model_create_multi
    def create(self, vals_list):
        value_fields = ['value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date']
        for vals in vals_list:
            if any(field in vals and vals[field] for field in value_fields):
                vals['technician_id'] = self.env.user.id
                vals['last_modified_date'] = fields.Datetime.now()
        
        records = super().create(vals_list)
        records.mapped('result_set_id')._compute_calculated_criteria()
        return records

    @api.model
    def _update_dashboard_statistics(self):
        """This method is executed via server action/cron to update stored fields that depend on heavy calculations to ensure that the dashboards load fast."""
        active_sets = self.search([
            ('state', 'in', ['draft', 'in_progress', 'calculated', 'review']),
            ('active', '=', True),
        ])
        if not active_sets:
            return True

        active_sets._compute_statistics()
        active_sets._compute_criteria_statistics()
        active_sets._compute_overall_result()
        _logger.info("تم تحديث إحصاءات %s مجموعة نتائج نشطة", len(active_sets))
        return True
        
    def action_calculate_results(self):
        """حساب جميع النتائج تلقائياً"""
        if not self.exists():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'خطأ',
                    'message': 'السجل غير موجود أو تم حذفه',
                    'type': 'danger',
                }
            }
            
        for record in self:

            current_set_running_timers = []
            

            if record.timer_status == 'running':
                current_set_running_timers.append(f"مؤقت هذا الفحص - متبقي: {record.timer_remaining_display}")
            

            line_timers = record.result_line_ids.filtered(
                lambda l: l.timer_scope == 'per_line' and l.timer_status == 'running'
            )
            

            if current_set_running_timers or line_timers:
                running_timers = current_set_running_timers.copy()
                for line in line_timers:
                    remaining = line.timer_remaining if line.timer_remaining else 0
                    hours = int(remaining // 3600)
                    minutes = int((remaining % 3600) // 60)
                    seconds = int(remaining % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    running_timers.append(f"مؤقت {line.criterion_id.name} - متبقي: {time_str}")
                
                timers_text = '\n'.join(running_timers) if running_timers else "المؤقتات قيد التشغيل"
                
                raise ValidationError(
                    _(" لا يمكن حساب النتائج قبل انتهاء جميع المؤقتات!\n\n"
                      " المؤقتات الجارية:\n%s\n\n"
                      " يرجى الانتظار حتى انتهاء جميع المؤقتات قبل حساب النتائج.") % timers_text
                )
            
            for line in record.result_line_ids:
                line._compute_compliance_and_deviation()
                line._compute_conformity_status()
            
            record._compute_overall_result()
            record._compute_overall_conformity()
            
            record.state = 'calculated'
            
            auto_filled_fields = []
            if record.is_concrete_sample and not record.testing_date:
                record.testing_date = fields.Date.today()
                auto_filled_fields.append("تاريخ الفحص")
            
            
            total_tests = len(record.result_line_ids.filtered(lambda l: not l.criterion_id.is_computed_field))
            computed_tests = len(record.result_line_ids.filtered(lambda l: l.criterion_id.is_computed_field))
            
            message_parts = [
                f"تم حساب النتائج بنجاح",
                f"إجمالي الفحوصات: {total_tests}",
                f"النتائج المحسوبة: {computed_tests}",
                f"نسبة الإنجاز: {record.progress_percentage:.1%}"
            ]
            
            if auto_filled_fields:
                message_parts.append(f" تم ملء تلقائياً: {', '.join(auto_filled_fields)}")
            
            record.message_post(
                body="<br/>".join(message_parts),
                message_type='notification'
            )
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
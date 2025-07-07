# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class LabResultSet(models.Model):
    """مجموعة نتائج الفحص - تجميع كل النتائج المتعلقة بطلب فحص واحد"""
    _name = 'lab.result.set'
    _description = 'مجموعة نتائج الفحص'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

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
        tracking=True
    )
    
    template_id = fields.Many2one(
        'lab.test.template',
        string='قالب الفحص',
        required=True,
        ondelete='restrict',
        tracking=True
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
        ('submitted', 'تم الإرسال للمراجعة'),
        ('review', 'قيد المراجعة'),
        ('approved', 'معتمد'),
        ('completed', 'مكتملة'),
        ('cancelled', 'ملغية')
    ], string='الحالة', default='draft', tracking=True)
    
    start_date = fields.Datetime(
        string='تاريخ البدء',
        tracking=True
    )
    
    end_date = fields.Datetime(
        string='تاريخ الانتهاء',
        tracking=True
    )
    
    technician_id = fields.Many2one(
        'res.users',
        string='الفني المسؤول',
        tracking=True
    )
    
    result_line_ids = fields.One2many(
        'lab.result.line',
        'result_set_id',
        string='أسطر النتائج'
    )
    
    total_criteria = fields.Integer(
        string='إجمالي المعايير',
        compute='_compute_statistics'
    )
    
    completed_criteria = fields.Integer(
        string='المعايير المكتملة',
        compute='_compute_statistics'
    )
    
    progress_percentage = fields.Float(
        string='نسبة الإنجاز',
        compute='_compute_statistics'
    )
    
    overall_result = fields.Selection([
        ('pass', 'نجح'),
        ('fail', 'فشل'),
        ('pending', 'في الانتظار')
    ], string='النتيجة العامة', compute='_compute_overall_result', store=True)
    
    failed_criteria_count = fields.Integer(
        string='عدد المعايير الفاشلة',
        compute='_compute_overall_result'
    )
    
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
    ], string='حالة المطابقة العامة', compute='_compute_overall_conformity', store=True)
    
    quality_check_id = fields.Many2one(
        'quality.check',
        string='فحص الجودة',
        help='فحص الجودة المرتبط بهذه المجموعة'
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

    active = fields.Boolean(string='نشط', default=True, help='إلغاء التحديد لأرشفة مجموعة النتائج بدون حذفها.')
    
    active_timer_name = fields.Char(
        string='المؤقّت الحالي',
        compute='_compute_active_timer',
        store=False
    )

    active_timer_remaining = fields.Char(
        string='الوقت المتبقّي',
        compute='_compute_active_timer',
        store=False
    )

    has_active_timer = fields.Boolean(
        string='يوجد مؤقّت نشط',
        compute='_compute_active_timer',
        store=False
    )

    @api.model
    def create(self, vals):
        """إنشاء مجموعة نتائج جديدة مع توليد الأسطر تلقائياً
        بالإضافة إلى ختم تاريخ البدء والفني عند أول حفظ."""
        if not vals.get('start_date'):
            vals['start_date'] = fields.Datetime.now()
        if not vals.get('technician_id'):
            vals['technician_id'] = self.env.user.id
        if vals.get('name', _('جديد')) == _('جديد'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.result.set') or _('جديد')
        result_set = super().create(vals)
        if result_set.template_id and result_set.number_of_samples:
            result_set._create_result_lines()
        return result_set
    
    @api.depends('result_line_ids', 'result_line_ids.value_numeric', 'result_line_ids.value_text')
    def _compute_statistics(self):
        for record in self:
            total = len(record.result_line_ids)
            completed = len([line for line in record.result_line_ids if line.is_filled])
            
            record.total_criteria = total
            record.completed_criteria = completed
            record.progress_percentage = (completed / total * 100) if total > 0 else 0
    
    @api.depends('result_line_ids.is_compliant')
    def _compute_overall_result(self):
        """حساب النتيجة العامة"""
        for result_set in self:
            filled_lines = result_set.result_line_ids.filtered('is_filled')
            if not filled_lines:
                result_set.overall_result = 'pending'
            else:
                non_compliant = filled_lines.filtered(lambda l: not l.is_compliant)
                if non_compliant:
                    result_set.overall_result = 'fail'
                else:
                    result_set.overall_result = 'pass'
    
    def _create_result_lines(self):
        """إنشاء أسطر النتائج الديناميكية
        - يتم إنشاء سطر لكل (معيار × عينة) بشكل افتراضي.
        - بالنسبة للمعايير التي تم تمييزها كـ "حقل تلخيصي" (is_summary_field=True)
          يجب أن يظهر السطر مرة واحدة فقط، ويُحسب عادةً من سلسلة العينات
          عبر avg_series() أو ما شابه.
        """
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
            batch_size = 100
            for i in range(0, len(lines_to_create), batch_size):
                batch = lines_to_create[i:i + batch_size]
                self.env['lab.result.line'].create(batch)

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

    def action_generate_result_lines(self):
        """دالة عامة لإنشاء أسطر النتائج - للتوافق مع الكود القديم"""
        return self._create_result_lines()
    
    def action_start(self):
        """بدء التنفيذ"""
        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now()
        })
        self.message_post(body=_('تم بدء تنفيذ الفحوصات'))
    
    def action_complete(self):
        """إكمال المجموعة"""
        incomplete_lines = self.result_line_ids.filtered(lambda l: not l._is_value_complete())
        if incomplete_lines:
            raise UserError(_('لا يمكن إكمال الفحص قبل إدخال جميع القيم المطلوبة.'))

        self._compute_calculated_criteria()

        self.write({
            'state': 'completed',
            'end_date': fields.Datetime.now()
        })
        self.message_post(body=_('تم إكمال جميع الفحوصات'))
    
        self._update_flow_state()
    
    def _compute_calculated_criteria(self):
        """حساب قيم المعايير المحسوبة"""
        series_data = {}
        for line in self.result_line_ids:
            code = line.criterion_id.code
            if code:
                series_data.setdefault(code, [])
                value = line.get_numeric_value()
                if value is not None:
                    series_data[code].append(value)

        for sample_no in range(1, self.number_of_samples + 1):
            sample_lines = self.result_line_ids.filtered(lambda l: l.sample_no == sample_no)
            
            computed_criteria = sample_lines.filtered('criterion_id.is_computed_field')
            
            for line in computed_criteria:
                try:
                    calculation_context = {}
                    for dep_line in sample_lines:
                        if dep_line.criterion_id.code:
                            calculation_context[dep_line.criterion_id.code] = dep_line.get_numeric_value()

                    if self.sample_id and self.sample_id.product_id:
                        calculation_context['HOLE_COUNT'] = self.sample_id.product_id.product_tmpl_id.hole_count or 0
                    
                    if line.criterion_id.computation_formula:
                        result = self.env['lab.computation.engine'].execute_formula(
                            line.criterion_id.computation_formula,
                            calculation_context,
                            series_data=series_data
                        )
                        line.value_numeric = result
                        
                except Exception as e:
                    _logger.error(_("Error computing criterion %s: %s"), line.criterion_id.code, str(e))
                    continue
    
    @api.depends('number_of_samples')
    def _compute_sample_count(self):
        for record in self:
            record.sample_count = record.number_of_samples
    
    @api.depends('overall_result')
    def _compute_overall_conformity(self):
        """حساب حالة المطابقة العامة"""
        for result_set in self:
            filled_lines = result_set.result_line_ids.filtered('is_filled')
            if not filled_lines:
                result_set.overall_conformity = 'pending'
            else:
                non_compliant = filled_lines.filtered(lambda l: not l.is_compliant)
                if non_compliant:
                    result_set.overall_conformity = 'fail'
                else:
                    result_set.overall_conformity = 'pass'

    @api.depends('result_line_ids.is_compliant', 'result_line_ids.is_critical')
    def _compute_criteria_statistics(self):
        """حساب إحصائيات المعايير والمطابقة"""
        for record in self:
            lines = record.result_line_ids
            
            record.total_criteria_count = len(lines)
            record.passed_criteria_count = len(lines.filtered(lambda l: l.is_compliant))
            record.failed_criteria_count = len(lines.filtered(lambda l: not l.is_compliant))
            
            if record.total_criteria_count > 0:
                record.compliance_percentage = (record.passed_criteria_count / record.total_criteria_count)
            else:
                record.compliance_percentage = 0.0
            
            critical_lines = lines.filtered(lambda l: l.is_critical)
            record.critical_criteria_count = len(critical_lines)
            record.critical_passed_count = len(critical_lines.filtered(lambda l: l.is_compliant))
            
            if record.critical_criteria_count > 0:
                record.critical_compliance_percentage = (record.critical_passed_count / record.critical_criteria_count)
            else:
                record.critical_compliance_percentage = 1.0

    def action_calculate_results(self):
        """🔄 حساب جميع النتائج تلقائياً"""
        for record in self:
            for line in record.result_line_ids:
                line._compute_compliance_and_deviation()
                line._compute_conformity_status()
            
            record._compute_overall_result()
            record._compute_overall_conformity()
            
            record.state = 'calculated'
            
            record.message_post(
                body="تم حساب النتائج تلقائياً ✅",
                message_type='notification'
            )
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_submit_results(self):
        """✅ تأكيد النتائج للمراجعة"""
        for record in self:
            incomplete_lines = record.result_line_ids.filtered(
                lambda l: not l._is_value_complete()
            )
            
            if incomplete_lines:
                criteria_names = ', '.join(incomplete_lines.mapped('criterion_id.name'))
                raise UserError(
                    f"يرجى إكمال البيانات للمعايير التالية:\n{criteria_names}"
                )
            
            record.state = 'submitted'
            
            record._notify_managers_for_approval()
            
            record.message_post(
                body="تم تأكيد النتائج وإرسالها للمراجعة 📋",
                message_type='notification'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_approve_results(self):
        """🏆 اعتماد النتائج نهائياً"""
        for record in self:
            record.state = 'completed'
            
            if record.sample_id:
                record.sample_id.action_complete_lab_test()
            
            if record.quality_check_id:
                record.quality_check_id.do_pass() if record.overall_result == 'pass' else record.quality_check_id.do_fail()
            
            record._notify_customer_results_ready()
            
            record.message_post(
                body="تم اعتماد النتائج نهائياً ✅🏆",
                message_type='notification'
            )

            record._update_flow_state()
        
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

    def _notify_managers_for_approval(self):
        """إشعار المدراء لمراجعة النتائج"""
        lab_managers = self.env.ref('appointment_products.group_lab_manager').users
        
        for manager in lab_managers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=manager.id,
                summary=f'مراجعة نتائج فحص: {self.name}',
                note=f'''
                يرجى مراجعة واعتماد نتائج الفحص التالية:
                
                📋 مجموعة النتائج: {self.name}
                🧪 العينة: {self.sample_id.name if self.sample_id else 'غير محدد'}
                📊 النتيجة الإجمالية: {dict(self._fields['overall_result'].selection).get(self.overall_result, self.overall_result)}
                ✅ نسبة المطابقة: {self.compliance_percentage * 100:.1f}%
                
                انقر هنا للمراجعة والاعتماد.
                '''
            )

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
            if flow and flow.state != 'completed':
                flow.action_next_step()

    def unlink(self):
        blocked_states = ('submitted', 'review', 'approved', 'completed')
        if any(rec.state in blocked_states for rec in self):
            raise UserError(_('لا يمكن حذف مجموعة النتائج بعد تأكيد الفحص. يمكنك أرشفتها بدلاً من ذلك.'))
        return super(LabResultSet, self).unlink()

    def _compute_active_timer(self):
        for record in self:
            record.active_timer_name = False
            record.active_timer_remaining = False
            record.has_active_timer = False

            timer_lines = record.result_line_ids.filtered(lambda l: l.criterion_id.is_time_based and l.timer_status in ('running', 'not_started'))
            if timer_lines:
                line = sorted(timer_lines, key=lambda x: (x.sequence, x.sample_no))[0]
                record.active_timer_name = line.criterion_id.name
                if line.timer_status == 'not_started':
                    record.active_timer_remaining = 'لم يبدأ'
                else:
                    record.active_timer_remaining = line.timer_remaining or ''
                record.has_active_timer = True

    def action_start_global_timer(self):
        """بدء المؤقت النشط من مستوى مجموعة النتائج"""
        self.ensure_one()
        timer_lines = self.result_line_ids.filtered(
            lambda l: l.criterion_id.is_time_based and l.timer_status == 'not_started'
        )
        if timer_lines:
            first_timer = sorted(timer_lines, key=lambda x: (x.sequence, x.sample_no))[0]
            first_timer.action_start_timer()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

    def write(self, vals):
        """تعديل مجموعة النتائج مع ختم تلقائي للتاريخ والفني عند أول تعديل"""
        value_fields = ['result_line_ids']
        if any(field in vals for field in value_fields):
            if not self.start_date:
                vals['start_date'] = fields.Datetime.now()
            if not self.technician_id:
                vals['technician_id'] = self.env.user.id
        
        return super().write(vals)


class LabResultLine(models.Model):
    """سطر نتيجة الفحص - يمثل فحصاً واحداً على عينة واحدة"""
    _name = 'lab.result.line'
    _description = 'سطر نتيجة الفحص'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'result_set_id, is_computed, sample_no, sequence, criterion_id'

    result_set_id = fields.Many2one(
        'lab.result.set',
        string='مجموعة النتائج',
        required=True,
        ondelete='cascade'
    )
    
    sample_no = fields.Integer(
        string='رقم العينة',
        required=True,
        help='رقم العينة في المجموعة (1، 2، 3...)'
    )
    
    criterion_id = fields.Many2one(
        'lab.test.criterion',
        string='معيار الفحص',
        required=True,
        ondelete='restrict'
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


    timer_start_time = fields.Datetime(
        string='وقت بدء المؤقت',
        help='وقت بدء المؤقت للمعايير الوقتية'
    )
    
    timer_end_time = fields.Datetime(
        string='وقت انتهاء المؤقت',
        compute='_compute_timer_end_time',
        help='الوقت المتوقع لانتهاء المؤقت'
    )
    
    timer_remaining = fields.Char(
        string='الوقت المتبقي',
        compute='_compute_timer_remaining',
        help='الوقت المتبقي للمؤقت'
    )
    
    timer_status = fields.Selection([
        ('not_started', 'لم يبدأ'),
        ('running', 'قيد التشغيل'),
        ('completed', 'انتهى'),
        ('overdue', 'متأخر')
    ], string='حالة المؤقت', compute='_compute_timer_status')
    
    can_edit_value = fields.Boolean(
        string='يمكن تعديل القيمة',
        compute='_compute_can_edit_value',
        help='هل يمكن تعديل قيمة هذا المعيار؟'
    )

    can_start_timer = fields.Boolean(
        string='يمكن بدء المؤقّت',
        compute='_compute_can_start_timer',
        store=False
    )

    is_critical = fields.Boolean(
        string='حرج',
        related='criterion_id.is_critical',
        store=True,
        readonly=True,
        help='يشير إلى أن هذا المعيار حرج ويؤثر على النتيجة النهائية'
    )
    
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
    
    criterion_is_time_based = fields.Boolean(
        string='معيار وقتي',
        related='criterion_id.is_time_based',
        readonly=True
    )
    
    is_computed = fields.Boolean(
        string='محسوب',
        related='criterion_id.is_computed_field',
        store=True,
        readonly=True
    )

    @api.depends('sample_no')
    def _compute_sample_identifier(self):
        for line in self:
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
                 'value_date')
    def _compute_is_filled(self):
        for line in self:
            test_type = line.criterion_id.test_type
            
            if test_type == 'numeric':
                line.is_filled = line.value_numeric not in (False, None)
            elif test_type == 'text':
                line.is_filled = bool(line.value_text)
            elif test_type == 'selection':
                line.is_filled = bool(line.value_selection)
            elif test_type == 'boolean':
                line.is_filled = True
            elif test_type == 'date':
                line.is_filled = bool(line.value_date)
            elif test_type == 'computed':
                line.is_filled = line.value_numeric not in (False, None)
            else:
                line.is_filled = False
    
    @api.depends('value_numeric', 'criterion_id.min_value', 'criterion_id.max_value')
    def _compute_compliance(self):
        for line in self:
            if not line.is_filled or line.criterion_id.test_type not in ('numeric', 'computed'):
                line.is_compliant = True
                continue
            
            criterion = line.criterion_id
            value = line.value_numeric
            
            is_compliant = True
            
            if criterion.min_value and value < criterion.min_value:
                is_compliant = False
            
            if criterion.max_value and value > criterion.max_value:
                is_compliant = False
            
            line.is_compliant = is_compliant
    
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
        """إرجاع القيمة المعروضة حسب نوع البيانات"""
        test_type = self.criterion_id.test_type
        
        if test_type == 'numeric':
            return str(self.value_numeric) if self.value_numeric is not None else ''
        elif test_type == 'text':
            return self.value_text or ''
        elif test_type == 'selection':
            return self.value_selection or ''
        elif test_type == 'boolean':
            return _('نعم') if self.value_boolean else _('لا')
        elif test_type == 'date':
            return str(self.value_date) if self.value_date else ''
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
        """فحص اكتمال القيمة حسب نوع الفحص"""
        self.ensure_one()
        
        if self.criterion_id.is_time_based and self.timer_status not in ['completed', 'overdue']:
            return False
        
        if self.criterion_id.test_type == 'numeric':
            return self.value_numeric is not False and self.value_numeric is not None
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
        """حساب المطابقة والانحراف للواجهة المحسّنة"""
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
    
    def write(self, vals):
        value_fields = ['value_numeric', 'value_text', 'value_selection', 'value_boolean', 'value_date']
        if any(field in vals for field in value_fields):
            for line in self:
                if line.criterion_id.is_time_based and not line.can_edit_value:
                    raise UserError(_(
                        'لا يمكن تعديل المعيار "%s" قبل انتهاء المؤقت!\n'
                        'الوقت المتبقي: %s'
                    ) % (line.criterion_id.name, line.timer_remaining))
                
                if not line.criterion_id.is_time_based:
                    timer_criteria = line.result_set_id.result_line_ids.filtered(
                        lambda l: l.criterion_id.is_time_based and 
                                 line.criterion_id in l.criterion_id.timer_dependent_criteria
                    )
                    active_timer = timer_criteria.filtered(lambda t: t.timer_status in ['not_started', 'running'])
                    if active_timer:
                        timer_names = ', '.join(active_timer.mapped('criterion_id.name'))
                        raise UserError(_(
                            'لا يمكن تعديل المعيار "%s" قبل انتهاء المؤقت المرتبط:\n%s'
                        ) % (line.criterion_id.name, timer_names))
            
            vals['technician_id'] = self.env.user.id
            vals['last_modified_date'] = fields.Datetime.now()
        
        res = super().write(vals)
        
        if any(k.startswith('value_') for k in vals.keys()):
            affected_sets = self.filtered(lambda l: l.criterion_id.is_input_field).mapped('result_set_id')
            if affected_sets:
                affected_sets._compute_calculated_criteria()
        return res

    def _check_previous_timers(self, current_line):
        """التحقق من المعايير الوقتية السابقة"""
        previous_timer_lines = current_line.result_set_id.result_line_ids.filtered(
            lambda l: l.criterion_id.is_time_based and 
                     l.sequence < current_line.sequence and 
                     l.timer_status in ['not_started', 'running']
        )
        
        if previous_timer_lines:
            timer_names = ', '.join(previous_timer_lines.mapped('criterion_id.name'))
            raise UserError(_(
                'المعايير التالية تتطلب مؤقّتًا ولم يبدأ/ينته بعد:\n%s\n'
                'يرجى الضغط على زر "🕒 بدء المؤقّت" أولاً.'
            ) % timer_names)

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

    @api.depends('criterion_id.is_time_based', 'criterion_id.time_duration', 'criterion_id.time_unit', 'timer_start_time')
    def _compute_timer_end_time(self):
        """حساب وقت انتهاء المؤقت"""
        for line in self:
            if line.criterion_id.is_time_based and line.timer_start_time:
                duration = line.criterion_id.time_duration or 0
                if line.criterion_id.time_unit == 'minutes':
                    delta = timedelta(minutes=duration)
                elif line.criterion_id.time_unit == 'hours':
                    delta = timedelta(hours=duration)
                elif line.criterion_id.time_unit == 'days':
                    delta = timedelta(days=duration)
                else:
                    delta = timedelta(minutes=duration)
                
                line.timer_end_time = line.timer_start_time + delta
            else:
                line.timer_end_time = False

    @api.depends('timer_start_time', 'timer_end_time')
    def _compute_timer_remaining(self):
        """حساب الوقت المتبقي للمؤقت"""
        now = fields.Datetime.now()
        for line in self:
            if line.criterion_id.is_time_based and line.timer_end_time:
                if line.timer_start_time and not line.timer_end_time:
                    line.timer_remaining = "لم يبدأ"
                elif line.timer_end_time <= now:
                    line.timer_remaining = "انتهى"
                else:
                    remaining = line.timer_end_time - now
                    hours, remainder = divmod(remaining.total_seconds(), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    if hours > 0:
                        line.timer_remaining = f"{int(hours)}س {int(minutes)}د"
                    else:
                        line.timer_remaining = f"{int(minutes)}د {int(seconds)}ث"
            else:
                line.timer_remaining = ""

    @api.depends('timer_start_time', 'timer_end_time')
    def _compute_timer_status(self):
        """حساب حالة المؤقت"""
        now = fields.Datetime.now()
        for line in self:
            if not line.criterion_id.is_time_based:
                line.timer_status = 'not_started'
            elif not line.timer_start_time:
                line.timer_status = 'not_started'
            elif line.timer_end_time and line.timer_end_time <= now:
                line.timer_status = 'completed'
            elif line.timer_end_time and line.timer_end_time > now:
                line.timer_status = 'running'
            else:
                line.timer_status = 'not_started'

    @api.depends('criterion_id.is_time_based', 'timer_status')
    def _compute_can_edit_value(self):
        """تحديد ما إذا كان يمكن تعديل القيمة"""
        for line in self:
            if not line.criterion_id.is_time_based:
                timer_criteria = line.result_set_id.result_line_ids.filtered(
                    lambda l: l.criterion_id.is_time_based and 
                             line.criterion_id in l.criterion_id.timer_dependent_criteria
                )
                if timer_criteria:
                    active_timer = timer_criteria.filtered(lambda t: t.timer_status in ['not_started', 'running'])
                    line.can_edit_value = not bool(active_timer)
                else:
                    line.can_edit_value = True
            elif line.timer_status == 'completed':
                line.can_edit_value = True
            else:
                line.can_edit_value = False

    def _compute_can_start_timer(self):
        """تحديد إمكانية إظهار زر بدء المؤقّت.
        يُسمح بالبدء فقط إذا كانت كل المعايير السابقة (بتسلسل أقل) مكتملة.
        """
        for line in self:
            if not line.criterion_id.is_time_based:
                line.can_start_timer = False
                continue

            prev_lines = line.result_set_id.result_line_ids.filtered(
                lambda l: l.sequence < line.sequence and not l.criterion_id.is_time_based
            )
            incomplete_prev = prev_lines.filtered(lambda l: not l._is_value_complete())
            line.can_start_timer = not bool(incomplete_prev)

    def action_start_timer(self):
        """بدء المؤقت للمعيار الوقتي"""
        for line in self:
            if not line.criterion_id.is_time_based:
                continue

            if not line.can_start_timer:
                raise UserError(_(
                    'لا يمكن بدء المؤقّت قبل إكمال جميع القيم السابقة!'
                ))

            line.timer_start_time = fields.Datetime.now()
            line.message_post(body=_('🕒 تم بدء المؤقت لهذا المعيار'))

    def action_reset_timer(self):
        """إعادة تعيين المؤقت"""
        self.ensure_one()
        if self.criterion_id.is_time_based:
            self.timer_start_time = False
            self.message_post(
                body=f"🔄 تم إعادة تعيين المؤقت للمعيار: {self.criterion_id.name}"
            )
        return True 
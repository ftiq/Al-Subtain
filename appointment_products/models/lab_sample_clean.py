# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError


STATE_TO_QC_STATUS = {
    'draft': 'pending',
    'received': 'pending',
    'testing': 'in_progress',
    'completed': 'completed',
    'approved': 'completed',
    'rejected': 'failed',
}

QC_TO_STATE_STATUS = {v: k for k, v in STATE_TO_QC_STATUS.items()}


class LabSample(models.Model):
    _name = 'lab.sample'
    _description = _('Lab Sample')
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, name'
    _rec_name = 'name'

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
        ('positive_quantity', 'check(quantity > 0)', 'الكمية يجب أن تكون أكبر من الصفر!'),
        ('unique_name', 'unique(name)', 'رقم العينة يجب أن يكون فريداً!'),
    ]

    
    name = fields.Char(
        string=_('Sample Number'),
        required=True,
        copy=False,
        default=lambda self: _('New'),
        tracking=True,
        help=_('Unique reference number for the sample'),
        index=True 
    )
    
    
    task_id = fields.Many2one(
        'project.task',
        string=_('Task'),
        required=False,
        ondelete='cascade',
        tracking=True,
        help=_('Task related to this sample'),
        index=True 
    )
    
    product_id = fields.Many2one(
        'product.product',
        string=_('Product (Sample)'),
        required=True,
        domain=[('product_tmpl_id.is_sample_product', '=', True)],
        tracking=True,
        help=_('Product that represents the sample type'),
        index=True 
    )
    

    sample_subtype_id = fields.Many2one(
        'lab.sample.subtype',
        string=_('Sample Subtype'),
        tracking=True,
        help=_('Specific subtype of the sample (e.g. Type A, Type B, Type C)'),
        index=True
    )
    
    lab_test_template_id = fields.Many2one(
        'lab.test.template',
        string=_('Test Template'),
        domain=[('state', '=', 'active')],
        tracking=True,
        help=_('Test template applied to this sample')
    )
    
    quality_check_id = fields.Many2one(
        'quality.check',
        string=_('Quality Check'),
        readonly=True,
        help=_('Quality check related to this sample')
    )
    
    
    collection_date = fields.Date(
        string=_('Collection Date'),
        default=fields.Date.today,
        tracking=True,
        help=_('Date when sample was collected from site')
    )
    
    received_date = fields.Datetime(
        string=_('Received Date'),
        default=fields.Datetime.now,
        tracking=True,
        help=_('Date and time when sample was received in laboratory')
    )
    
    quantity = fields.Float(
        string=_('Quantity'),
        default=1.0,
        required=True,
        digits=(12, 3),
        help=_('Quantity of received sample')
    )
    
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('received', 'مستلمة'),
        ('testing', 'قيد الفحص'),
        ('completed', 'مكتملة'),
        ('approved', 'مصادق علية'),
        ('rejected', 'مرفوضة')
    ], string='الحالة', default='draft', tracking=True, required=True, index=True)  # فهرس لفلترة الحالات
    
    overall_result = fields.Selection([
        ('pass', 'ناجح'),
        ('fail', 'فاشل'),
        ('pending', 'قيد الانتظار')
    ], string='النتيجة النهائية', compute='_compute_overall_result', store=True, tracking=True)
    
    
    result_set_ids = fields.One2many(
        'lab.result.set',
        'sample_id',
        string=_('Dynamic Result Sets'),
        help=_('Result sets related to this sample')
    )
    

    
    test_flow_ids = fields.One2many(
        'lab.test.flow',
        'sample_id',
        string=_('Test Flows')
    )
    
    
    result_set_count = fields.Integer(
        string=_('Result Sets Count'),
        compute='_compute_result_set_count',
        store=True
    )
    
    total_criteria = fields.Integer(
        string=_('Total Criteria'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    completed_criteria = fields.Integer(
        string=_('Completed Criteria'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    criteria_progress_percentage = fields.Float(
        string=_('Criteria Progress Percentage'),
        compute='_compute_criteria_progress',
        store=True
    )
    
    
    project_id = fields.Many2one(
        related='task_id.project_id',
        string=_('Project'),
        store=True,
        readonly=True
    )
    
    sale_order_id = fields.Many2one(
        related='task_id.sale_order_id',
        string=_('Sale Order'),
        store=True,
        readonly=True
    )
    
    partner_id = fields.Many2one(
        related='task_id.partner_id',
        string=_('Customer'),
        store=True,
        readonly=True
    )
    

    reference_general_limit = fields.Float(
        related='task_id.reference_general_limit',
        string='المعدل',
        readonly=True,
        store=False,
        help='المعيار العام للمقارنة من المهمة المرتبطة'
    )

    core_compaction_ratio = fields.Float(
        string='نسبة الحدل (%)',
        help='النسبة المرجعية المطلوبة للحدل لعينة الكور الخرساني (٪)'
    )

    # الكثافة الموقعية: وزن وحجم مرجعيان على مستوى العينة
    is_field_density_sample = fields.Boolean(
        string='عينة كثافة موقعية',
        compute='_compute_is_field_density_sample',
        store=True,
        help='يتفعّل عندما يكون نوع العينة FIELD_DENSITY'
    )

    field_density_weight = fields.Float(
        string='الوزن',
        help='وزن العينة لفحوص الكثافة الموقعية (مرجعي لهذه العينة)'
    )

    field_density_volume = fields.Float(
        string='الحجم',
        help='حجم القالب/الحفرة لفحوص الكثافة الموقعية (مرجعي لهذه العينة)'
    )
    
    concrete_sample_type_id = fields.Many2one(
        related='task_id.concrete_sample_type_id',
        string='نوع عينة الخرسانة',
        store=True,
        readonly=True,
        help='نوع العينة للخرسانة (أبنية، أساسات، جسور)'
    )
    
    is_concrete_sample = fields.Boolean(
        string='عينة خرسانية',
        compute='_compute_is_concrete_sample',
        store=True,
        help='هل هذه عينة خرسانية؟'
    )

    is_core_ui = fields.Boolean(
        string='Is Core UI',
        compute='_compute_is_core_ui',
        store=False
    )
    
    bitumen_type = fields.Char(
        string='نوع القير',
        compute='_compute_bitumen_type',
        store=False,
        help='يظهر نوع القير (أساس أو تسطيح) إذا كان المنتج قير'
    )
    
    bitumen_results_summary = fields.Html(
        string='ملخص نتائج القير',
        compute='_compute_bitumen_results_summary',
        store=False,
        help='عرض جدولي لجميع نتائج متوسطات القير والمستويات المطبقة'
    )

    core_results_summary = fields.Html(
        string='ملخص نتائج الكور',
        compute='_compute_core_results_summary',
        store=False,
        help='عرض ملخص منظم لنتائج فحص سمك وحدل الكور' 
    )
    
    field_density_results_summary = fields.Html(
        string='ملخص الكثافة الموقعية',
        compute='_compute_field_density_results_summary',
        store=False,
        help='عرض ملخص منظم لنتائج الكثافة الموقعية لكل مجموعة'
    )

    # ---- Asphalt Mix Summary ----
    is_asphalt_mix_sample = fields.Boolean(
        string='عينة خلطة إسفلتية',
        compute='_compute_is_asphalt_mix_sample',
        store=True
    )
    asphalt_mix_results_summary = fields.Html(
        string='ملخص نتائج الخلطة الإسفلتية',
        compute='_compute_asphalt_mix_results_summary',
        store=False,
        sanitize=False
    )

    # ---- Aggregate Quality (Sieve + Proctor + CBR + LL/PL) Summary ----
    is_agg_quality_sample_flag = fields.Boolean(
        string='عينة جودة الركام',
        compute='_compute_is_agg_quality_sample_flag',
        store=False
    )
    agg_quality_results_summary = fields.Html(
        string='ملخص جودة الركام',
        compute='_compute_agg_quality_results_summary',
        store=False,
        sanitize=False
    )

    # ---- PLR (Pavement Longitudinal Regularity) Summary ----
    is_plr_sample = fields.Boolean(
        string='عينة PLR',
        compute='_compute_is_plr_sample',
        store=False
    )
    plr_results_summary = fields.Html(
        string='ملخص نتائج PLR',
        compute='_compute_plr_results_summary',
        store=False,
        sanitize=False
    )
    plr_delta_m = fields.Float(string='Δ (متر)', compute='_compute_plr_results_summary', store=False)
    plr_initial_discount_pct = fields.Float(string='نسبة الخصم الأولية %', compute='_compute_plr_results_summary', store=False)
    plr_final_discount_pct = fields.Float(string='نسبة الخصم النهائية %', compute='_compute_plr_results_summary', store=False)
    
    bitumen_comparison_level = fields.Selection(
        selection=[
            ('1', 'المستوى الأول'),
            ('2', 'المستوى الثاني'),
            ('3', 'المستوى الثالث'),
            ('4', 'المستوى الرابع'),
        ],
        string='مستوى المقارنة (قير)',
        help='اختر مستوى المقارنة المطلوب تطبيقه على جميع فحوصات القير لهذه العينة.\nلقير التسطيح: 4 مستويات.\nلقير الأساس: 3 مستويات (يتم تجاهل الرابع).'
    )

    @api.onchange('bitumen_type')
    def _onchange_bitumen_type_set_default_level(self):
        for rec in self:
            if not rec.bitumen_type:
                rec.bitumen_comparison_level = False
            else:

                if not rec.bitumen_comparison_level:
                    rec.bitumen_comparison_level = '1'

                if rec.bitumen_type == 'قير أساس' and rec.bitumen_comparison_level == '4':
                    rec.bitumen_comparison_level = '3'

    @api.onchange('bitumen_comparison_level')
    def _onchange_bitumen_comparison_level(self):
        for rec in self:
            if rec.bitumen_type == 'قير أساس' and rec.bitumen_comparison_level == '4':
                rec.bitumen_comparison_level = '3'
                return {
                    'warning': {
                        'title': _('تنبيه'),
                        'message': _('لقير الأساس توجد 3 مستويات فقط. تم تعيين المستوى الثالث تلقائياً.'),
                    }
                }
    
    
    notes = fields.Html(
        string=_('Notes'),
        help=_('General notes about the sample')
    )

    exec_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    exec_signer_id = fields.Many2one(
        'res.partner',
        string='اختيار المسؤول',
        domain=[('is_company', '=', False)]
    )
    exec_signer_name = fields.Char(
        string='اسم المسؤول',
        related='exec_signer_id.name',
        store=True,
        readonly=True
    )
    exec_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_exec_is_signed',
        store=True,
        readonly=True
    )
    exec_signed_at = fields.Datetime(
        string='تاريخ توقيع ممثل الجهة المنفذة',
        readonly=True
    )
    exec_signature_locked = fields.Boolean(
        string='قفل التوقيع (منفذ)',
        compute='_compute_signature_locks',
        readonly=True
    )

    super_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    super_signer_id = fields.Many2one(
        'res.partner',
        string='اختيار المسؤول',
        domain=[('is_company', '=', False)]
    )
    super_signer_name = fields.Char(
        string='اسم المسؤول',
        related='super_signer_id.name',
        store=True,
        readonly=True
    )
    super_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_super_is_signed',
        store=True,
        readonly=True
    )
    super_signed_at = fields.Datetime(
        string='تاريخ توقيع ممثل الجهة المشرفة',
        readonly=True
    )
    super_signature_locked = fields.Boolean(
        string='قفل التوقيع (مشرف)',
        compute='_compute_signature_locks',
        readonly=True
    )

    company_signature = fields.Binary(
        string='التوقيع الإلكتروني',
        attachment=True
    )
    company_signer_id = fields.Many2one(
        'res.users',
        string='اختيار المدير التنفيذي'
    )
    company_signer_name = fields.Char(
        string='اسم المدير التنفيذي',
        related='company_signer_id.name',
        store=True,
        readonly=True
    )
    company_is_signed = fields.Boolean(
        string='تم التوقيع',
        compute='_compute_company_is_signed',
        store=True,
        readonly=True
    )
    company_signed_at = fields.Datetime(
        string='تاريخ توقيع المدير التنفيذي',
        readonly=True
    )
    company_signature_locked = fields.Boolean(
        string='قفل التوقيع (المدير التنفيذي)',
        compute='_compute_signature_locks',
        readonly=True
    )
    

    all_signatures_signed = fields.Boolean(
        string='جميع التوقيعات مكتملة',
        compute='_compute_all_signatures_signed',
        store=True,
        help='يتم تفعيل هذا الحقل عندما تكون جميع التوقيعات الثلاثة موجودة'
    )
    
    lab_code = fields.Char(
        string=_('الرمز المختبري'),
        tracking=True,
        help=_('الرمز المختبري المخصص للعينة'),
        index=True
    )
    
    field_serial = fields.Char(
        string=_('الرمز الحقلي'),
        tracking=True,
        help=_('الرقم التسلسلي الحقلي المخصص للعينة'),
        index=True
    )
    
    
    color = fields.Integer(
        string=_('Color'),
        default=0,
        help=_('Color for kanban view')
    )
    
    priority = fields.Selection([
        ('0', _('Normal')),
        ('1', _('High'))
    ], string=_('Priority'), default='0')
    
    activity_state = fields.Selection([
        ('overdue', _('Overdue')),
        ('today', _('Today')),
        ('planned', _('Planned'))
    ], string=_('Activity State'), compute='_compute_activity_state')
    
    @api.depends('activity_ids.state', 'activity_ids.date_deadline')
    def _compute_activity_state(self):
        """حساب حالة النشاط"""

        if not self:
            return
        for record in self:
            if not record.activity_ids:
                record.activity_state = False
            else:

                latest_activity = record.activity_ids.sorted('date_deadline')[0]
                if latest_activity.date_deadline:
                    from datetime import date
                    today = date.today()
                    if latest_activity.date_deadline < today:
                        record.activity_state = 'overdue'
                    elif latest_activity.date_deadline == today:
                        record.activity_state = 'today'
                    else:
                        record.activity_state = 'planned'
                else:
                    record.activity_state = 'planned'

    testers_with_states = fields.Html(
        string='المكلفون مع الحالات',
        compute='_compute_testers_with_states',
        help='عرض المكلفين مع حالة كل نتيجة',
        sanitize=False
    )
    
    @api.depends('result_set_ids.testers_ids', 'result_set_ids.state')
    def _compute_testers_with_states(self):
        """حساب المكلفين مع حالاتهم - يجمع حالات المكلف الواحد في باج واحد"""

        if not self:
            return
        for sample in self:
            testers_dict = {}
            
            for result_set in sample.result_set_ids:
                if result_set.testers_ids:
                    state_color = {
                        'draft': 'secondary',
                        'in_progress': 'warning', 
                        'calculated': 'info',
                        'review': 'primary',
                        'approved': 'success',
                        'completed': 'success',
                        'cancelled': 'danger'
                    }.get(result_set.state, 'secondary')
                    
                    state_text = {
                        'draft': 'مسودة',
                        'received': 'مستلمة',
                        'testing': 'قيد الفحص',
                        'completed': 'مكتملة',
                        'rejected': 'مرفوضة',
                        'in_progress': 'قيد العمل',
                        'calculated': 'محسوبة', 
                        'review': 'مراجعة',
                        'approved': 'معتمد',
                        'cancelled': 'ملغي'
                    }.get(result_set.state, 'غير محدد')
                    
                    template_name = result_set.template_id.name[:12] if result_set.template_id else 'نتيجة'
                    
                    for tester in result_set.testers_ids:
                        if tester.id not in testers_dict:
                            testers_dict[tester.id] = {
                                'name': tester.name,
                                'states': [],
                                'colors': [],
                                'templates': []
                            }
                        
                        testers_dict[tester.id]['states'].append(state_text)
                        testers_dict[tester.id]['colors'].append(state_color)
                        testers_dict[tester.id]['templates'].append(template_name)
            
            if testers_dict:
                html_content = '<div class="d-flex flex-wrap gap-1">'
                tester_count = 0
                
                for tester_id, tester_data in testers_dict.items():
                    if tester_count >= 4:  
                        break
                        
                    priority_colors = ['danger', 'warning', 'primary', 'info', 'success', 'secondary']
                    badge_color = 'secondary'
                    for color in priority_colors:
                        if color in tester_data['colors']:
                            badge_color = color
                            break
                    
                    unique_states = list(dict.fromkeys(tester_data['states']))  
                    states_text = ', '.join(unique_states[:2])
                    if len(unique_states) > 2:
                        states_text += f' +{len(unique_states) - 2}'
                    
                    unique_templates = list(dict.fromkeys(tester_data['templates']))[:3]
                    tooltip = f"{tester_data['name']} - {', '.join(unique_templates)}"
                    
                    html_content += f'<span class="badge bg-{badge_color} text-white small" title="{tooltip}">'
                    html_content += f'<i class="fa fa-user me-1"></i>{tester_data["name"]} ({states_text})'
                    html_content += '</span>'
                    
                    tester_count += 1
                
                if len(testers_dict) > 4:
                    html_content += f'<span class="badge bg-secondary text-white small">+{len(testers_dict) - 4} آخرين</span>'
                    
                html_content += '</div>'
                sample.testers_with_states = html_content
            else:
                sample.testers_with_states = '<small class="text-muted"><i class="fa fa-user-o me-1"></i>غير معيّن</small>'

    def _compute_is_plr_sample(self):
        for sample in self:
            val = False
            try:
                val = any((rs.template_id.code or '').upper() == 'PAVEMENT_LONG_REG' for rs in sample.result_set_ids)
            except Exception:
                val = False
            sample.is_plr_sample = val

    def _compute_plr_results_summary(self):
        for sample in self:
            # Defaults
            sample.plr_results_summary = False
            sample.plr_delta_m = 0.0
            sample.plr_initial_discount_pct = 0.0
            sample.plr_final_discount_pct = 0.0

            # Locate PLR result set
            rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'PAVEMENT_LONG_REG')[:1]
            if not rs:
                continue

            task = sample.task_id
            course = getattr(task, 'plr_course_type', 'surface') or 'surface'
            road_type = getattr(task, 'plr_road_type', 'secondary') or 'secondary'
            street_len = float(getattr(task, 'plr_street_length', 0.0) or 0.0)

            # Spacing per layer (متر)
            spacing = 15.0 if course == 'surface' else 5.0

            # Build lines per segment_no
            # criterion codes
            def pick(code):
                return rs.result_line_ids.filtered(lambda l: l.criterion_id.code == code)

            lines_459 = pick('PLR_4_59')
            lines_610 = pick('PLR_6_10')
            lines_gt10 = pick('PLR_GT10')
            lines_ratio = pick('PLR_SEG_RATIO')

            seg_nos = set(lines_459.mapped('sample_no') + lines_610.mapped('sample_no') + lines_gt10.mapped('sample_no'))
            seg_nos = sorted([n for n in seg_nos if n])

            total_fail_pts = 0.0
            failed_segments = 0

            # Helper to get count and ratio per segment
            def get_val(lines, i):
                rec = lines.filtered(lambda l: l.sample_no == i)[:1]
                return float(getattr(rec, 'value_numeric', 0.0) or 0.0)

            is_surface = 1 if course == 'surface' else 0

            # fetch station labels from task segments
            station_map = {}
            try:
                if task and getattr(task, 'plr_segment_ids', False):
                    for s in task.plr_segment_ids:
                        station_map[s.segment_no] = s.station_range
            except Exception:
                station_map = {}

            # Build HTML
            rows = []
            for i in seg_nos:
                a = get_val(lines_459, i)
                b = get_val(lines_610, i)
                c = get_val(lines_gt10, i)
                ratio = get_val(lines_ratio, i) or 1.0

                base_a = 20.0 if is_surface else 40.0
                base_b = 0.0 if is_surface else 3.0
                base_c = 0.0
                allow_a = base_a * ratio
                allow_b = base_b * ratio
                allow_c = base_c * ratio  # always 0

                seg_fail_pts = max(0.0, a - allow_a) + max(0.0, b - allow_b) + (c if c > allow_c else 0.0)
                total_fail_pts += seg_fail_pts

                seg_pass = (a <= allow_a and b <= allow_b and c <= allow_c)
                if not seg_pass:
                    failed_segments += 1

                rows.append({
                    'no': i,
                    'station': station_map.get(i, str(i)),
                    'a': a, 'allow_a': allow_a,
                    'b': b, 'allow_b': allow_b,
                    'c': c, 'allow_c': allow_c,
                    'pass': seg_pass,
                })

            delta_m = total_fail_pts * spacing
            init_pct = (delta_m / street_len) * 100.0 if street_len > 0 else 0.0
            if road_type == 'main':
                final_pct = 100.0 * ((init_pct + 5.0) / 40.0) ** 2
            else:
                final_pct = init_pct

            # Compose HTML
            total_segments = len(seg_nos)
            pass_segments = total_segments - failed_segments
            pass_pct = (pass_segments / total_segments * 100.0) if total_segments else 0.0

            html = [
                '<div class="card"><div class="card-body">',
                f'<p><b>نوع الطبقة:</b> {course} &nbsp; | &nbsp; <b>نوع الشارع:</b> {road_type} &nbsp; | &nbsp; <b>مسافة الفحص:</b> {spacing:.0f} م</p>',
                '<table class="table table-sm table-bordered">',
                '<thead><tr>'
                '<th>م</th><th>المحطة</th>'
                '<th>A 4.0–5.9 (عدد/الحد)</th>'
                '<th>B 6.0–10.0 (عدد/الحد)</th>'
                '<th>C &gt;10 (عدد/الحد)</th>'
                '<th>مطابقة</th>'
                '</tr></thead><tbody>'
            ]
            for r in rows:
                badge = '<span class="badge bg-success">مطابق</span>' if r['pass'] else '<span class="badge bg-danger">غير مطابق</span>'
                html.append(
                    f"<tr><td>{r['no']}</td><td>{r['station']}</td><td>{r['a']:.0f}/{r['allow_a']:.0f}</td><td>{r['b']:.0f}/{r['allow_b']:.0f}</td><td>{r['c']:.0f}/{r['allow_c']:.0f}</td><td>{badge}</td></tr>"
                )
            html += [
                '</tbody></table>',
                f'<p><b>إجمالي المقاطع:</b> {total_segments} &nbsp; | &nbsp; <b>غير مطابق:</b> {failed_segments} &nbsp; | &nbsp; <b>نسبة النجاح:</b> {pass_pct:.1f}%</p>',
                f'<p><b>عدد النقاط الفاشلة:</b> {total_fail_pts:.0f} &nbsp; | &nbsp; <b>Δ:</b> {delta_m:.2f} م &nbsp; | &nbsp; <b>نسبة الخصم الأولية:</b> {init_pct:.2f}% &nbsp; | &nbsp; <b>نسبة الخصم النهائية:</b> {final_pct:.2f}%</p>',
                '</div></div>'
            ]

            sample.plr_results_summary = ''.join(html)
            sample.plr_delta_m = delta_m
            sample.plr_initial_discount_pct = init_pct
            sample.plr_final_discount_pct = final_pct

    @api.depends('product_id.product_tmpl_id.sample_type_id.code')
    def _compute_is_agg_quality_sample_flag(self):
        for sample in self:
            try:
                st_code = (sample.product_id.product_tmpl_id.sample_type_id.code or '').upper() if sample.product_id and sample.product_id.product_tmpl_id and sample.product_id.product_tmpl_id.sample_type_id else ''
            except Exception:
                st_code = ''
            sample.is_agg_quality_sample_flag = (st_code == 'AGG_QUALITY')

    @api.depends('result_set_ids.result_line_ids.value_numeric',
                 'result_set_ids.template_id.code',
                 'result_set_ids.agg_selected_class',
                 'result_set_ids.agg_quality_range_ids.effective_min',
                 'result_set_ids.agg_quality_range_ids.effective_max')
    def _compute_agg_quality_results_summary(self):
        for sample in self:
            sample.agg_quality_results_summary = False
            # Ensure only for AGG_QUALITY samples
            if not sample.is_agg_quality_sample_flag:
                continue
            try:
                # Locate related result sets
                sieve_rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'AGG_QUALITY_SIEVE')[:1]
                proctor_rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'AGG_PROCTOR_D698')[:1]
                cbr_rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'AGG_CBR_D1883')[:1]
                ll_rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'LL_D4318')[:1]
                pl_rs = sample.result_set_ids.filtered(lambda r: (r.template_id.code or '').upper() == 'PL_D4318')[:1]

                # Helper to fetch a numeric value by criterion code
                def get_line_value(rs, code):
                    if not rs:
                        return None
                    line = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == code)[:1]
                    if not line:
                        return None
                    val = line.value_numeric
                    if (val is None or val == 0) and getattr(line, 'result_value_computed', False):
                        val = line.result_value_computed
                    return float(val) if val is not None else None

                selected_class = sieve_rs.agg_selected_class if sieve_rs else None
                # Proctor values
                mdd = get_line_value(proctor_rs, 'MDD_KG_M3')  # كغم/م3
                omc = get_line_value(proctor_rs, 'OMC_PERCENT')
                # CBR summary
                cbr_at95 = get_line_value(cbr_rs, 'CBR_AT_95_PERCENT_COMPACTION')
                # LL/PL
                ll_val = get_line_value(ll_rs, 'LL_PERCENT')
                pl_val = get_line_value(pl_rs, 'PL_PERCENT')
                pi_val = (ll_val - pl_val) if (ll_val is not None and pl_val is not None) else None

                # Build sieve table rows
                rows_html = ''
                if sieve_rs and sieve_rs.agg_quality_range_ids:
                    # Order by sequence like UI
                    for r in sieve_rs.agg_quality_range_ids.sorted('sequence'):
                        lo = r.effective_min or 0.0
                        hi = r.effective_max or 0.0
                        actual = r.actual_passing or 0.0
                        rows_html += (
                            f"<tr>"
                            f"<td style='text-align:center;'>{r.sieve_label or ''}</td>"
                            f"<td style='text-align:center;'>{actual:.0f}</td>"
                            f"<td style='text-align:center;'>{lo:.0f}</td>"
                            f"<td style='text-align:center;'>{hi:.0f}</td>"
                            f"</tr>"
                        )

                # Spec min for CBR by class
                cbr_min = None
                if selected_class == 'B':
                    cbr_min = 35
                elif selected_class == 'C':
                    cbr_min = 30
                elif selected_class == 'D':
                    cbr_min = 20
                # A: open (None)

                # Compose HTML card
                html = [
                    "<div class='card'><div class='card-body'>",
                    f"<p><b>فئة المطابقة:</b> {selected_class or '-'} &nbsp; | &nbsp; <b>الرمز الحقلي:</b> {sample.field_serial or ''}</p>",
                    "<table class='table table-sm table-bordered' style='table-layout:fixed;'>",
                    "<thead><tr>",
                    "<th>مقاس المنخل</th>",
                    "<th>% المار الفعلي</th>",
                    "<th>الحد الأدنى</th>",
                    "<th>الحد الأعلى</th>",
                    "</tr></thead><tbody>",
                    rows_html or "",
                    "</tbody></table>",
                ]

                # Bottom summary like client's order
                # Convert MDD to g/cm³ if available
                mdd_g_cm3 = (mdd / 1000.0) if (mdd is not None and mdd != 0) else None
                html += [
                    "<table class='table table-sm table-bordered' style='width:100%;'>",
                    "<tbody>",
                    f"<tr><td style='width:30%;background:#DDDDDD;font-weight:bold;'>الكثافة الجافة العظمى gm/cm³</td><td>{(f'{mdd_g_cm3:.3f}' if mdd_g_cm3 is not None else '-')}</td></tr>",
                    f"<tr><td style='background:#DDDDDD;font-weight:bold;'>نسبة الرطوبة المثلى %</td><td>{(f'{omc:.1f}' if omc is not None else '-')}</td></tr>",
                    f"<tr><td style='background:#DDDDDD;font-weight:bold;'>نسبة التحمل الكاليفورني نسبة الحدل 95% %CBR</td><td>{(f'{cbr_at95:.0f}' if cbr_at95 is not None else '-')}" + (f" &nbsp; <span class='badge bg-secondary'>حد أدنى {cbr_min}%</span>" if cbr_min is not None else "") + "</td></tr>",
                    f"<tr><td style='background:#DDDDDD;font-weight:bold;'>LL %</td><td>{(f'{ll_val:.0f}' if ll_val is not None else '-')}</td></tr>",
                    f"<tr><td style='background:#DDDDDD;font-weight:bold;'>P.I %</td><td>{(f'{pi_val:.0f}' if pi_val is not None else '-')}</td></tr>",
                    "</tbody></table>",
                    "</div></div>"
                ]

                sample.agg_quality_results_summary = ''.join(html)
            except Exception:
                sample.agg_quality_results_summary = False
    
    @api.depends('result_set_ids')
    def _compute_result_set_count(self):
        """حساب عدد مجموعات النتائج"""
        for sample in self:
            sample.result_set_count = len(sample.result_set_ids)
    
    @api.depends('result_set_ids.result_line_ids', 'result_set_ids.state')
    def _compute_criteria_progress(self):
        """حساب تقدم المعايير"""
        for sample in self:
            total = sum(len(rs.result_line_ids) for rs in sample.result_set_ids)
            completed = sum(
                len(rs.result_line_ids.filtered(lambda l: l.result_value))
                for rs in sample.result_set_ids
            )
            
            sample.total_criteria = total
            sample.completed_criteria = completed
            sample.criteria_progress_percentage = (
                (completed / total * 100) if total > 0 else 0
            )
    
    @api.depends('result_set_ids.overall_result')
    def _compute_overall_result(self):
        """حساب النتيجة العامة"""
        for sample in self:

            result_sets = sample.result_set_ids.filtered(lambda rs: rs.state in ('completed', 'approved'))
            if not result_sets:
                sample.overall_result = 'pending'
            elif any(rs.overall_result == 'fail' for rs in result_sets):
                sample.overall_result = 'fail'
            else:
                sample.overall_result = 'pass'
    
    @api.depends('activity_ids.date_deadline')
    def _compute_activity_state_alt(self):
        """بديل (غير مستخدم في الحقل) لحساب حالة الأنشطة.
        ملاحظة: تم تغيير الاسم لتجنّب تظليل الدالة الأساسية، كما تم إزالة الاعتماد على حقل غير موجود (a.done).
        """
        today = fields.Date.today()
        for sample in self:
            activities = sample.activity_ids  # لا نستخدم a.done لأنه غير موجود على mail.activity
            if not activities:
                sample.activity_state = 'planned'
            else:
                overdue = activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)
                today_activities = activities.filtered(lambda a: a.date_deadline == today)
                if overdue:
                    sample.activity_state = 'overdue'
                elif today_activities:
                    sample.activity_state = 'today'
                else:
                    sample.activity_state = 'planned'

    
    @api.model
    def create(self, vals):
        """إنشاء العينة مع رقم متسلسل"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lab.sample') or _('New')
        

        if vals.get('task_id') and not vals.get('sample_subtype_id'):
            task = self.env['project.task'].browse(vals.get('task_id'))
            product_id = vals.get('product_id')
            
            if task and product_id:
                form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product_id)
                if form_line and form_line.sample_subtype_id:
                    vals['sample_subtype_id'] = form_line.sample_subtype_id.id
        
        if vals.get('quality_check_id') and not (vals.get('lab_code') or vals.get('field_serial')):
            quality_check = self.env['quality.check'].browse(vals.get('quality_check_id'))
            if quality_check and quality_check.picking_id:
                move_line = quality_check.picking_id.move_line_ids.filtered(
                    lambda ml: ml.product_id.id == vals.get('product_id')
                )
                if move_line:
                    move_line = move_line[0] if move_line else False
                    if move_line and move_line.field_code and not vals.get('lab_code'):
                        vals['lab_code'] = move_line.field_code
                    if move_line and move_line.field_serial and not vals.get('field_serial'):
                        vals['field_serial'] = move_line.field_serial


        now = fields.Datetime.now()
        if vals.get('exec_signature'):
            vals['exec_signed_at'] = now
        if vals.get('super_signature'):
            vals['super_signed_at'] = now
        if vals.get('company_signature'):
            vals['company_signed_at'] = now
        

        try:
            if vals.get('task_id') and 'core_compaction_ratio' not in vals:
                task = self.env['project.task'].browse(vals['task_id'])
                if task and task.core_compaction_ratio:
                    vals['core_compaction_ratio'] = task.core_compaction_ratio
        except Exception:
            pass


        try:
            product_id = vals.get('product_id')
            is_field_density = False
            if product_id:
                prod = self.env['product.product'].browse(product_id)
                st_code = (prod.product_tmpl_id.sample_type_id.code or '').upper() if prod and prod.product_tmpl_id and prod.product_tmpl_id.sample_type_id else ''
                is_field_density = 'FIELD_DENSITY' in st_code

            if is_field_density and vals.get('task_id'):
                task = self.env['project.task'].browse(vals['task_id'])
                if 'field_density_weight' not in vals and getattr(task, 'field_density_weight', False):
                    vals['field_density_weight'] = task.field_density_weight
                if 'field_density_volume' not in vals and getattr(task, 'field_density_volume', False):
                    vals['field_density_volume'] = task.field_density_volume
        except Exception:
            pass

        return super().create(vals)

    @api.depends('task_id.stock_receipt_id.concrete_sample_type_id', 'task_id.main_sample_is_concrete_core', 'task_id.is_concrete_core_type_selected', 'concrete_sample_type_id')
    def _compute_is_core_ui(self):
        for rec in self:
            is_core = False
            try:
                code = (rec.task_id.stock_receipt_id.concrete_sample_type_id.code or '').upper() if rec.task_id and rec.task_id.stock_receipt_id and rec.task_id.stock_receipt_id.concrete_sample_type_id else ''
                if code == 'CONCRETE_CORE':
                    is_core = True
                if not is_core and getattr(rec.task_id, 'main_sample_is_concrete_core', False):
                    is_core = True
                if not is_core and getattr(rec.task_id, 'is_concrete_core_type_selected', False):
                    is_core = True
                if not is_core and rec.concrete_sample_type_id and (rec.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                    is_core = True
            except Exception:
                is_core = False
            rec.is_core_ui = is_core

    @api.depends('product_id.product_tmpl_id.sample_type_id.code', 'sample_subtype_id.sample_type_id.code')
    def _compute_is_field_density_sample(self):
        for rec in self:
            val = False
            try:
                code = ''
                if rec.sample_subtype_id and rec.sample_subtype_id.sample_type_id and rec.sample_subtype_id.sample_type_id.code:
                    code = (rec.sample_subtype_id.sample_type_id.code or '').upper()
                elif rec.product_id and rec.product_id.product_tmpl_id and rec.product_id.product_tmpl_id.sample_type_id:
                    code = (rec.product_id.product_tmpl_id.sample_type_id.code or '').upper()
                val = 'FIELD_DENSITY' in code
            except Exception:
                val = False
            rec.is_field_density_sample = val
    
    
    
    def action_start_testing(self):
        """بدء الفحص - إنشاء مجموعة نتائج ديناميكية مع حماية من Race Conditions"""
        self.ensure_one()
        
        with self.env.cr.savepoint():
            if self.state == 'testing':
                if self.result_set_ids:
                    latest_result_set = self.result_set_ids.sorted('id', reverse=True)[0]
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Result Set'),
                        'res_model': 'lab.result.set',
                        'res_id': latest_result_set.id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                else:
                    self.state = 'draft'
            
            active_result_sets = self.result_set_ids.filtered(lambda rs: rs.state in ('draft', 'in_progress'))
            active_flows = self.test_flow_ids.filtered(lambda tf: tf.state in ('draft', 'in_progress'))
            
            if active_result_sets or active_flows:
                if active_result_sets:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Result Set'),
                        'res_model': 'lab.result.set',
                        'res_id': active_result_sets[0].id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
                elif active_flows:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Test Flow'),
                        'res_model': 'lab.test.flow',
                        'res_id': active_flows[0].id,
                        'view_mode': 'form',
                        'target': 'current',
                    }
            

            forced_template_id = self.env.context.get('force_flow_template_id')
            if forced_template_id:
                flow_template = self.env['lab.test.flow.template'].browse(forced_template_id)
            else:
                flow_template = self.product_id.product_tmpl_id.test_flow_template_id

            if flow_template:
                flow = self.env['lab.test.flow'].create({
                    'name': _("Flow %s") % self.name,
                    'sample_id': self.id,
                    'template_id': flow_template.id,
                })

                action = flow.action_next_step()

                self.state = 'testing'

                self.message_post(body=_(
                    "<b>Test flow started</b><br/>"
                    "Template: <em>%s</em>"
                ) % flow_template.name)

                return action or {
                    'type': 'ir.actions.act_window',
                    'name': _('Test Flow'),
                    'res_model': 'lab.test.flow',
                    'res_id': flow.id,
                    'view_mode': 'form',
                    'target': 'current',
                }

            if not self.lab_test_template_id:
                raise UserError(_('You must specify a test template or test flow first!'))


            try:
                total_count = int(self.task_id.total_samples_count or 1)
            except Exception:
                total_count = 1
            total_count = max(1, total_count)

            created_sets = self.env['lab.result.set']
            for group_no in range(1, total_count + 1):
                rs = self.env['lab.result.set'].create({
                    'name': _("Results %s - %s (مجموعة %s)") % (self.name, self.lab_test_template_id.name, group_no),
                    'sample_id': self.id,
                    'template_id': self.lab_test_template_id.id,
                    'test_group_no': group_no,
                    'number_of_samples': 1,
                    'state': 'draft'
                })
                rs.action_generate_result_lines()
                created_sets |= rs

            self.state = 'testing'

            first_name = created_sets and created_sets[0].name or ''
            self.message_post(body=_(
                "<b>Testing started</b><br/>"
                "Created result sets: <em>%s مجموعة</em><br/>"
                "First: <em>%s</em><br/>"
                "Test template: <em>%s</em>"
            ) % (len(created_sets), first_name, self.lab_test_template_id.name))


            return {
                'type': 'ir.actions.act_window',
                'name': _('Result Set'),
                'res_model': 'lab.result.set',
                'res_id': created_sets and created_sets[0].id or False,
                'view_mode': 'form',
                'target': 'current',
            }
    
    def action_view_result_sets(self):
        """عرض مجموعات النتائج"""
        if len(self.result_set_ids) == 1:

            return {
                'type': 'ir.actions.act_window',
                'name': f'نتيجة {self.name}',
                'res_model': 'lab.result.set',
                'res_id': self.result_set_ids[0].id,
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'sample_id': self.id,
                    'sample_name': self.name,
                    'breadcrumb_parent_action': 'appointment_products.action_lab_result_sets_sample_filtered',
                },
            }
        else:
            action = self.env.ref('appointment_products.action_lab_result_sets_sample_filtered').read()[0]
            action['domain'] = [('sample_id', '=', self.id)]
            action['name'] = f'نتائج العينة: {self.name}'
            action['context'] = {
                'default_sample_id': self.id,
                'sample_name': self.name,
                'active_id': self.id,
                'create': True,
            }
            return action
    
    def _auto_complete_if_ready(self):
        """إكمال العينة تلقائياً فقط عند اعتماد جميع المجموعات غير التجريبية"""
        for sample in self:
            direct_result_sets = sample.result_set_ids
            flow_result_sets = sample.test_flow_ids.mapped('line_ids.result_set_id')
            all_result_sets = direct_result_sets + flow_result_sets
            if not all_result_sets:
                continue

            non_experimental_sets = []
            for rs in all_result_sets:
                if sample._is_result_set_experimental(rs):
                    continue
                non_experimental_sets.append(rs)

            ready = True if not non_experimental_sets else all(rs.state == 'approved' for rs in non_experimental_sets)
            if ready and sample.state not in ('completed', 'approved'):
                sample.write({'state': 'completed'})
                sample.message_post(body=_('اكتملت العينة تلقائياً بعد اعتماد جميع النتائج'))
        return True

    def action_complete(self):
        """إكمال العينة - مع استثناء العينات التجريبية"""
        if not self.result_set_ids:
            raise UserError(_('لا توجد مجموعات نتائج للعينة!'))
        

        non_experimental_sets = []
        for rs in self.result_set_ids:
            if self._is_result_set_experimental(rs):
                continue
            non_experimental_sets.append(rs)
        

        unapproved_names = [rs.name for rs in non_experimental_sets if rs.state != 'approved']
        if unapproved_names:
            raise UserError(_(
                'لا يمكن إكمال العينة حتى يتم اعتماد جميع مجموعات النتائج غير التجريبية!\n'
                'المجموعات غير المعتمدة: %s\n\n'
                'يرجى اعتماد جميع النتائج أولاً قبل إكمال العينة. (تم استثناء عينات 7 أيام والاحتياط)'
            ) % ', '.join(unapproved_names))
        
        self.write({'state': 'completed'})
        self.message_post(body=_('<b>تم إكمال العينة بنجاح</b>'))
    
    def action_approve(self):
        """ اعتماد العينة"""
        self.write({'state': 'approved'})
        self.message_post(body=_("<b>تم اعتماد العينة بنجاح</b>"))
    
    def action_reject(self):
        """رفض العينة"""
        self.write({'state': 'rejected'})
        self.message_post(body=_("<b>Sample rejected</b>"))


    def action_clear_exec_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.exec_signature and rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'exec_signature': False, 'exec_signer_id': False, 'exec_signed_at': False})
        return True

    def action_clear_super_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.super_signature and rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'super_signature': False, 'super_signer_id': False, 'super_signed_at': False})
        return True

    def action_clear_company_signature(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.company_signature and rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600:
                raise UserError(_('لا يمكن حذف التوقيع بعد مرور 24 ساعة من التوقيع.'))
            rec.write({'company_signature': False, 'company_signer_id': False, 'company_signed_at': False})
        return True
    
    def action_approve_test(self):
        """مصادقة على الفحص - تغيير الحالة إلى مصادق عليه"""
        self.ensure_one()
        

        if not self.all_signatures_signed:
            from odoo.exceptions import UserError
            raise UserError(_('لا يمكن المصادقة على الفحص قبل إكمال جميع التوقيعات الثلاثة.'))
        

        if self.state != 'completed':
            raise UserError(_('لا يمكن المصادقة إلا على الفحوصات المكتملة.'))
        

        self.write({
            'state': 'approved'
        })
        

        self.message_post(
            body=_('تم المصادقة على الفحص بواسطة %s') % self.env.user.name,
            message_type='notification'
        )
        
        return True


    @api.depends('exec_signature')
    def _compute_exec_is_signed(self):
        for rec in self:
            rec.exec_is_signed = bool(rec.exec_signature)

    @api.depends('super_signature')
    def _compute_super_is_signed(self):
        for rec in self:
            rec.super_is_signed = bool(rec.super_signature)

    @api.depends('company_signature')
    def _compute_company_is_signed(self):
        for rec in self:
            rec.company_is_signed = bool(rec.company_signature)
    
    @api.depends('exec_signature', 'super_signature', 'company_signature')
    def _compute_all_signatures_signed(self):
        """حساب ما إذا كانت جميع التوقيعات الثلاثة موجودة"""
        for rec in self:
            rec.all_signatures_signed = bool(
                rec.exec_signature and 
                rec.super_signature and 
                rec.company_signature
            )

    @api.depends('exec_signed_at', 'super_signed_at', 'company_signed_at')
    def _compute_signature_locks(self):
        """يحسِب قفل التوقيع إذا مرَّ 24 ساعة على آخر توقيع."""
        now = fields.Datetime.now()
        for rec in self:
            rec.exec_signature_locked = bool(rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600)
            rec.super_signature_locked = bool(rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600)
            rec.company_signature_locked = bool(rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600)


    def write(self, vals):
        """تحديث حالة فحص الجودة عند تغيير حالة العينة والعكس + حماية التوقيع بعد 24 ساعة"""


        if any(rec.state == 'approved' for rec in self):

            allowed_fields = {'message_follower_ids', 'message_ids', 'activity_ids', 'activity_state'}
            if not set(vals.keys()).issubset(allowed_fields):
                from odoo.exceptions import UserError
                raise UserError(_('لا يمكن تعديل الفحص بعد المصادقة عليه نهائياً.'))

        now = fields.Datetime.now()


        if 'exec_signature' in vals:
            for rec in self:
                if rec.exec_signature and rec.exec_signed_at and (now - rec.exec_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع ممثل الجهة المنفذة بعد مرور 24 ساعة من التوقيع.'))
        if 'super_signature' in vals:
            for rec in self:
                if rec.super_signature and rec.super_signed_at and (now - rec.super_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع مسؤول الجودة بعد مرور 24 ساعة من التوقيع.'))
        if 'company_signature' in vals:
            for rec in self:
                if rec.company_signature and rec.company_signed_at and (now - rec.company_signed_at).total_seconds() >= 24 * 3600:
                    raise UserError(_('لا يمكن تعديل أو حذف توقيع المدير التنفيذي بعد مرور 24 ساعة من التوقيع.'))

        if (vals.get('task_id') or vals.get('product_id')) and not vals.get('sample_subtype_id'):
            for rec in self:
                task_id = vals.get('task_id', rec.task_id.id)
                product_id = vals.get('product_id', rec.product_id.id)
                
                if task_id and product_id:
                    task = self.env['project.task'].browse(task_id)

                    form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product_id)
                    if form_line and form_line.sample_subtype_id:
                        vals['sample_subtype_id'] = form_line.sample_subtype_id.id

        res = super().write(vals)


        for rec in self:
            updates = {}
            if 'exec_signature' in vals:
                if rec.exec_signature:
                    updates['exec_signed_at'] = now
                else:
                    updates['exec_signed_at'] = False
            if 'super_signature' in vals:
                if rec.super_signature:
                    updates['super_signed_at'] = now
                else:
                    updates['super_signed_at'] = False
            if 'company_signature' in vals:
                if rec.company_signature:
                    updates['company_signed_at'] = now
                else:
                    updates['company_signed_at'] = False
            if updates:
                rec.write(updates)

        if 'state' in vals:
            target_qc_status = STATE_TO_QC_STATUS.get(vals['state'])
            for rec in self.filtered(lambda s: s.quality_check_id):
                if target_qc_status and rec.quality_check_id.lab_test_status != target_qc_status:
                    rec.quality_check_id.sudo().write({'lab_test_status': target_qc_status})

        return res
    
    
    @api.constrains('quantity')
    def _check_quantity(self):
        """التحقق من الكمية"""
        for sample in self:
            if sample.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero!'))
    
    @api.constrains('collection_date', 'received_date')
    def _check_dates(self):
        """التحقق من التواريخ"""
        for sample in self:
            if sample.collection_date and sample.received_date:
                if sample.collection_date > sample.received_date.date():
                    raise ValidationError(_('Collection date cannot be after received date!'))
    


    test_count = fields.Integer(
        string=_('Test Count (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system - use result_set_count')
    )
    
    completed_tests = fields.Integer(
        string=_('Completed Tests (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system')
    )
    
    progress_percentage = fields.Float(
        string=_('Progress Percentage (Legacy)'),
        compute='_compute_legacy_compat',
        help=_('For compatibility with legacy system - use criteria_progress_percentage')
    )
    
    @api.depends('result_set_ids', 'result_set_ids.state')
    def _compute_legacy_compat(self):
        """حساب الحقول"""
        for sample in self:
            total_sets = len(sample.result_set_ids)
            completed_sets = len(sample.result_set_ids.filtered(lambda rs: rs.state == 'completed'))
            
            sample.test_count = total_sets
            sample.completed_tests = completed_sets
            sample.progress_percentage = (
                (completed_sets / total_sets) if total_sets > 0 else 0
            ) 

    cube_ids = fields.One2many('lab.sample.cube', 'sample_id', string='المكعبات')

    def action_generate_concrete_cubes(self, total_volume_m3, truck_ids):
        """يُنشئ عينات ومكعبات وفق خطة نوع العينة وحجم الصبّ"""
        self.ensure_one()
        sample_type = self.product_id.product_tmpl_id.sample_type_id or self.env.ref('appointment_products.lab_sample_type_concrete')
        if not sample_type:
            raise UserError(_('يجب تحديد نوع عينة يملك خطة أخذ عينات!'))


        if self.cube_ids:
            self.cube_ids.unlink()


        first_stage_sets = sample_type.sets_first_stage
        repeat = sample_type.repeat_volume_m3
        extra_sets = 0
        if total_volume_m3 > sample_type.initial_volume_m3:
            extra_sets = int(((total_volume_m3 - sample_type.initial_volume_m3) + repeat - 1) / repeat)
        total_sets = first_stage_sets + extra_sets


        cube_per_set = sample_type.cubes_per_set
        extra_cubes = sample_type.extra_cubes_per_set
        age_days_list = [int(a.strip()) for a in (sample_type.age_days_list or '7,28').split(',') if a.strip()]

        for s in range(1, total_sets + 1):

            for i in range(1, cube_per_set + 1):
                self.env['lab.sample.cube'].create({
                    'sample_id': self.id,
                    'set_no': s,
                    'cube_index': i,
                    'cube_type': 'core',
                    'age_days': 28,
                })

            for j in range(1, extra_cubes + 1):
                age_val = age_days_list[j-1] if j-1 < len(age_days_list) else 28
                self.env['lab.sample.cube'].create({
                    'sample_id': self.id,
                    'set_no': s,
                    'cube_index': cube_per_set + j,
                    'cube_type': 'extra',
                    'age_days': age_val,
                    'truck_id': False,
                })

        self.message_post(body=_('تم إنشاء %s عينة فرعية بـ %s مكعب لكلٍّ منها وفق الخطة.', total_sets, cube_per_set + extra_cubes)) 

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """تحديث مجال النوع الفرعي عند تغيير المنتج"""
        if self.product_id:
            product_code = self.product_id.default_code or ''
            if 'MASONRY' in product_code.upper() or 'BRICK' in product_code.upper():
                masonry_type = self.env['lab.sample.type'].search([('code', '=', 'MASONRY')], limit=1)
                if masonry_type:
                    return {'domain': {'sample_subtype_id': [('sample_type_id', '=', masonry_type.id)]}}
            
        return {'domain': {'sample_subtype_id': []}}
    
    @api.onchange('sample_subtype_id')
    def _onchange_sample_subtype_id(self):
        """تحديث قالب الفحص المناسب عند تغيير النوع الفرعي"""
        if self.sample_subtype_id:
            if self.sample_subtype_id.sample_type_id.code == 'MASONRY':
                efflorescence_template = self.env['lab.test.template'].search([('code', '=', 'BRICK_EFFLOR')], limit=1)
                if efflorescence_template:
                    self.lab_test_template_id = efflorescence_template.id
            elif self.sample_subtype_id.default_test_template_id:
                self.lab_test_template_id = self.sample_subtype_id.default_test_template_id.id
    


    @api.onchange('task_id', 'product_id')
    def _onchange_task_product(self):
        """تحديث النوع الفرعي للعينة عند تغيير المهمة أو المنتج"""
        if self.task_id and self.product_id and not self.sample_subtype_id:
            form_line = self.task_id.form_line_ids.filtered(lambda l: l.product_id.id == self.product_id.id)
            if form_line and form_line.sample_subtype_id:
                self.sample_subtype_id = form_line.sample_subtype_id


    is_assigned_to_me = fields.Boolean(
        string='مكلف ',
        compute='_compute_is_assigned_to_me',
        search='_search_is_assigned_to_me',
        help='يحدد ما إذا كان المستخدم الحالي مكلف بأي فحص في هذه العينة'
    )
    

    assigned_emails = fields.Char(
        string='إيميلات المكلفين',
        compute='_compute_assigned_users',
        help='إيميلات جميع الفنيين المكلفين - للاستخدام في قوالب الإيميل'
    )
    
    assigned_names = fields.Char(
        string='أسماء المكلفين',
        compute='_compute_assigned_users',
        help='أسماء جميع الفنيين المكلفين - للاستخدام في قوالب الإيميل'
    )
    
    @api.depends('result_set_ids.testers_ids')
    def _compute_assigned_users(self):
        """حساب إيميلات وأسماء جميع الفنيين المكلفين"""
        for sample in self:
            assigned_users = sample.result_set_ids.mapped('testers_ids')
            
            emails = assigned_users.mapped('email')
            sample.assigned_emails = ','.join(filter(None, emails))
            
            names = assigned_users.mapped('name')
            sample.assigned_names = ' و '.join(filter(None, names))
    
    @api.depends('result_set_ids.testers_ids')
    def _compute_is_assigned_to_me(self):
        """حساب ما إذا كان المستخدم الحالي مكلف بأي فحص في هذه العينة"""
        for sample in self:
            assigned_users = sample.result_set_ids.mapped('testers_ids')
            sample.is_assigned_to_me = self.env.user in assigned_users
    
    def _search_is_assigned_to_me(self, operator, value):
        """تمكين البحث على حقل is_assigned_to_me"""
        if operator == '=' and value:
            return [('result_set_ids.testers_ids', 'in', [self.env.uid])]
        elif operator == '=' and not value:
            return [('result_set_ids.testers_ids', 'not in', [self.env.uid])]
        elif operator == '!=' and value:
            return [('result_set_ids.testers_ids', 'not in', [self.env.uid])]
        elif operator == '!=' and not value:
            return [('result_set_ids.testers_ids', 'in', [self.env.uid])]
        else:
            return []
    
    all_results_approved = fields.Boolean(
        string='جميع النتائج معتمدة',
        compute='_compute_all_results_approved',
        help='حقل محسوب يبين ما إذا كانت جميع مجموعات النتائج معتمدة'
    )
    
    @api.depends('result_set_ids.state', 'test_flow_ids.line_ids.result_set_id.state')
    def _compute_all_results_approved(self):
        """حساب ما إذا كانت جميع النتائج معتمدة - مع استثناء العينات التجريبية"""
        for sample in self:

            direct_result_sets = sample.result_set_ids
            flow_result_sets = sample.test_flow_ids.mapped('line_ids.result_set_id')
            all_result_sets = direct_result_sets + flow_result_sets
            
            if not all_result_sets:
                sample.all_results_approved = False
                continue
            

            non_experimental_sets = []
            for rs in all_result_sets:
                if sample._is_result_set_experimental(rs):
                    continue 
                non_experimental_sets.append(rs)
            

            if not non_experimental_sets:
                sample.all_results_approved = True 
            else:
                sample.all_results_approved = all(
                    rs.state in ('approved', 'completed') for rs in non_experimental_sets
                )
    
    def _is_result_set_experimental(self, result_set):
        """فحص إذا كانت مجموعة النتائج من عينة تجريبية (7 أيام أو احتياط)"""
        self.ensure_one()
        

        if not result_set.is_concrete_sample:
            return False
            

        sample = result_set.sample_id
        if not sample:
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
    
    

    
    consecutive_groups_count = fields.Integer(
        string='عدد المجموعات المتعاقبة',
        compute='_compute_consecutive_groups_data',
        help='عدد المجموعات المتعاقبة المتاحة لحساب المتوسطات'
    )
    
    consecutive_groups_data = fields.Html(
        string='بيانات المجموعات المتعاقبة',
        compute='_compute_consecutive_groups_data',
        help='جدول يعرض متوسطات المجموعات المتعاقبة',
        sanitize=False
    )
    
    show_consecutive_groups = fields.Boolean(
        string='عرض المجموعات المتعاقبة',
        compute='_compute_show_consecutive_groups',
        help='يحدد ما إذا كان يجب عرض المجموعات المتعاقبة للخرسانة'
    )
    
    @api.depends('concrete_sample_type_id')
    def _compute_is_concrete_sample(self):
        """تحديد ما إذا كانت هذه عينة خرسانية"""
        concrete_codes = ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES', 'CONCRETE_CORE']
        for sample in self:
            sample.is_concrete_sample = bool(
                sample.concrete_sample_type_id and 
                sample.concrete_sample_type_id.code in concrete_codes
            )
    
    @api.depends('concrete_sample_type_id', 'result_set_ids')
    def _compute_show_consecutive_groups(self):
        """تحديد ما إذا كان يجب عرض المجموعات المتعاقبة"""
        for sample in self:

            if (sample.concrete_sample_type_id and 
                sample.concrete_sample_type_id.code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS']):

                concrete_sets = sample.result_set_ids.filtered(
                    lambda rs: rs.is_concrete_sample and rs.concrete_age_days == '28'
                )
                sample.show_consecutive_groups = len(concrete_sets) >= 4
            else:
                sample.show_consecutive_groups = False
    
    @api.depends('result_set_ids.result_line_ids.value_numeric', 'concrete_sample_type_id')
    def _compute_consecutive_groups_data(self):
        """حساب بيانات المجموعات المتعاقبة"""
        for sample in self:
            if not sample.show_consecutive_groups:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            

            result_sets = sample.result_set_ids.filtered(
                lambda rs: (rs.is_concrete_sample and 
                           rs.concrete_age_days == '28' and 
                           rs.concrete_group_no)
            ).sorted('concrete_group_no')
            
            if len(result_sets) < 4:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            
            group_averages = []
            for rs in result_sets:
                avg_lines = rs.result_line_ids.filtered(
                    lambda l: l.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                )
                if avg_lines and avg_lines[0].value_numeric:
                    group_averages.append({
                        'group_no': rs.concrete_group_no,
                        'average': avg_lines[0].value_numeric
                    })
            
            if len(group_averages) < 4:
                sample.consecutive_groups_count = 0
                sample.consecutive_groups_data = ''
                continue
            
            consecutive_data = []
            window_size = 4
            
            ref_general = 0
            ref_min = 0
            general_margin = 3.0
            min_margin = 3.0
            
            if sample.task_id:
                ref_general = float(sample.task_id.reference_general_limit or 0)
                ref_min = float(sample.task_id.reference_min_limit or 0)
            
            for i in range(len(group_averages) - window_size + 1):
                window_groups = group_averages[i:i + window_size]
                window_avg = sum(g['average'] for g in window_groups) / window_size
                
                is_failed = False
                if ref_general and window_avg < (ref_general + general_margin):
                    is_failed = True
                
                consecutive_data.append({
                    'groups': f"{window_groups[0]['group_no']}-{window_groups[-1]['group_no']}",
                    'average': window_avg,
                    'is_failed': is_failed
                })
            
            sample.consecutive_groups_count = len(consecutive_data)
            
            if consecutive_data:
                html = '<div class="consecutive-groups-table">'
                html += '<h5 style="color: #4F81BD; margin-bottom: 10px;">متوسطات المجموعات المتعاقبة</h5>'
                html += '<table class="table table-sm table-bordered" style="font-size: 12px;">'
                html += '<thead style="background-color: #305496; color: white;">'
                html += '<tr><th style="text-align: center; padding: 4px;">المجموعات</th>'
                html += '<th style="text-align: center; padding: 4px;">متوسط القوة (N/mm²)</th>'
                html += '<th style="text-align: center; padding: 4px;">الحالة</th></tr></thead><tbody>'
                
                for data in consecutive_data:
                    bg_color = '#FFC7CE' if data['is_failed'] else '#C6EFCE'
                    status = 'فاشل' if data['is_failed'] else 'ناجح'
                    
                    html += f'<tr style="background-color: {bg_color};">'
                    html += f'<td style="text-align: center; padding: 4px;">{data["groups"]}</td>'
                    html += f'<td style="text-align: center; padding: 4px; font-weight: bold;">{data["average"]:.2f}</td>'
                    html += f'<td style="text-align: center; padding: 4px;">{status}</td>'
                    html += '</tr>'
                
                html += '</tbody></table>'
                
                if ref_general or ref_min:
                    html += '<div style="margin-top: 10px; font-size: 11px; color: #666;">'
                    html += '<strong>المرجع:</strong> '
                    if ref_general:
                        html += f'المعدل: {ref_general:.2f} N/mm² '
                html += '</div>'
            
            sample.consecutive_groups_data = html or False
    
    @api.depends('product_id.default_code', 'product_id.name')
    def _compute_bitumen_type(self):
        """تحديد نوع القير من المنتج"""
        for record in self:
            if record.product_id:
                product_code = record.product_id.default_code or ''
                product_name = record.product_id.name or ''
                
                if 'BASE' in product_code or 'أساس' in product_name:
                    record.bitumen_type = 'قير أساس'
                elif 'SURFACE' in product_code or 'تسطيح' in product_name:
                    record.bitumen_type = 'قير تسطيح'
                else:
                    record.bitumen_type = False
            else:
                record.bitumen_type = False
    
    @api.depends('product_id', 'bitumen_type',
                 'bitumen_comparison_level',
                 'result_set_ids.result_line_ids.value_numeric',
                 'result_set_ids.result_line_ids.value_text',
                 'result_set_ids.result_line_ids.value_selection')
    def _compute_bitumen_results_summary(self):
        """إنشاء ملخص علمي منظم لنتائج القير لكل مجموعة بحسب رقم المجموعة"""
        for record in self:

            if not record.bitumen_type or record.bitumen_type not in ['قير أساس', 'قير تسطيح']:
                record.bitumen_results_summary = False
                continue


            asphalt_sets = record.result_set_ids.filtered(lambda rs: rs.template_id and rs.template_id.industry_type == 'asphalt')
            if not asphalt_sets:
                record.bitumen_results_summary = '<p>لا توجد نتائج فحص مرتبطة بالعينة بعد</p>'
                continue

            group_nos = sorted(set([(rs.test_group_no or 1) for rs in asphalt_sets]))

            is_surface = (record.bitumen_type == 'قير تسطيح')
            is_base = (record.bitumen_type == 'قير أساس')
            pen_ranges = [(18,60),(15,35),(12,25)] if is_surface else [(50,100),(25,50),(20,40)]
            soft_ranges = [(57,66),(70,80),(85,96),(99,107)] if is_surface else [(46,60),(63,77),(83,93)]
            duct_mins = [10,3,2.5,1.5] if is_surface else [30,10,2]
            flash_min = 302 if is_surface else 232
            max_level = 4 if is_surface else 3

            def pick_level_for_group(g_sets):
                lvl = None
                rs_with_lvl = g_sets.filtered(lambda x: getattr(x, 'bitumen_comparison_level', False))
                if rs_with_lvl:
                    lvl = rs_with_lvl[0].bitumen_comparison_level
                elif getattr(record, 'bitumen_comparison_level', False):
                    lvl = record.bitumen_comparison_level
                try:
                    lvl_idx = max(1, min(int(lvl or '1'), max_level))
                except Exception:
                    lvl_idx = 1
                return lvl_idx

            def get_value_for(g_sets, crit_codes):
                lines = g_sets.mapped('result_line_ids').filtered(lambda l: l.criterion_id and l.criterion_id.code in crit_codes and l.value_numeric not in (None, False))
                return lines and lines[0].value_numeric or None

            html = f"""
            <div class="bitumen-results-summary">
                <h4 style="margin:0 0 8px 0;">ملخص نتائج {record.bitumen_type} - العينة {record.name}</h4>
                <table class="table table-sm table-bordered" style="font-size:12px; text-align:center;">
                    <thead style="background:#f1f1f1;">
                        <tr>
                            <th style="width:8%;">المجموعة</th>
                            <th style="width:14%;">النوع</th>
                            <th style="width:14%;">الاختراق (0.1 مم)</th>
                            <th style="width:14%;">نقطة الليونة (°م)</th>
                            <th style="width:14%;">اللدونة (سم)</th>
                            <th style="width:14%;">نقطة الوميض (°م)</th>
                            <th style="width:12%;">النتيجة</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for g in group_nos:
                g_sets = asphalt_sets.filtered(lambda rs: (rs.test_group_no or 1) == g)
                lvl_idx = pick_level_for_group(g_sets)

                pen_val = get_value_for(g_sets, ['PENTEST_AVG'])
                soft_val = get_value_for(g_sets, ['SOFTENING_AVG'])
                duct_val = get_value_for(g_sets, ['DUCTILITY_TEST_AVG'])
                flash_val = get_value_for(g_sets, ['FLASH_POINT', 'FLASH_IGNITION_POINT'])

                pen_spec = None
                soft_spec = None
                duct_spec = None
                if lvl_idx - 1 < len(pen_ranges):
                    pen_spec = pen_ranges[lvl_idx-1]
                if lvl_idx - 1 < len(soft_ranges):
                    soft_spec = soft_ranges[lvl_idx-1]
                if lvl_idx - 1 < len(duct_mins):
                    duct_spec = duct_mins[lvl_idx-1]

                tests_present = 0
                fails = 0

                def render_cell(val, ok, spec_text):
                    if val is None:
                        return f"—<div style='font-size:10px;color:#666;'>{spec_text}</div>"
                    color = '#28a745' if ok else '#dc3545'
                    star = '' if ok else "<sup style='font-size:10px;'>*</sup>"
                    return f"<span style='color:{color};font-weight:600;'>{val:.1f}{star}</span><div style='font-size:10px;color:#666;'>{spec_text}</div>"

                pen_ok = True
                pen_cell = "—"
                if pen_val is not None and pen_spec:
                    tests_present += 1
                    pen_ok = (pen_spec[0] <= pen_val <= pen_spec[1])
                    if not pen_ok:
                        fails += 1
                    pen_cell = render_cell(pen_val, pen_ok, f"المواصفة: {pen_spec[0]}–{pen_spec[1]}")
                else:
                    pen_cell = render_cell(pen_val, True, f"المواصفة: {'–'.join(map(str, pen_spec)) if pen_spec else 'غير متاح'}")

                soft_ok = True
                soft_cell = "—"
                if soft_val is not None and soft_spec:
                    tests_present += 1
                    soft_ok = (soft_spec[0] <= soft_val <= soft_spec[1])
                    if not soft_ok:
                        fails += 1
                    soft_cell = render_cell(soft_val, soft_ok, f"النطاق: {soft_spec[0]}–{soft_spec[1]}")
                else:
                    soft_cell = render_cell(soft_val, True, f"النطاق: {'–'.join(map(str, soft_spec)) if soft_spec else 'غير متاح'}")

                duct_ok = True
                duct_cell = "—"
                if duct_val is not None and duct_spec is not None:
                    tests_present += 1
                    duct_ok = (duct_val >= float(duct_spec))
                    if not duct_ok:
                        fails += 1
                    duct_cell = render_cell(duct_val, duct_ok, f"الحد الأدنى: ≥ {duct_spec}")
                else:
                    duct_cell = render_cell(duct_val, True, f"الحد الأدنى: ≥ {duct_spec if duct_spec is not None else 'غير متاح'}")

                flash_ok = True
                flash_cell = "—"
                if flash_val is not None:
                    tests_present += 1
                    flash_ok = (flash_val >= flash_min)
                    if not flash_ok:
                        fails += 1
                    flash_cell = render_cell(flash_val, flash_ok, f"الحد الأدنى: ≥ {flash_min}")
                else:
                    flash_cell = render_cell(flash_val, True, f"الحد الأدنى: ≥ {flash_min}")

                if tests_present == 0:
                    group_status = ("غير مكتمل", "#6c757d")
                else:
                    group_status = (("ناجح", "#28a745") if fails == 0 else ("فاشل", "#dc3545"))


                lvl_names_surface = ['النوع الأول','النوع الثاني','النوع الثالث','النوع الرابع']
                lvl_names_base = ['المستوى الأول','المستوى الثاني','المستوى الثالث']
                lvl_name = lvl_names_surface[lvl_idx-1] if is_surface else lvl_names_base[lvl_idx-1]

                html += f"""
                    <tr>
                        <td style="vertical-align:middle;">{g}</td>
                        <td style="vertical-align:middle;">{lvl_name}</td>
                        <td>{pen_cell}</td>
                        <td>{soft_cell}</td>
                        <td>{duct_cell}</td>
                        <td>{flash_cell}</td>
                        <td style="vertical-align:middle;color:{group_status[1]};font-weight:700;">{group_status[0]}</td>
                    </tr>
                """

            html += f"""
                    </tbody>
                </table>
                <div style="font-size:11px;color:#666;">
                    <div><strong>المراجع القياسية:</strong> D5 (الاختراق), D36 (الليونة بالحلقة والكرة), D113 (اللدونة), D92 (نقطة الوميض).</div>
                    <div><strong>ملاحظة:</strong> علامة * تشير إلى عدم المطابقة للمواصفة في الخانة.</div>
                </div>
            </div>
            """

    @api.depends('product_id.product_tmpl_id.sample_type_id.code')
    def _compute_is_asphalt_mix_sample(self):
        for sample in self:
            try:
                st_code = (sample.product_id.product_tmpl_id.sample_type_id.code or '').upper() if sample.product_id and sample.product_id.product_tmpl_id and sample.product_id.product_tmpl_id.sample_type_id else ''
            except Exception:
                st_code = ''
            sample.is_asphalt_mix_sample = (st_code == 'ASPHALT_MIX')

    @api.depends(
        'is_asphalt_mix_sample',
        'sample_subtype_id.code',
        'result_set_ids.template_id.code',
        'result_set_ids.test_group_no',
        'result_set_ids.result_line_ids.value_numeric',
        'result_set_ids.result_line_ids.result_value_computed'
    )
    def _compute_asphalt_mix_results_summary(self):
        for sample in self:
            # Default
            sample.asphalt_mix_results_summary = False

            if not sample.is_asphalt_mix_sample:
                continue

            # Collect only ASPHALT_* result sets for this sample
            try:
                asp_sets = sample.result_set_ids.filtered(lambda r: (r.template_id and (r.template_id.code or '').upper().startswith('ASPHALT_')))
            except Exception:
                asp_sets = self.env['lab.result.set']

            if not asp_sets:
                sample.asphalt_mix_results_summary = '<p>لا توجد نتائج فحص مرتبطة بالعينة بعد</p>'
                continue

            group_nos = sorted(set([(rs.test_group_no or 1) for rs in asp_sets]))

            # Layer thresholds
            layer_code = (sample.sample_subtype_id.code or '').upper() if sample.sample_subtype_id else ''
            ac_min = 8.0 if layer_code == 'SURFACE' else (5.0 if layer_code == 'BASE' else None)
            av_range = (3.0, 5.0) if layer_code == 'SURFACE' else ((3.0, 6.0) if layer_code == 'BASE' else None)
            mar_min = 5.0 if layer_code == 'BASE' else None  # BASE ≥ 5.0 kN
            tsr_min = 70.0  # default per template

            def get_val(g, tmpl_code, crit_code):
                rs = asp_sets.filtered(lambda r: (r.template_id and (r.template_id.code or '').upper() == tmpl_code) and ((r.test_group_no or 1) == g))[:1]
                if not rs:
                    return None
                line = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == crit_code)[:1]
                if not line:
                    return None
                val = line.value_numeric
                if (val is None or val is False) and hasattr(line, 'result_value_computed'):
                    val = line.result_value_computed
                try:
                    return float(val) if val not in (None, False) else None
                except Exception:
                    return None

            def get_class(g):
                rs = asp_sets.filtered(lambda r: (r.template_id and (r.template_id.code or '').upper() == 'ASPHALT_GRADATION_T30_T164') and ((r.test_group_no or 1) == g))[:1]
                return rs.asphalt_selected_class if rs else None

            # Build HTML summary table
            rows_html = ''
            for g in group_nos:
                ac_val = get_val(g, 'ASPHALT_GRADATION_T30_T164', 'AC_PERCENT_FILTERED') or get_val(g, 'ASPHALT_GRADATION_T30_T164', 'AC_PERCENT_SIMPLE')
                gmb_avg = get_val(g, 'ASPHALT_DENSITY_VOIDS', 'GMB_AVG')
                av_avg = get_val(g, 'ASPHALT_DENSITY_VOIDS', 'AV_AVG_PCT')
                mar_avg = get_val(g, 'ASPHALT_MARSHALL', 'MAR_STAB_AVG_KN')
                flow_avg = get_val(g, 'ASPHALT_MARSHALL', 'MAR_FLOW_AVG_MM')
                tsr_pct = get_val(g, 'ASPHALT_ITS_TSR', 'TSR_PCT')
                cls = get_class(g) or '-'

                # Compliance checks (missing values are neutral)
                def fmt(val, decimals=2):
                    return (f"{val:.{decimals}f}" if val is not None else '—')

                ac_ok = True if (ac_min is None or ac_val is None) else (ac_val >= ac_min)
                av_ok = True if (av_range is None or av_avg is None) else (av_range[0] <= av_avg <= av_range[1])
                mar_ok = True if (mar_min is None or mar_avg is None) else (mar_avg >= mar_min)
                tsr_ok = True if (tsr_pct is None) else (tsr_pct >= tsr_min)

                checks = [ac_ok, av_ok, mar_ok, tsr_ok]
                present = [v is not None for v in [ac_val, av_avg, mar_avg, tsr_pct]]
                if not any(present):
                    group_status = ('غير مكتمل', 'secondary')
                else:
                    group_status = (('ناجح', 'success') if all(checks) else ('فاشل', 'danger'))

                # Notes for specs (avoid nested f-strings/backslashes)
                ac_note = ''
                if (ac_min is not None) and (ac_val is not None):
                    ac_note = ' <small class="text-muted">(≥ {:.1f})</small>'.format(ac_min)
                av_note = ''
                if (av_range is not None) and (av_avg is not None):
                    av_note = ' <small class="text-muted">({:.1f}–{:.1f})</small>'.format(av_range[0], av_range[1])
                mar_note = ''
                if (mar_min is not None) and (mar_avg is not None):
                    mar_note = ' <small class="text-muted">(≥ {:.1f})</small>'.format(mar_min)
                tsr_note = ' <small class="text-muted">(≥ {:.0f})</small>'.format(tsr_min)

                ac_cell = f"{fmt(ac_val, 1)}{ac_note}"
                gmb_cell = fmt(gmb_avg, 3)
                av_cell = f"{fmt(av_avg, 2)}{av_note}"
                mar_cell = f"{fmt(mar_avg, 2)}{mar_note}"
                flow_cell = fmt(flow_avg, 2)
                tsr_cell = f"{fmt(tsr_pct, 0)}{tsr_note}"

                rows_html += (
                    f"<tr>"
                    f"<td style='vertical-align:middle;text-align:center;'>{g}</td>"
                    f"<td style='vertical-align:middle;text-align:center;'>{cls}</td>"
                    f"<td style='text-align:center;'>{ac_cell}</td>"
                    f"<td style='text-align:center;'>{gmb_cell}</td>"
                    f"<td style='text-align:center;'>{av_cell}</td>"
                    f"<td style='text-align:center;'>{mar_cell}</td>"
                    f"<td style='text-align:center;'>{flow_cell}</td>"
                    f"<td style='text-align:center;'>{tsr_cell}</td>"
                    f"<td style='vertical-align:middle;text-align:center;'><span class='badge bg-{group_status[1]}'>{group_status[0]}</span></td>"
                    f"</tr>"
                )

            header_info = (
                f"<p><b>نوع الطبقة:</b> {(sample.sample_subtype_id.name or '-') if sample.sample_subtype_id else '-'} "
                f"&nbsp; | &nbsp; <b>الرمز الحقلي:</b> {sample.field_serial or ''}</p>"
            )

            html = [
                "<div class='card'><div class='card-body'>",
                header_info,
                "<table class='table table-sm table-bordered' style='font-size:12px;text-align:center;'>",
                "<thead><tr>",
                "<th style='width:8%;'>المجموعة</th>",
                "<th style='width:8%;'>الفئة</th>",
                "<th style='width:12%;'>AC %</th>",
                "<th style='width:12%;'>Gmb (معدل)</th>",
                "<th style='width:12%;'>AV % (معدل)</th>",
                "<th style='width:14%;'>ثبات مُصحح (kN)</th>",
                "<th style='width:12%;'>الزحف (مم)</th>",
                "<th style='width:10%;'>TSR %</th>",
                "<th style='width:12%;'>نتيجة المجموعة</th>",
                "</tr></thead><tbody>",
                rows_html or "",
                "</tbody></table>",
                "<div style='font-size:11px;color:#666;'><div><strong>ملاحظة:</strong> القيم الناقصة لا تؤثر على الحكم النهائي للمجموعة وتُظهر (غير مكتمل).</div></div>",
                "</div></div>"
            ]
            sample.asphalt_mix_results_summary = ''.join(html)


    @api.depends('is_core_ui',
                 'result_set_ids.template_id.code',
                 'result_set_ids.result_line_ids.value_numeric',
                 'result_set_ids.result_line_ids.is_compliant',
                 'result_set_ids.result_line_ids.sample_no')
    def _compute_core_results_summary(self):
        """إنشاء ملخص منظم لفحص الكور (سمك وحدل) يظهر فقط لعينة الكور"""
        for record in self:
            if not getattr(record, 'is_core_ui', False):
                record.core_results_summary = False
                continue


            core_sets = record.result_set_ids.filtered(lambda rs: rs.template_id and rs.template_id.code == 'CONCRETE_CORE_TEST')
            if not core_sets:
                record.core_results_summary = '<p>لا توجد نتائج فحص كور متاحة للعرض</p>'
                continue


            sorted_sets = core_sets.sorted(lambda rs: (rs.concrete_group_no or 0, rs.id))

            def line_val(line, fmt="{:.2f}"):
                if not line:
                    return "-", False
                val = line.value_numeric if hasattr(line, 'value_numeric') else None
                val_str = (fmt.format(val) if isinstance(val, (int, float)) else "-") if val not in (None, False) else "-"
                return val_str, (not getattr(line, 'is_compliant', True))

            def get_line(rs, code, sample_no=None):
                lines = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == code and (sample_no is None or getattr(l, 'sample_no', None) == sample_no))
                return lines and lines[0] or False


            html = """
            <div class="core-results-summary">
                <h4 style="margin:0 0 8px 0;">ملخص نتائج الكور - العينة {name}</h4>
                <table class="table table-sm table-bordered" style="font-size:12px; text-align:center;">
                    <thead style="background:#f1f1f1;">
                        <tr>
                            <th style="width:8%;">م</th>
                            <th style="width:9%;">سمك1 (سم)</th>
                            <th style="width:9%;">سمك2 (سم)</th>
                            <th style="width:10%;">السمك العام</th>
                            <th style="width:10%;">كثافة موقعي1</th>
                            <th style="width:10%;">كثافة موقعي2</th>
                            <th style="width:10%;">كثافة مختبري1</th>
                            <th style="width:10%;">كثافة مختبري2</th>
                            <th style="width:8%;">حدل1%</th>
                            <th style="width:8%;">حدل2%</th>
                            <th style="width:8%;">معدل الحدل%</th>
                            <th style="width:10%;">الحالة</th>
                        </tr>
                    </thead>
                    <tbody>
            """.format(name=record.name)


            ref_thickness = None
            ref_compaction = None

            for idx, rs in enumerate(sorted_sets, start=1):

                serial_raw = rs.concrete_field_serial or rs.concrete_field_code or ''
                display_serial = serial_raw.split('/')[-1] if serial_raw else str(idx)

                l_t1 = get_line(rs, 'CORE_SIZE_AVG', 1)
                l_t2 = get_line(rs, 'CORE_SIZE_AVG', 2)
                l_over = get_line(rs, 'CORE_THICKNESS_OVERALL_AVG')

                l_bd1 = get_line(rs, 'BULK_DENSITY', 1)
                l_bd2 = get_line(rs, 'BULK_DENSITY', 2)
                l_ld1 = get_line(rs, 'LABORATORY_DENSITY', 1)
                l_ld2 = get_line(rs, 'LABORATORY_DENSITY', 2)

                l_c1 = get_line(rs, 'COMPACTION_RATIO', 1)
                l_c2 = get_line(rs, 'COMPACTION_RATIO', 2)
                l_cavg = get_line(rs, 'COMPACTION_RATIO_AVG')

                t1, t1_fail = line_val(l_t1)
                t2, t2_fail = line_val(l_t2)
                tover, tover_fail = line_val(l_over)
                bd1, _ = line_val(l_bd1)
                bd2, _ = line_val(l_bd2)
                ld1, _ = line_val(l_ld1, fmt="{:.3f}")
                ld2, _ = line_val(l_ld2, fmt="{:.3f}")
                c1, _ = line_val(l_c1)
                c2, _ = line_val(l_c2)
                cavg, cavg_fail = line_val(l_cavg)


                tover_disp = tover + ("<sup style='font-size:10px;'>*</sup>" if tover_fail else "")
                cavg_disp = cavg + ("<sup style='font-size:10px;'>*</sup>" if cavg_fail else "")


                values_present = any(v not in (None, False, '-') for v in [t1, t2, tover, c1, c2, cavg])
                if not values_present:
                    status_txt = 'غير مكتمل'
                    status_color = '#6c757d'
                else:
                    any_fail = any([tover_fail, cavg_fail])
                    if any_fail:
                        status_txt = 'فاشل'
                        status_color = '#dc3545'
                    else:
                        status_txt = 'ناجح'
                        status_color = '#28a745'

                html += f"""
                    <tr>
                        <td style="vertical-align:middle;">{display_serial}</td>
                        <td>{t1}</td>
                        <td>{t2}</td>
                        <td>{tover_disp}</td>
                        <td>{bd1}</td>
                        <td>{bd2}</td>
                        <td>{ld1}</td>
                        <td>{ld2}</td>
                        <td>{c1}</td>
                        <td>{c2}</td>
                        <td>{cavg_disp}</td>
                        <td style="vertical-align:middle;color:{status_color};font-weight:700;">{status_txt}</td>
                    </tr>
                """

                if ref_thickness is None and getattr(rs, 'reference_general_limit', False):
                    ref_thickness = rs.reference_general_limit
                if ref_compaction is None and getattr(rs, 'core_compaction_ratio_reference', False):
                    ref_compaction = rs.core_compaction_ratio_reference

            html += """
                    </tbody>
                </table>
            """

            foot_parts = []
            if ref_thickness:
                try:
                    foot_parts.append(f"السمك المطلوب: {float(ref_thickness):.2f} سم")
                except Exception:
                    foot_parts.append(f"السمك المطلوب: {ref_thickness}")
            if ref_compaction:
                try:
                    foot_parts.append(f"نسبة الحدل الدنيا: ≥ {float(ref_compaction):.2f}%")
                except Exception:
                    foot_parts.append(f"نسبة الحدل الدنيا: ≥ {ref_compaction}%")

            if foot_parts:
                html += f"""
                <div style="font-size:11px;color:#666;">{' | '.join(foot_parts)}</div>
                """

            html += """
            </div>
            """

            record.core_results_summary = html
    
    @api.depends('is_field_density_sample',
                 'result_set_ids.template_id.code',
                 'result_set_ids.result_line_ids.value_numeric',
                 'result_set_ids.core_compaction_ratio_reference',
                 'task_id.core_compaction_ratio')
    def _compute_field_density_results_summary(self):
        """إنشاء ملخص منظم للكثافة الموقعية يظهر فقط لعينة FIELD_DENSITY"""
        for record in self:
            if not getattr(record, 'is_field_density_sample', False):
                record.field_density_results_summary = False
                continue

            fd_sets = record.result_set_ids.filtered(
                lambda rs: rs.template_id and rs.template_id.code and 'FIELD_DENSITY' in rs.template_id.code
            )
            if not fd_sets:
                record.field_density_results_summary = '<p>لا توجد نتائج فحص كثافة موقعية متاحة للعرض</p>'
                continue

            sorted_sets = fd_sets.sorted('test_group_no')

            def line_value(rs, code):
                """Return numeric value for the first line with given code, or None if not found.
                Do not collapse 0.0 to False, so zeros are shown correctly in the UI summary.
                """
                lines = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == code)
                return lines[0].value_numeric if lines else None

            html = """
            <div class="field-density-results-summary">
                <h4 style="margin:0 0 8px 0;">ملخص نتائج الكثافة الموقعية - العينة {name}</h4>
                <table class="table table-sm table-bordered" style="font-size:12px; text-align:center;">
                    <thead style="background:#f1f1f1;">
                        <tr>
                            <th style="width:8%;">المجموعة</th>
                            <th style="width:16%;">الرمز</th>
                            <th style="width:14%;">الرطوبة (%)</th>
                            <th style="width:18%;">الكثافة الجافة (كغم/م³)</th>
                            <th style="width:18%;">الكثافة المختبرية (كغم/م³)</th>
                            <th style="width:14%;">نسبة الحدل %</th>
                        </tr>
                    </thead>
                    <tbody>
            """.format(name=record.name)

            for idx, rs in enumerate(sorted_sets, start=1):
                # الرمز الحقلـي/المختبري إن وجد
                serial_raw = getattr(rs, 'concrete_field_serial', False) or getattr(rs, 'concrete_field_code', False) or ''
                display_serial = serial_raw.split('/')[-1] if serial_raw else str(idx)

                # الرطوبة: متوسط من خطوط MOISTURE_CONTENT داخل نفس المجموعة
                moist_lines = rs.result_line_ids.filtered(lambda l: l.criterion_id and l.criterion_id.code == 'MOISTURE_CONTENT')
                mvals = [l.value_numeric for l in moist_lines if l.value_numeric not in (None, False)]
                moist_avg = (sum(mvals) / len(mvals)) if mvals else None

                dry_avg = line_value(rs, 'DRY_DENSITY_AVG')
                lab_max = line_value(rs, 'LAB_MAX_DRY_DENSITY')
                comp_avg = line_value(rs, 'COMPACTION_RATIO_AVG')
                ref_comp = getattr(rs, 'core_compaction_ratio_reference', False) or getattr(record.task_id, 'core_compaction_ratio', False) or False
                star = ''
                if comp_avg not in (None, False) and ref_comp:
                    try:
                        if float(comp_avg) < float(ref_comp):
                            star = "<sup style='color:#dc3545;'>*</sup>"
                    except Exception:
                        star = ''
                # تنسيق الأرقام إلى 3 منازل عشرية لعرض نظيف
                def fmt3(val):
                    try:
                        return f"{float(val):.3f}"
                    except Exception:
                        return str(val) if val not in (None, '') else ''

                moist_disp = '-' if moist_avg is None else fmt3(moist_avg)
                dry_disp = '-' if dry_avg is None else fmt3(dry_avg)
                labmax_disp = '-' if lab_max is None else fmt3(lab_max)
                comp_base = '' if comp_avg is None else fmt3(comp_avg)
                comp_disp = '-' if comp_base == '' else f"{comp_base}{star}"

                html += f"""
                    <tr>
                        <td style="vertical-align:middle;">{idx}</td>
                        <td>{display_serial}</td>
                        <td>{moist_disp}</td>
                        <td>{dry_disp}</td>
                        <td>{labmax_disp}</td>
                        <td>{comp_disp}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

            record.field_density_results_summary = html
    
    def _get_penetration_level(self, value):
        """تحديد مستوى الاختراق حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':

            if 18 <= value <= 60:
                return "النوع الأول", "18-60"
            elif 15 <= value <= 35:
                return "النوع الثاني", "15-35"
            elif 12 <= value <= 25:
                return "النوع الثالث", "12-25"
            else:
                return "خارج المواصفات", f"القيمة {value} خارج النطاقات المقبولة"
                
        elif self.bitumen_type == 'قير أساس':
            if 50 <= value <= 100:
                return "المستوى الأول", "50-100"
            elif 25 <= value <= 50:
                return "المستوى الثاني", "25-50"
            elif 20 <= value <= 40:
                return "المستوى الثالث", "20-40"
            else:
                return "خارج المواصفات", f"القيمة {value} خارج النطاقات المقبولة"
        
        return "غير محدد", ""
    
    def _get_ductility_level(self, value):
        """تحديد مستوى الاستطالة حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':
            if value >= 10:
                return "النوع الأول", "≥ 10 سم"
            elif value >= 3:
                return "النوع الثاني", "≥ 3 سم"
            elif value >= 2.5:
                return "النوع الثالث", "≥ 2.5 سم"
            elif value >= 1.5:
                return "النوع الرابع", "≥ 1.5 سم"
            else:
                return "خارج المواصفات", f"القيمة {value} أقل من 1.5 سم"
                
        elif self.bitumen_type == 'قير أساس':
            if value >= 30:
                return "المستوى الأول", "≥ 30 سم"
            elif value >= 10:
                return "المستوى الثاني", "≥ 10 سم"
            elif value >= 2:
                return "المستوى الثالث", "≥ 2 سم"
            else:
                return "خارج المواصفات", f"القيمة {value} أقل من 2 سم"
        
        return "غير محدد", ""
    
    def _get_softening_level(self, value):
        """تحديد مستوى الليونة حسب نوع القير والقيمة"""
        if not self.bitumen_type:
            return "غير محدد", ""
            
        if self.bitumen_type == 'قير تسطيح':

            if 57 <= value <= 66:
                return "النوع الأول", "57-66°م"
            elif 70 <= value <= 80:
                return "النوع الثاني", "70-80°م"
            elif 85 <= value <= 96:
                return "النوع الثالث", "85-96°م"
            elif 99 <= value <= 107:
                return "النوع الرابع", "99-107°م"
            else:
                return "خارج المواصفات", f"القيمة {value}°م خارج النطاقات المقبولة"
                
        elif self.bitumen_type == 'قير أساس':
            if 46 <= value <= 60:
                return "المستوى الأول", "46-60°م"
            elif 63 <= value <= 77:
                return "المستوى الثاني", "63-77°م"
            elif 83 <= value <= 93:
                return "المستوى الثالث", "83-93°م"
            else:
                return "خارج المواصفات", f"القيمة {value}°م خارج النطاقات المقبولة"
        
        return "غير محدد", ""
    
    def _get_all_penetration_levels(self):
        """الحصول على جميع مستويات الاختراق للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "18-60", "0.1 مم"),
                ("النوع الثاني", "15-35", "0.1 مم"),
                ("النوع الثالث", "12-25", "0.1 مم"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "50-100", "0.1 مم"),
                ("المستوى الثاني", "25-50", "0.1 مم"),
                ("المستوى الثالث", "20-40", "0.1 مم"),
            ]
        return []
    
    def _get_all_ductility_levels(self):
        """الحصول على جميع مستويات الاستطالة للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "≥ 10", "سم"),
                ("النوع الثاني", "≥ 3", "سم"),
                ("النوع الثالث", "≥ 2.5", "سم"),
                ("النوع الرابع", "≥ 1.5", "سم"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "≥ 30", "سم"),
                ("المستوى الثاني", "≥ 10", "سم"),
                ("المستوى الثالث", "≥ 2", "سم"),
            ]
        return []
    
    def _get_all_softening_levels(self):
        """الحصول على جميع مستويات الليونة للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [
                ("النوع الأول", "57-66", "°م"),
                ("النوع الثاني", "70-80", "°م"),
                ("النوع الثالث", "85-96", "°م"),
                ("النوع الرابع", "99-107", "°م"),
            ]
        elif self.bitumen_type == 'قير أساس':
            return [
                ("المستوى الأول", "46-60", "°م"),
                ("المستوى الثاني", "63-77", "°م"),
                ("المستوى الثالث", "83-93", "°م"),
            ]
        return []
    
    def _get_all_flash_point_levels(self):
        """الحصول على مستويات نقطة الوميض للعرض"""
        if not self.bitumen_type:
            return []
        
        if self.bitumen_type == 'قير تسطيح':
            return [("الحد الأدنى المطلوب", "≥ 302", "°م")]
        elif self.bitumen_type == 'قير أساس':
            return [("الحد الأدنى المطلوب", "≥ 232", "°م")]
        return []
    
    def _generate_levels_table(self, test_type, current_value=None):
        """إنشاء جدول المستويات مع تمييز المستوى المطبق"""
        levels = []
        applied_level = ""
        chosen_level_name = ""
        
        if test_type == 'penetration':
            levels = self._get_all_penetration_levels()
            if current_value is not None:
                applied_level, _ = self._get_penetration_level(current_value)
        elif test_type == 'ductility':
            levels = self._get_all_ductility_levels()
            if current_value is not None:
                applied_level, _ = self._get_ductility_level(current_value)
        elif test_type == 'softening':
            levels = self._get_all_softening_levels()
            if current_value is not None:
                applied_level, _ = self._get_softening_level(current_value)
        elif test_type == 'flash_point':
            levels = self._get_all_flash_point_levels()
            if current_value is not None:
                if self.bitumen_type == 'قير تسطيح' and current_value >= 302:
                    applied_level = "الحد الأدنى المطلوب"
                elif self.bitumen_type == 'قير أساس' and current_value >= 232:
                    applied_level = "الحد الأدنى المطلوب"
        

        if levels and hasattr(self, 'bitumen_comparison_level'):
            try:
                idx = int(self.bitumen_comparison_level or '1')
            except Exception:
                idx = 1
            idx = max(1, min(idx, len(levels)))
            chosen_level_name = levels[idx - 1][0]
        
        if not levels:
            return ""
        
        html = f"""
        <div class="mt-2">
            <h6 style="color: #6c757d; margin-bottom: 8px;">📋 مستويات {test_type.replace('_', ' ').title()}:</h6>
            <table class="table table-sm table-bordered" style="font-size: 0.85em;">
                <thead style="background-color: #f8f9fa;">
                    <tr>
                        <th style="width: 40%;">المستوى</th>
                        <th style="width: 35%;">النطاق</th>
                        <th style="width: 20%;">الوحدة</th>
                        <th style="width: 5%;">✓</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for level_name, range_value, unit in levels:
            is_chosen = (level_name == chosen_level_name) if chosen_level_name else False
            meets_chosen = (applied_level == chosen_level_name) if chosen_level_name else False
            row_style = "background-color: #fff3cd;" if is_chosen else ""
            check_mark = "✅" if (is_chosen and meets_chosen) else ("❌" if is_chosen else "")
            
            html += f"""
                    <tr style="{row_style}">
                        <td><strong>{level_name}</strong></td>
                        <td>{range_value}</td>
                        <td>{unit}</td>
                        <td style="text-align: center;">{check_mark}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return html
      
   # def unlink(self):
   #     """منع حذف العينات في حالة الاختبار أو المكتملة أو المصادق عليها"""
   #     for sample in self:
   #         if sample.state in ('testing', 'completed', 'approved'):
   #             from odoo.exceptions import UserError
   #             raise UserError(_('لا يمكن حذف العينة في حالة الاختبار أو بعد اكتمالها أو بعد المصادقة عليها.'))
   #     return super().unlink()
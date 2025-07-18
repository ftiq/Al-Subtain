# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class LabTestTemplate(models.Model):
    _name = 'lab.test.template'
    _description = 'قالب الفحص المختبري'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

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
        ('unique_code', 'unique(code)', 'رمز القالب يجب أن يكون فريداً!'),
        ('positive_duration', 'check(estimated_duration >= 0)', 'المدة المقدرة يجب أن تكون موجبة!'),
    ]

    name = fields.Char(
        string='اسم القالب',
        required=True,
        tracking=True,
        help='اسم قالب الفحص (مثل: فحص الطابوق الطيني حسب المواصفة العراقية IQS 44)'
    )
    
    code = fields.Char(
        string='رمز القالب',
        required=True,
        tracking=True,
        help='رمز فريد للقالب',
        index=True
    )
    
    description = fields.Html(
        string='الوصف',
        help='وصف تفصيلي لقالب الفحص'
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب عرض القالب'
    )
    
    active = fields.Boolean(
        string='نشط',
        default=True,
        tracking=True
    )
    
    allow_parallel_tests = fields.Boolean(
        string='السماح بالفحوصات المتوازية',
        default=False,
        tracking=True,
        help='عند تفعيله، يتم تجاهل الترتيب المتبع ويمكن العمل على كل الفحوصات دفعة واحدة'
    )
    
    product_ids = fields.Many2many(
        'product.template',
        'lab_template_product_rel',
        'template_id',
        'product_id',
        string='المنتجات المرتبطة',
        domain=[('is_sample_product', '=', True)],
        help='المنتجات (العينات) التي ينطبق عليها هذا القالب'
    )
    
    criterion_ids = fields.One2many(
        'lab.test.criterion',
        'template_id',
        string='معايير الفحص',
        help='قائمة معايير الفحص المطلوبة في هذا القالب'
    )
    
    criterion_count = fields.Integer(
        string='عدد المعايير',
        compute='_compute_criterion_count'
    )
    
    product_count = fields.Integer(
        string='عدد المنتجات',
        compute='_compute_product_count'
    )

    applicable_sample_type_ids = fields.Many2many(
        'lab.sample.type',
        'lab_sample_type_template_rel',
        'template_id',
        'sample_type_id',
        string='أنواع العينات القابلة للتطبيق',
        help='حدد أنواع العينات التي يمكن تطبيق هذا القالب عليها'
    )
    
    standard_code = fields.Char(
        string='رمز المعيار المرجعي',
        help='المعيار أو المواصفة المرجعية (مثل: ISO 17025، ASTM C39، IQS 44)'
    )
    
    quality_level = fields.Selection([
        ('basic', 'أساسي'),
        ('standard', 'قياسي'),
        ('advanced', 'متقدم'),
        ('specialized', 'متخصص')
    ], string='مستوى الجودة', default='standard')
    
    estimated_duration = fields.Float(
        string='المدة المقدرة (ساعة)',
        help='المدة المقدرة لإنجاز جميع فحوصات هذا القالب'
    )
    
    test_duration_days = fields.Integer(
        string='مدة الاختبار (يوم)',
        help='عدد الأيام بين أخذ العينة وإجراء الفحص (مثال: 7 أو 28 يوم)'
    )
    
    state = fields.Selection([
        ('draft', 'مسودة'),
        ('active', 'نشط'),
        ('archived', 'مؤرشف')
    ], string='الحالة', default='draft', tracking=True, index=True) 
    

    template_category = fields.Selection([
        ('construction', 'إنشائية'),
        ('chemical', 'كيميائية'), 
        ('mechanical', 'ميكانيكية'),
        ('environmental', 'بيئية'),
        ('quality', 'جودة'),
        ('custom', 'مخصص')
    ], string='فئة القالب', default='construction')
    
    industry_type = fields.Selection([
        ('concrete', 'خرسانة'),
        ('asphalt', 'أسفلت'),
        ('soil', 'تربة'),
        ('steel', 'حديد'),
        ('masonry', 'بناء'),
        ('water', 'مياه'),
        ('aggregate', 'ركام'),
        ('mixed', 'متنوع'),
        ('building', 'أبنية'),
        ('foundation', 'أساسات'),
        ('bridge', 'جسور'),
    ], string='نوع الصناعة')
    
    sample_size_min = fields.Integer(string='أقل عدد عينات', default=1)
    sample_size_max = fields.Integer(string='أكثر عدد عينات', default=100)
    sample_size_recommended = fields.Integer(string='العدد المُوصى به', default=3)
    
    environmental_conditions = fields.Text(
        string='الظروف البيئية المطلوبة',
        help='مثل: درجة الحرارة، الرطوبة، الضغط الجوي'
    )
    
    required_equipment = fields.Text(
        string='المعدات المطلوبة',
        help='قائمة بالمعدات والأجهزة المطلوبة لهذا الفحص'
    )
    
    @api.depends('criterion_ids')
    def _compute_criterion_count(self):
        for template in self:
            template.criterion_count = len(template.criterion_ids)
    
    @api.depends('product_ids')
    def _compute_product_count(self):
        for template in self:
            template.product_count = len(template.product_ids)
    
    @api.constrains('code')
    def _check_unique_code(self):
        for template in self:
            if template.code:
                existing = self.search([
                    ('code', '=', template.code),
                    ('id', '!=', template.id)
                ])
                if existing:
                    raise ValidationError(_('رمز القالب يجب أن يكون فريداً!'))
    

    
    def action_activate(self):
        """تفعيل القالب"""
        self.write({'state': 'active'})
        self.message_post(body=_('تم تفعيل قالب الفحص'))
    
    def action_archive(self):
        """أرشفة القالب"""
        self.write({'state': 'archived'})
        self.message_post(body=_('تم أرشفة قالب الفحص'))
    
    def action_duplicate(self):
        """نسخ القالب"""
        new_template = self.copy({
            'name': _('%s (نسخة)') % self.name,
            'code': _('%s_copy') % self.code,
            'state': 'draft'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('قالب الفحص الجديد'),
            'res_model': 'lab.test.template',
            'res_id': new_template.id,
            'view_mode': 'form',
            'target': 'current'
        }


class LabTestCriterion(models.Model):
    _name = 'lab.test.criterion'
    _description = 'معيار الفحص المختبري'
    _order = 'timer_sequence, sequence, name'

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
        ('unique_code_per_template', 'unique(template_id, code)', 
         'رمز المعيار يجب أن يكون فريداً ضمن القالب الواحد!'),
        ('valid_value_range', 'check(min_value <= max_value)', 
         'الحد الأدنى يجب أن يكون أقل من أو يساوي الحد الأعلى!'),
    ]

    name = fields.Char(
        string='اسم المعيار',
        required=True,
        help='اسم معيار الفحص (مثل: قوة الانضغاط، نسبة الامتصاص)'
    )
    
    code = fields.Char(
        string='رمز المعيار',
        required=True,
        help='رمز فريد للمعيار يستخدم في الحسابات والبرمجة',
        index=True 
    )
    
    template_id = fields.Many2one(
        'lab.test.template',
        string='قالب الفحص',
        required=True,
        ondelete='cascade',
        index=True  
    )
    
    sequence = fields.Integer(
        string='التسلسل',
        default=10,
        help='ترتيب عرض المعيار في القالب'
    )
    

    test_type = fields.Selection([
        ('numeric', 'رقمي'),
        ('text', 'نصي'),
        ('computed', 'محسوب'),
    ], string='نوع الإدخال', required=True, default='numeric')
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='وحدة القياس',
        help='وحدة القياس للمعيار الرقمي'
    )
    
    min_value = fields.Float(
        string='الحد الأدنى',
        help='أقل قيمة مسموحة للمعيار'
    )
    
    max_value = fields.Float(
        string='الحد الأعلى',
        help='أعلى قيمة مسموحة للمعيار'
    )
    
    target_value = fields.Float(
        string='القيمة المستهدفة',
        help='القيمة المثالية للمعيار'
    )
    
    global_standard_type = fields.Selection([
        ('iqs', 'IQS - المواصفة القياسية العراقية'),
    ], string='نوع المعيار')
    
    standard_code = fields.Char(
        string='رمز المعيار',
        help='مثل: ASTM C39, ISO 17025, IQS 5'
    )
    
    is_input_field = fields.Boolean(
        string='حقل إدخال',
        default=True,
        help='هل يتم إدخال هذا المعيار يدوياً؟'
    )
    
    is_computed_field = fields.Boolean(
        string='حقل محسوب',
        default=False,
        help='هل يتم حساب هذا المعيار تلقائياً؟'
    )

    reference_id = fields.Many2one(
        'lab.test.criterion',
        string='نسخ',
        help='اختر معياراً سابقاً لنسخ بياناته إلى هذا السطر',
        ondelete='set null'
    )

    @api.onchange('reference_id')
    def _onchange_reference_id(self):
        """عند اختيار معيار موجود، انسخ خصائصه إلى السطر الحالي."""
        if self.reference_id:
            ref = self.reference_id

            new_code = ref.code
            if self.template_id and ref.template_id == self.template_id:
                new_code = f"{ref.code}_copy"

            self.name = ref.name
            self.code = new_code
            self.test_type = ref.test_type
            self.uom_id = ref.uom_id.id
            self.min_value = ref.min_value
            self.max_value = ref.max_value
            self.target_value = ref.target_value
            self.is_computed_field = ref.is_computed_field
            self.computation_formula = ref.computation_formula
            self.depends_on_criteria_ids = [(6, 0, ref.depends_on_criteria_ids.ids)]
            self.selection_options = ref.selection_options
            self.is_required = ref.is_required
            self.is_critical = ref.is_critical
            self.is_summary_field = ref.is_summary_field
            self.timer_scope = ref.timer_scope
            self.waiting_unit = ref.waiting_unit
            self.waiting_value = ref.waiting_value
            self.lock_during_wait = ref.lock_during_wait

    computation_formula = fields.Text(
        string='معادلة الحساب',
        help='معادلة Python لحساب القيمة (مثل: result = input1 * input2 / 100)'
    )
    
    depends_on_criteria_ids = fields.Many2many(
        'lab.test.criterion',
        'criterion_dependency_rel',
        'criterion_id',
        'depends_on_id',
        string='يعتمد على المعايير',
        help='المعايير الأخرى المطلوبة لحساب هذا المعيار'
    )
    
    selection_options = fields.Text(
        string='خيارات الاختيار',
        help='قائمة الخيارات المتاحة للاختيار (كل خيار في سطر منفصل)\nمثال:\nممتاز\nجيد جداً\nجيد\nمقبول\nضعيف'
    )
    
    is_required = fields.Boolean(
        string='مطلوب',
        default=True,
        help='هل هذا المعيار مطلوب أم اختياري'
    )
    
    is_critical = fields.Boolean(
        string='حرج',
        default=False,
        help='هل هذا المعيار حرج (يؤثر على نتيجة الاجتياز)'
    )

    is_summary_field = fields.Boolean(
        string='حقل تلخيصي',
        default=False,
        help='عند تفعيله، يُحتسب هذا المعيار من سلسلة العينات مثل avg_series(), max_series() ... ويُعرض مرة واحدة فى تقرير الموحد.'
    )

    timer_scope = fields.Selection([
        ('per_set', 'لكل مجموعة نتائج'),
        ('per_line', 'لكل سطر نتيجة'),
    ], string='نطاق المؤقّت', default='per_set', help='تحديد ما إذا كان المؤقّت يطبق على كامل مجموعة النتائج أو على كل سطر على حدة.')

    waiting_unit = fields.Selection([
        ('minutes', 'دقائق'),
        ('hours', 'ساعات'),
        ('days', 'أيام'),
        ('weeks', 'أسابيع'),
    ], string='وحدة الانتظار', help='الوحدة الزمنية المطلوبة قبل السماح بإدخال القيمة.')

    waiting_value = fields.Integer(string='قيمة الانتظار', help='عدد الوحدات الزمنية المطلوبة (مثل 24 مع وحدة "ساعات").')

    lock_during_wait = fields.Boolean(string='قفل الحقول أثناء الانتظار', default=True, help='إذا تم التفعيل، تُقفل حقول الإدخال حتى انتهاء المؤقّت.')
    

    timer_sequence = fields.Integer(
        string='ترتيب المؤقت',
        compute='_compute_timer_sequence',
        store=True,
        help='ترتيب المعايير حسب الوقت المطلوب (الأطول أولاً)'
    )
    
    total_waiting_minutes = fields.Integer(
        string='إجمالي الانتظار (دقائق)',
        compute='_compute_total_waiting_minutes',
        store=True,
        help='إجمالي وقت الانتظار بالدقائق'
    )
    
    tolerance_percentage = fields.Float(
        string='نسبة التسامح (%)',
        help='نسبة التسامح المسموحة في القياس'
    )
    
    widget_type = fields.Selection([
        ('default', 'افتراضي'),
        ('integer', 'رقم صحيح'),
        ('float', 'رقم عشري'),
        ('percentage', 'نسبة مئوية'),
    ], string='نوع العنصر', default='default')
    
    instructions = fields.Html(
        string='تعليمات الفحص',
        help='تعليمات تفصيلية لإجراء هذا الفحص'
    )
    
    is_global = fields.Boolean(
        string='معيار عام',
        default=False,
        help='عند تفعيله يتم إنشاء سطر واحد فقط لهذا المعيار بغض النظر عن عدد العينات.'
    )
    
    help_text = fields.Text(
        string='نص المساعدة',
        help='نص مساعدة يظهر للمستخدم'
    )
    
    validation_rules = fields.Text(
        string='قواعد التحقق',
        help='قواعد Python للتحقق من صحة البيانات المدخلة'
    )

    @api.constrains('code', 'template_id')
    def _check_unique_code_in_template(self):
        for criterion in self:
            if criterion.code and criterion.template_id:
                existing = self.search([
                    ('code', '=', criterion.code),
                    ('template_id', '=', criterion.template_id.id),
                    ('id', '!=', criterion.id)
                ])
                if existing:
                    raise ValidationError(_('رمز المعيار يجب أن يكون فريداً داخل القالب!'))

    @api.constrains('min_value', 'max_value')
    def _check_value_range(self):
        for criterion in self:
            if criterion.test_type == 'numeric' and criterion.min_value and criterion.max_value:
                if criterion.min_value >= criterion.max_value:
                    raise ValidationError(_('الحد الأدنى يجب أن يكون أقل من الحد الأعلى!'))

    @api.onchange('test_type')
    def _onchange_test_type(self):
        """تحديث الحقول حسب نوع البيانات"""
        if self.test_type == 'computed':
            self.is_computed_field = True
            self.is_input_field = False
        else:
            self.is_computed_field = False
            self.is_input_field = True 

    @api.depends('waiting_unit', 'waiting_value')
    def _compute_total_waiting_minutes(self):
        """حساب إجمالي وقت الانتظار بالدقائق"""
        for criterion in self:
            if criterion.waiting_unit and criterion.waiting_value:
                if criterion.waiting_unit == 'minutes':
                    criterion.total_waiting_minutes = criterion.waiting_value
                elif criterion.waiting_unit == 'hours':
                    criterion.total_waiting_minutes = criterion.waiting_value * 60
                elif criterion.waiting_unit == 'days':
                    criterion.total_waiting_minutes = criterion.waiting_value * 60 * 24
                elif criterion.waiting_unit == 'weeks':
                    criterion.total_waiting_minutes = criterion.waiting_value * 60 * 24 * 7
                else:
                    criterion.total_waiting_minutes = 0
            else:
                criterion.total_waiting_minutes = 0

    @api.depends('total_waiting_minutes', 'timer_scope', 'sequence')
    def _compute_timer_sequence(self):
        """حساب ترتيب المعايير حسب الوقت المطلوب"""
        for criterion in self:
            if criterion.timer_scope and criterion.total_waiting_minutes > 0:
                criterion.timer_sequence = criterion.total_waiting_minutes + 1000
            else:
                criterion.timer_sequence = criterion.sequence or 10

    def copy(self, default=None):
        """إعادة تعريف دالة النسخ لجعل الكود فارغاً عند النسخ"""
        if default is None:
            default = {}
        

        default['code'] = ''
        

        if 'name' not in default:
            default['name'] = _('%s (نسخة)') % (self.name or '')
        
        return super(LabTestCriterion, self).copy(default)
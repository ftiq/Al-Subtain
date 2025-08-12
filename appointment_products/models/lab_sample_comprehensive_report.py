# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class LabSampleComprehensiveReport(models.TransientModel):
    """تقرير شامل للعينة المختبرية - يحفظ بيانات المجموعات بعد الحفظ"""
    _name = 'lab.sample.comprehensive.report'
    _description = 'Lab Sample Comprehensive Report - Persists Group Data'

    sample_id = fields.Many2one(
        'lab.sample',
        string='العينة',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    

    sample_name = fields.Char(related='sample_id.name', readonly=True)
    lab_number = fields.Char(related='sample_id.name', readonly=True)
    descriptive_title = fields.Char(string='العنوان الوصفي', compute='_compute_descriptive_title')
    

    project_name = fields.Char(string='اسم المشروع', compute='_compute_project_info')
    company_name = fields.Char(string='اسم الشركة', compute='_compute_project_info')
    

    casting_date = fields.Date(string='تاريخ الصب', compute='_compute_dates')
    testing_date = fields.Date(string='تاريخ الفحص', compute='_compute_dates')
    age_days = fields.Integer(string='العمر بالأيام', compute='_compute_dates')
    

    total_groups_count = fields.Integer(string='إجمالي المجموعات', compute='_compute_group_stats')
    tested_groups_28_count = fields.Integer(string='مجموعات 28 يوم المفحوصة', compute='_compute_group_stats')
    total_cubes_count = fields.Integer(string='إجمالي المكعبات', compute='_compute_group_stats')
    

    overall_average = fields.Float(string='المتوسط الإجمالي (N/mm²)', compute='_compute_statistics')
    min_group_average = fields.Float(string='أقل متوسط مجموعة', compute='_compute_statistics')
    max_group_average = fields.Float(string='أعلى متوسط مجموعة', compute='_compute_statistics')
    standard_deviation = fields.Float(string='الانحراف المعياري', compute='_compute_statistics')
    uncertainty_value = fields.Float(string='قيمة عدم التأكد', compute='_compute_statistics')
    

    sample_type = fields.Selection([
        ('concrete', 'خرسانة')
    ], string='نوع العينة', compute='_compute_sample_type', store=True)
    

    group_data_ids = fields.One2many(
        'lab.sample.report.group.data',
        'report_id',
        string='بيانات المجموعات'
    )
    

    @api.depends('sample_id')
    def _compute_sample_type(self):
        """تحديد نوع العينة (خرسانة فقط)"""
        for record in self:
            record.sample_type = 'concrete'

    @api.depends('sample_id', 'sample_id.lab_test_template_id', 'sample_id.sample_subtype_id', 'sample_type')
    def _compute_descriptive_title(self):
        """حساب العنوان الوصفي للتقرير"""
        for record in self:
            if record.sample_id:

                    test_name = ''
                    if record.sample_id.lab_test_template_id:
                        test_name = record.sample_id.lab_test_template_id.name
                    elif record.sample_id.sample_subtype_id and record.sample_id.sample_subtype_id.default_test_template_id:
                        test_name = record.sample_id.sample_subtype_id.default_test_template_id.name
                    else:
                        test_name = 'فحص مقاومة الانضغاط للخرسانة' 
                    
                    sample_type = ''
                    if record.sample_id.sample_subtype_id:
                        sample_type = record.sample_id.sample_subtype_id.name
                    elif record.sample_id.concrete_sample_type_id:
                        sample_type = record.sample_id.concrete_sample_type_id.name
                    else:
                        sample_type = 'عام'  
                    

                    record.descriptive_title = f"{test_name} - {sample_type}"
            else:
                record.descriptive_title = 'تقرير شامل للعينة المختبرية'

    @api.depends('sample_id')
    def _compute_project_info(self):
        """حساب معلومات المشروع"""
        for record in self:
            if record.sample_id:

                task = self.env['project.task'].search([
                    ('stock_receipt_id.move_line_ids.product_id', '=', record.sample_id.product_id.id)
                ], limit=1)
                
                if task:

                    project_name_from_answers = 'غير محدد'
                    if task.fsm_question_ids:

                        first_answer = task.fsm_question_ids.sorted('id')[0]

                        answer_value = first_answer.value_text_box or (first_answer.value_answer_id.name if first_answer.value_answer_id else '')
                        if answer_value:
                            project_name_from_answers = answer_value
                    
                    record.project_name = project_name_from_answers
                    record.company_name = task.project_id.partner_id.name or record.sample_id.company_id.name
                else:
                    record.project_name = 'غير محدد'
                    record.company_name = record.sample_id.company_id.name
            else:
                record.project_name = 'غير محدد'
                record.company_name = 'غير محدد'

    @api.depends('sample_id')
    def _compute_dates(self):
        """حساب التواريخ المهمة"""
        for record in self:
            if record.sample_id and record.sample_id.result_set_ids:

                result_sets_28 = record.sample_id.result_set_ids.filtered(
                    lambda rs: rs.concrete_age_days == '28' and rs.casting_date and rs.testing_date
                )
                
                if result_sets_28:
                    first_set = result_sets_28.sorted('id')[0]
                    record.casting_date = first_set.casting_date
                    record.testing_date = first_set.testing_date
                    
                    if record.casting_date and record.testing_date:
                        delta = record.testing_date - record.casting_date
                        record.age_days = delta.days
                    else:
                        record.age_days = 28
                else:
                    record.casting_date = False
                    record.testing_date = False
                    record.age_days = 28
            else:
                record.casting_date = False
                record.testing_date = False
                record.age_days = 28

    @api.depends('sample_id')
    def _compute_group_stats(self):
        """حساب إحصائيات المجموعات"""
        for record in self:
            if record.sample_id:
                result_sets = record.sample_id.result_set_ids
                

                groups_28_day = result_sets.filtered(
                    lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                               rs.concrete_group_no and
                               rs.concrete_age_days == '28')
                )
                
                record.total_groups_count = len(result_sets.filtered(lambda rs: rs.concrete_group_no))
                record.tested_groups_28_count = len(groups_28_day)
                

                record.total_cubes_count = record.tested_groups_28_count * 3
            else:
                record.total_groups_count = 0
                record.tested_groups_28_count = 0
                record.total_cubes_count = 0

    @api.depends('sample_id')
    def _compute_statistics(self):
        """حساب الإحصائيات الشاملة"""
        for record in self:
            if record.sample_id:

                overall_avg_set = record.sample_id.result_set_ids.filtered(
                    lambda rs: rs.template_id.code == 'CONCRETE_OVERALL_AVG'
                )
                
                if overall_avg_set:
                    overall_set = overall_avg_set[0]
                    

                    overall_avg_line = overall_set.result_line_ids.filtered(
                        lambda line: line.criterion_id.code == 'OVERALL_AVG_COMP_STRENGTH'
                    )
                    record.overall_average = overall_avg_line[0].value_numeric if overall_avg_line else 0.0
                    

                    std_dev_line = overall_set.result_line_ids.filtered(
                        lambda line: line.criterion_id.code == 'COMP_STD_DEVIATION'
                    )
                    record.standard_deviation = std_dev_line[0].value_numeric if std_dev_line else 0.0
                    
                    uncertainty_line = overall_set.result_line_ids.filtered(
                        lambda line: line.criterion_id.code == 'UNCERTAINTY_STRESS_VALUE'
                    )
                    record.uncertainty_value = uncertainty_line[0].value_numeric if uncertainty_line else 0.0
                    
                    groups_28_day = record.sample_id.result_set_ids.filtered(
                        lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                                   rs.concrete_group_no and
                                   rs.concrete_age_days == '28')
                    )
                    
                    group_averages = []
                    for group_set in groups_28_day:
                        avg_line = group_set.result_line_ids.filtered(
                            lambda line: line.criterion_id.code == 'AVG_COMP_STRENGTH_CONCRETE'
                        )
                        if avg_line and avg_line[0].value_numeric:
                            group_averages.append(avg_line[0].value_numeric)
                    
                    if group_averages:
                        record.min_group_average = min(group_averages)
                        record.max_group_average = max(group_averages)
                    else:
                        record.min_group_average = 0.0
                        record.max_group_average = 0.0
                else:
                    record.overall_average = 0.0
                    record.standard_deviation = 0.0
                    record.uncertainty_value = 0.0
                    record.min_group_average = 0.0
                    record.max_group_average = 0.0
            else:
                record.overall_average = 0.0
                record.standard_deviation = 0.0
                record.uncertainty_value = 0.0
                record.min_group_average = 0.0
                record.max_group_average = 0.0

    @api.model
    def create(self, vals):
        """إنشاء التقرير مع بيانات المجموعات"""
        record = super().create(vals)
        if record.sample_id:
            if record.sample_type == 'concrete':
                record._generate_group_data()
        return record

    def _generate_group_data(self):
        """إنشاء بيانات المجموعات مرة واحدة عند فتح التقرير"""
        self.ensure_one()
        

        if self.group_data_ids:
            self.group_data_ids.unlink()
        
        if self.sample_id:

            groups_28_day = self.sample_id.result_set_ids.filtered(
                lambda rs: (rs.template_id.code != 'CONCRETE_OVERALL_AVG' and 
                           rs.concrete_group_no and
                           rs.concrete_age_days == '28')
            ).sorted('concrete_group_no')
            
            for group_set in groups_28_day:

                group_vals = self._prepare_group_data(group_set)
                if group_vals:
                    group_vals['report_id'] = self.id

                    individual_results = group_vals.pop('individual_results', [])
                    

                    group_record = self.env['lab.sample.report.group.data'].create(group_vals)
                    

                    for result_data in individual_results:
                        result_data['group_data_id'] = group_record.id
                        self.env['lab.sample.individual.result'].create(result_data)

    def action_refresh_group_data(self):
        """إعادة تحميل بيانات المجموعات من العينة"""
        self.ensure_one()
        
        if self.sample_type == 'concrete':
            self._generate_group_data()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_preview_report(self):
        """معاينة التقرير في عرض HTML"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'appointment_products.lab_sample_comprehensive_report_template',
            'report_type': 'qweb-html',
            'data': {'ids': self.ids},
            'context': self.env.context,
        }

    def _prepare_group_data(self, result_set):
        """تحضير بيانات مجموعة واحدة"""
        data = {
            'report_id': self.id,
            'group_number': result_set.concrete_group_no,
            'lab_code': result_set.concrete_field_code or '',
            'field_code': result_set.concrete_field_serial or '',
            'age_days': '28',
            'cube_count': result_set.number_of_samples or 3,
            'casting_date': result_set.casting_date,
            'testing_date': result_set.testing_date,
            'testing_temperature': result_set.testing_temperature or 31.0,
        }
        

        comp_strengths = []
        individual_results = []
        temp_data = {}  
        

        for line in result_set.result_line_ids:
            code = line.criterion_id.code
            value = line.value_numeric
            
            if code == 'WEIGHT_CONCRETE':
                data['weight_kg'] = value
                temp_data['weight_kg'] = value
            elif code == 'DENSITY_CONCRETE':
                data['density'] = value
                temp_data['density'] = value
            elif code == 'LOAD_KN_CONCRETE':
                data['load_kn'] = value
                temp_data['load_kn'] = value
            elif code == 'AVG_COMP_STRENGTH_CONCRETE':
                data['average_strength'] = value
        

        cube_sequence = 1
        for line in result_set.result_line_ids:
            code = line.criterion_id.code
            value = line.value_numeric
            
            if code == 'COMP_STRENGTH_CONCRETE':
                comp_strengths.append(value)

                individual_results.append({
                    'cube_sequence': cube_sequence,
                    'cube_id': f'C{cube_sequence}',
                    'weight_kg': temp_data.get('weight_kg', 0),
                    'density': temp_data.get('density', 0),
                    'load_kn': temp_data.get('load_kn', 0),
                    'compressive_strength': value,
                })
                cube_sequence += 1
        

        if comp_strengths:
            data['group_average'] = sum(comp_strengths) / len(comp_strengths)
            data['min_strength'] = min(comp_strengths)
            data['max_strength'] = max(comp_strengths)
            data['sample_count'] = len(comp_strengths)
            

        data['individual_results'] = individual_results
        
        return data

    def action_generate_comprehensive_report(self):
        """إنشاء التقرير الشامل"""
        self.ensure_one()
        
        if not self.sample_id:
            raise UserError(_('يجب تحديد عينة لإنشاء التقرير'))
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'appointment_products.lab_sample_comprehensive_report_template',
            'report_type': 'qweb-pdf',
            'data': {'ids': self.ids},
            'context': self.env.context,
        }


    
    def get_sliding_group_summaries(self):
        """إنشاء ملخصات متتالية لكل 4 مجموعات"""
        self.ensure_one()
        

        all_groups = self.group_data_ids.sorted('group_number')
        sliding_summaries = []
        
        # إنشاء تجميعات متتالية
        for i in range(len(all_groups)):

            group_chunk = all_groups[i:i+4]
            
            if len(group_chunk) >= 4:  
                chunk_summary = {
                    'start_group': group_chunk[0].group_number,
                    'end_group': group_chunk[3].group_number,
                    'groups': group_chunk,
                    'chunk_average': sum(g.group_average for g in group_chunk if g.group_average) / len([g for g in group_chunk if g.group_average]),
                    'chunk_index': i + 1,
                    'total_samples': sum(g.sample_count for g in group_chunk if g.sample_count),
                }
                sliding_summaries.append(chunk_summary)
            

            if i + 4 >= len(all_groups):
                break
        
        return sliding_summaries


class LabSampleReportGroupData(models.TransientModel):
    """بيانات مجموعة واحدة في التقرير الشامل"""
    _name = 'lab.sample.report.group.data'
    _description = 'Lab Sample Report Group Data'
    _order = 'group_number'

    report_id = fields.Many2one('lab.sample.comprehensive.report', required=True, ondelete='cascade')
    

    group_number = fields.Integer(string='رقم المجموعة', required=True)
    group_name = fields.Char(string='اسم المجموعة')
    lab_code = fields.Char(string='الرمز المختبري')
    field_code = fields.Char(string='الرمز الحقلي')
    age_days = fields.Char(string='الأيام', default='28')
    cube_count = fields.Integer(string='عدد المكعبات', default=3)
    group_average = fields.Float(string='متوسط المجموعة', digits=(6, 3))
    min_strength = fields.Float(string='أقل قيمة', digits=(6, 3))
    max_strength = fields.Float(string='أعلى قيمة', digits=(6, 3))
    sample_count = fields.Integer(string='عدد العينات')
    

    casting_date = fields.Date(string='تاريخ الصب')
    testing_date = fields.Date(string='تاريخ الفحص')
    testing_temperature = fields.Float(string='درجة حرارة الفحص', default=31.0)

    weight_kg = fields.Float(string='الوزن (كغم)', digits=(5, 3))
    density = fields.Float(string='الكثافة (كغم/م³)', digits=(6, 1))
    load_kn = fields.Float(string='الحمل (kN)', digits=(6, 1))
    compressive_strength = fields.Float(string='قوة الضغط (N/mm²)', digits=(5, 2))
    average_strength = fields.Float(string='متوسط قوة الضغط (N/mm²)', digits=(5, 2))
    

    individual_result_ids = fields.One2many(
        'lab.sample.individual.result', 
        'group_data_id', 
        string='النتائج الفردية'
    )


class LabSampleIndividualResult(models.TransientModel):
    """نتيجة فردية لمكعب واحد في المجموعة"""
    _name = 'lab.sample.individual.result'
    _description = 'Lab Sample Individual Result'
    _order = 'cube_sequence'
    
    group_data_id = fields.Many2one(
        'lab.sample.report.group.data', 
        required=True, 
        ondelete='cascade'
    )
    

    cube_sequence = fields.Integer(string='ترتيب المكعب', required=True)
    cube_id = fields.Char(string='رقم المكعب')
    

    weight_kg = fields.Float(string='الوزن (كغم)', digits=(5, 3))
    density = fields.Float(string='الكثافة (كغم/م³)', digits=(6, 1))
    load_kn = fields.Float(string='الحمل (kN)', digits=(6, 1))
    compressive_strength = fields.Float(string='قوة الضغط (N/mm²)', digits=(5, 2))

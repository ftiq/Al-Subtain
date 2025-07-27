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
        ('concrete', 'خرسانة'),
        ('masonry', 'طابوق')
    ], string='نوع العينة', compute='_compute_sample_type', store=True)
    

    group_data_ids = fields.One2many(
        'lab.sample.report.group.data',
        'report_id',
        string='بيانات المجموعات'
    )
    

    brick_data_ids = fields.One2many(
        'lab.sample.brick.data',
        'report_id',
        string='بيانات الطابوق'
    )
    

    brick_compression_average = fields.Float(string='متوسط قوة الضغط (N/mm²)', compute='_compute_brick_statistics')
    brick_absorption_average = fields.Float(string='متوسط الامتصاص (%)', compute='_compute_brick_statistics')
    brick_samples_count = fields.Integer(string='عدد العينات', compute='_compute_brick_statistics')
    brick_subtype_name = fields.Char(string='نوع الطابوق', compute='_compute_brick_info')

    @api.depends('sample_id')
    def _compute_sample_type(self):
        """تحديد نوع العينة (خرسانة أو طابوق)"""
        for record in self:
            if record.sample_id and record.sample_id.product_id:
                product = record.sample_id.product_id
                if (product.product_tmpl_id.sample_type_id and 
                    product.product_tmpl_id.sample_type_id.code == 'MASONRY'):
                    record.sample_type = 'masonry'
                else:
                    record.sample_type = 'concrete'
            else:
                record.sample_type = 'concrete'

    @api.depends('sample_id', 'sample_type')
    def _compute_brick_info(self):
        """حساب معلومات الطابوق"""
        for record in self:
            if record.sample_id and record.sample_type == 'masonry':
                if record.sample_id.sample_subtype_id:
                    record.brick_subtype_name = record.sample_id.sample_subtype_id.name
                else:
                    record.brick_subtype_name = 'غير محدد'
            else:
                record.brick_subtype_name = ''

    @api.depends('sample_id', 'sample_type', 'brick_data_ids')
    def _compute_brick_statistics(self):
        """حساب إحصائيات الطابوق"""
        for record in self:
            if record.sample_id and record.sample_type == 'masonry':

                compression_data = record.brick_data_ids.filtered(lambda x: x.test_type == 'compression' and x.compressive_strength > 0)
                if compression_data:
                    record.brick_compression_average = sum(compression_data.mapped('compressive_strength')) / len(compression_data)
                else:
                    record.brick_compression_average = 0
                

                absorption_data = record.brick_data_ids.filtered(lambda x: x.test_type == 'absorption' and x.absorption_rate > 0)
                if absorption_data:
                    record.brick_absorption_average = sum(absorption_data.mapped('absorption_rate')) / len(absorption_data)
                else:
                    record.brick_absorption_average = 0
                

                record.brick_samples_count = len(record.brick_data_ids)
            else:
                record.brick_compression_average = 0
                record.brick_absorption_average = 0
                record.brick_samples_count = 0

    @api.depends('sample_id', 'sample_id.lab_test_template_id', 'sample_id.sample_subtype_id', 'sample_type')
    def _compute_descriptive_title(self):
        """حساب العنوان الوصفي للتقرير"""
        for record in self:
            if record.sample_id:
                if record.sample_type == 'masonry':
                    record.descriptive_title = 'تقرير فحص طابوق (طبعي)'
                else:

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

                        answer_value = first_answer.value_text_box or (first_answer.value_answer_id.value if first_answer.value_answer_id else '')
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
        """إنشاء التقرير مع بيانات المجموعات أو الطابوق"""
        record = super().create(vals)
        if record.sample_id:
            if record.sample_type == 'concrete':
                record._generate_group_data()
            elif record.sample_type == 'masonry':
                record._generate_brick_data()
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

    def _generate_brick_data(self):
        """إنشاء بيانات الطابوق مرة واحدة عند فتح التقرير"""
        _logger.info(f"=== _generate_brick_data START for sample {self.sample_id.name}, type: {self.sample_type} ===")
        
        if self.sample_type != 'masonry':
            _logger.info("Sample type is not masonry, skipping brick data generation")
            return
            
        _logger.info(f"Found {len(self.sample_id.result_set_ids)} result sets for sample")
        self.ensure_one()
        

        if self.brick_data_ids:
            self.brick_data_ids.unlink()
        
        if self.sample_id:
            result_sets = self.sample_id.result_set_ids
            _logger.info(f"Processing {len(result_sets)} result sets")
            

            dimensions_data = {}
            compression_samples = []
            absorption_samples = []
            efflorescence_samples = []
            
            for result_set in result_sets:
                template_code = ''
                if result_set.template_id and hasattr(result_set.template_id, 'code'):
                    template_code = result_set.template_id.code or ''
                _logger.info(f"Processing result set {result_set.id} with template code: '{template_code}'")
                _logger.info(f"Result set has {len(result_set.result_line_ids)} lines")
                
                if template_code == 'BRICK_DIMENS_B':

                    _logger.info(f"Processing BRICK_DIMENS_B with {len(result_set.result_line_ids)} lines")
                    for line in result_set.result_line_ids:
                        if not line.criterion_id:
                            _logger.info(f"Line {line.id} has no criterion_id, skipping")
                            continue
                        criterion_code = line.criterion_id.code or ''
                        value = line.value_numeric or 0
                        _logger.info(f"Line {line.id}: criterion_code='{criterion_code}', value={value}, sample_no={line.sample_no}")
                        
                        if criterion_code == 'LENGTH_B':
                            dimensions_data['length_mm'] = line.value_numeric or 0
                            _logger.info(f"Set length_mm = {dimensions_data['length_mm']}")
                        elif criterion_code == 'WIDTH_B':
                            dimensions_data['width_mm'] = line.value_numeric or 0
                            _logger.info(f"Set width_mm = {dimensions_data['width_mm']}")
                        elif criterion_code == 'HEIGHT_B':
                            dimensions_data['height_mm'] = line.value_numeric or 0
                            _logger.info(f"Set height_mm = {dimensions_data['height_mm']}")
                        elif criterion_code == 'HOLE_DIA_B':
                            dimensions_data['hole_diameter_mm'] = line.value_numeric or 0
                            _logger.info(f"Set hole_diameter_mm = {dimensions_data['hole_diameter_mm']}")
                        elif criterion_code == 'HOLE_COUNT':
                            dimensions_data['hole_count'] = int(value)
                            _logger.info(f"Set hole_count = {int(value)}")
                        elif criterion_code == 'HOLE_RATIO':
                            dimensions_data['holes_percentage'] = value
                            _logger.info(f"Set holes_percentage = {value}")
            
                elif template_code == 'BRICK_COMP_B':

                    _logger.info(f"Processing BRICK_COMP_B with {len(result_set.result_line_ids)} lines")
                    

                    samples_by_no = {}
                    for line in result_set.result_line_ids:
                        if not line.criterion_id:
                            _logger.info(f"Line {line.id} has no criterion_id, skipping")
                            continue
                        
                        sample_no = line.sample_no or 1
                        criterion_code = line.criterion_id.code or ''
                        value = line.value_numeric or 0
                        _logger.info(f"Line {line.id}: criterion_code='{criterion_code}', value={value}, sample_no={sample_no}")
                        
                        if sample_no not in samples_by_no:
                            samples_by_no[sample_no] = {'test_type': 'compression'}
                        
                        if criterion_code == 'LOAD_KN_B':
                            samples_by_no[sample_no]['load_kn'] = value
                            _logger.info(f"Set load_kn = {value} for sample {sample_no}")
                        elif criterion_code == 'COMP_STRENGTH_B':
                            samples_by_no[sample_no]['compressive_strength'] = value
                            _logger.info(f"Set compressive_strength = {value} for sample {sample_no}")
                        elif criterion_code == 'AREA_COMP_B':
                            samples_by_no[sample_no]['area_mm2'] = value
                            _logger.info(f"Set area_mm2 = {value} for sample {sample_no}")
                    

                    for sample_no, sample_data in samples_by_no.items():
                        if any(key in sample_data for key in ['load_kn', 'compressive_strength', 'area_mm2']):
                            compression_samples.append(sample_data)
                            _logger.info(f"Added compression sample {sample_no}: {sample_data}")
                    
                    _logger.info(f"Total compression samples found: {len(compression_samples)}")
                
                elif template_code == 'BRICK_ABSORB_B':

                    _logger.info(f"Processing BRICK_ABSORB_B with {len(result_set.result_line_ids)} lines")
                    

                    samples_by_no = {}
                    for line in result_set.result_line_ids:
                        if not line.criterion_id:
                            _logger.info(f"Line {line.id} has no criterion_id, skipping")
                            continue
                        
                        sample_no = line.sample_no or 1
                        criterion_code = line.criterion_id.code or ''
                        value = line.value_numeric or 0
                        _logger.info(f"Line {line.id}: criterion_code='{criterion_code}', value={value}, sample_no={sample_no}")
                        
                        if sample_no not in samples_by_no:
                            samples_by_no[sample_no] = {'test_type': 'absorption'}
                        
                        if criterion_code == 'DRY_WT_B':
                            samples_by_no[sample_no]['dry_weight_gm'] = value
                            _logger.info(f"Set dry_weight_gm = {value} for sample {sample_no}")
                        elif criterion_code == 'WET_WT_B':
                            samples_by_no[sample_no]['wet_weight_gm'] = value
                            _logger.info(f"Set wet_weight_gm = {value} for sample {sample_no}")
                        elif criterion_code == 'ABSORB_PCT_B':
                            samples_by_no[sample_no]['absorption_rate'] = value
                            _logger.info(f"Set absorption_rate = {value} for sample {sample_no}")
                    

                    for sample_no, sample_data in samples_by_no.items():
                        if any(key in sample_data for key in ['dry_weight_gm', 'wet_weight_gm', 'absorption_rate']):
                            absorption_samples.append(sample_data)
                            _logger.info(f"Added absorption sample {sample_no}: {sample_data}")
                    
                    _logger.info(f"Total absorption samples found: {len(absorption_samples)}")
                
                elif template_code == 'BRICK_EFFLOR_B':

                    _logger.info(f"Processing BRICK_EFFLOR_B with {len(result_set.result_line_ids)} lines")
                    

                    samples_by_no = {}
                    for line in result_set.result_line_ids:
                        if not line.criterion_id:
                            _logger.info(f"Line {line.id} has no criterion_id, skipping")
                            continue
                        
                        sample_no = line.sample_no or 1
                        criterion_code = line.criterion_id.code or ''
                        value_text = line.value_text or ''
                        _logger.info(f"Line {line.id}: criterion_code='{criterion_code}', value_text='{value_text}', sample_no={sample_no}")
                        
                        if sample_no not in samples_by_no:
                            samples_by_no[sample_no] = {'test_type': 'efflorescence'}
                        
                        if criterion_code == 'EFFLOR_GRADE_B':
                            samples_by_no[sample_no]['efflorescence_degree'] = value_text
                            _logger.info(f"Set efflorescence_degree = '{value_text}' for sample {sample_no}")
                    

                    for sample_no, sample_data in samples_by_no.items():
                        if 'efflorescence_degree' in sample_data:
                            efflorescence_samples.append(sample_data)
                            _logger.info(f"Added efflorescence sample {sample_no}: {sample_data}")
                    
                    _logger.info(f"Total efflorescence samples found: {len(efflorescence_samples)}")
            

            if dimensions_data:
                dimensions_data.update({
                    'report_id': self.id,
                    'test_type': 'dimensions',
                    'sequence': 1,
                    'sample_number': 1
                })
                created_dimensions = self.env['lab.sample.brick.data'].create(dimensions_data)
                _logger.info(f"Created dimensions record: {created_dimensions.id} with data: {dimensions_data}")
            else:
                _logger.info("No dimensions data to create")
            

            _logger.info(f"Creating {len(compression_samples)} compression records")
            for i, sample_data in enumerate(compression_samples, 1):
                sample_data.update({
                    'report_id': self.id,
                    'sequence': 10 + i,
                    'sample_number': i
                })
                created_compression = self.env['lab.sample.brick.data'].create(sample_data)
                _logger.info(f"Created compression record {i}: {created_compression.id}")
            

            _logger.info(f"Creating {len(absorption_samples)} absorption records")
            for i, sample_data in enumerate(absorption_samples, 1):
                sample_data.update({
                    'report_id': self.id,
                    'sequence': 20 + i,
                    'sample_number': i
                })
                created_absorption = self.env['lab.sample.brick.data'].create(sample_data)
                _logger.info(f"Created absorption record {i}: {created_absorption.id}")
            

            _logger.info(f"Creating {len(efflorescence_samples)} efflorescence records")
            for i, sample_data in enumerate(efflorescence_samples, 1):
                sample_data.update({
                    'report_id': self.id,
                    'sequence': 30 + i,
                    'sample_number': i
                })
                created_efflorescence = self.env['lab.sample.brick.data'].create(sample_data)
                _logger.info(f"Created efflorescence record {i}: {created_efflorescence.id}")
            
            _logger.info(f"Brick data generation completed:")
            _logger.info(f"  - Dimensions data: {1 if dimensions_data else 0} records")
            _logger.info(f"  - Compression samples: {len(compression_samples)} records")
            _logger.info(f"  - Absorption samples: {len(absorption_samples)} records")
            _logger.info(f"  - Efflorescence samples: {len(efflorescence_samples)} records")
            _logger.info(f"=== _generate_brick_data END ===")

    def action_refresh_group_data(self):
        """إعادة تحميل بيانات المجموعات من العينة"""
        self.ensure_one()
        
        if self.sample_type == 'concrete':
            self._generate_group_data()
        elif self.sample_type == 'masonry':
            self._generate_brick_data()
        
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

    def action_preview_report(self):
        """معاينة التقرير في المتصفح"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'appointment_products.lab_sample_comprehensive_report_template',
            'report_type': 'qweb-html',
            'data': {'ids': self.ids},
            'context': self.env.context,
        }
    
    def action_print_brick_report(self):
        """طباعة تقرير الطابوق"""
        self.ensure_one()
        
        if self.sample_type != 'masonry':
            raise UserError('هذا التقرير مخصص لعينات الطابوق فقط')
        
        return {
            'type': 'ir.actions.report',
            'report_name': 'appointment_products.brick_comprehensive_report_template',
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

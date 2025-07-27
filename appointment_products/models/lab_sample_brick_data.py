# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class LabSampleBrickData(models.TransientModel):
    """بيانات الطابوق في التقرير الشامل"""
    _name = 'lab.sample.brick.data'
    _description = 'Lab Sample Brick Data'
    _order = 'sequence'

    report_id = fields.Many2one('lab.sample.comprehensive.report', required=True, ondelete='cascade')
    sequence = fields.Integer(string='الترتيب', default=1)
    
    length_mm = fields.Float(string='الطول (mm)', digits=(5, 1))
    width_mm = fields.Float(string='العرض (mm)', digits=(5, 1))
    height_mm = fields.Float(string='الارتفاع (mm)', digits=(5, 1))
    area_mm2 = fields.Float(string='المساحة (mm²)', digits=(10, 1))
    hole_diameter_mm = fields.Float(string='قطر الفتحة (mm)', digits=(5, 1))
    hole_count = fields.Integer(string='عدد الفتحات')
    holes_percentage = fields.Float(string='نسبة الفتحات (%)', digits=(5, 2))
    

    load_kn = fields.Float(string='الحمولة (KN)', digits=(6, 1))
    compressive_strength = fields.Float(string='قوة الضغط (N/mm²)', digits=(5, 2))
    

    dry_weight_gm = fields.Float(string='الوزن الجاف (gm)', digits=(6, 1))
    wet_weight_gm = fields.Float(string='الوزن المبلل (gm)', digits=(6, 1))
    absorption_rate = fields.Float(string='نسبة الامتصاص (%)', digits=(5, 2))
    

    efflorescence_degree = fields.Integer(string='درجة التزهر', default=1)
    

    test_type = fields.Selection([
        ('dimensions', 'القياسات'),
        ('compression', 'الانضغاط'),
        ('absorption', 'الامتصاص'),
        ('efflorescence', 'التزهر')
    ], string='نوع الفحص')
    
    sample_number = fields.Integer(string='رقم العينة')
    notes = fields.Text(string='ملاحظات')
    
    @api.depends('length_mm', 'width_mm')
    def _compute_area(self):
        """حساب المساحة تلقائياً"""
        for record in self:
            if record.length_mm and record.width_mm:
                record.area_mm2 = record.length_mm * record.width_mm
            else:
                record.area_mm2 = 0
    
    @api.depends('hole_diameter_mm', 'hole_count', 'area_mm2')
    def _compute_holes_percentage(self):
        """حساب نسبة الفتحات تلقائياً"""
        for record in self:
            if record.hole_diameter_mm and record.hole_count and record.area_mm2:
                hole_area = 3.14159 * (record.hole_diameter_mm / 2) ** 2 * record.hole_count
                record.holes_percentage = (hole_area / record.area_mm2) * 100
            else:
                record.holes_percentage = 0
    
    @api.depends('dry_weight_gm', 'wet_weight_gm')
    def _compute_absorption_rate(self):
        """حساب نسبة الامتصاص تلقائياً"""
        for record in self:
            if record.dry_weight_gm and record.wet_weight_gm:
                record.absorption_rate = ((record.wet_weight_gm - record.dry_weight_gm) / record.dry_weight_gm) * 100
            else:
                record.absorption_rate = 0
    
    @api.depends('load_kn', 'area_mm2')
    def _compute_compressive_strength(self):
        """حساب قوة الضغط تلقائياً"""
        for record in self:
            if record.load_kn and record.area_mm2:
                record.compressive_strength = (record.load_kn * 1000) / record.area_mm2
            else:
                record.compressive_strength = 0

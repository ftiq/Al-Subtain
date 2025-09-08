# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import math


class LabSampleRule(models.Model):
    """قواعد أخذ العينات للخرسانة حسب النوع والكمية"""
    _name = 'lab.sample.rule'
    _description = 'Lab Sample Rule'
    _order = 'sample_type_id, sequence'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    _check_company_auto = True

    name = fields.Char(string='اسم القاعدة', required=True)
    
    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع العينة',
        required=True,
        ondelete='cascade',
        help='نوع العينة التي تطبق عليها هذه القاعدة'
    )
    
    base_quantity = fields.Float(
        string='الكمية الأساسية (م³)',
        required=True,
        default=80.0,
        help='الكمية الأساسية بالمتر المكعب التي تستلزم أخذ المجموعة الأولى من العينات'
    )
    
    base_groups = fields.Integer(
        string='عدد المجموعات الأساسية',
        required=True,
        default=4,
        help='عدد المجموعات في الشريحة الأولى'
    )
    
    repeat_step_qty = fields.Float(
        string='كمية التكرار (م³)',
        required=True,
        default=50.0,
        help='كل هذه الكمية يتم أخذ مجموعة إضافية'
    )
    
    repeat_groups = fields.Integer(
        string='مجموعات التكرار',
        required=True,
        default=1,
        help='عدد المجموعات الإضافية لكل تكرار'
    )
    
    cubes_per_group = fields.Integer(
        string='مكعبات لكل مجموعة',
        required=True,
        default=3,
        help='عدد المكعبات الأساسية في كل مجموعة'
    )
    
    extra_cubes_per_group = fields.Integer(
        string='مكعبات إضافية لكل مجموعة',
        required=True,
        default=2,
        help='عدد المكعبات الإضافية (7 أيام + احتياطي)'
    )
    

    
    max_small_quantity = fields.Float(
        string='حد الكمية الصغيرة (م³)',
        default=200.0,
        help='إذا كانت الكمية أقل من أو تساوي هذا الحد، تطبق القاعدة الأساسية فقط'
    )
    
    sequence = fields.Integer(string='التسلسل', default=10)
    active = fields.Boolean(string='نشط', default=True)
    description = fields.Text(string='الوصف')
    
    test_ages = fields.Char(
        string='أعمار الاختبار (أيام)',
        default='7',
        help='قائمة مفصولة بفواصل لأعمار اختبار المكعبات الإضافية (تجنب 28 لضمان عدم تجاوز 3 مكعبات لـ28 يوم)'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )

    _sql_constraints = [
        ('positive_base_quantity', 'CHECK(base_quantity > 0)', 'الكمية الأساسية يجب أن تكون أكبر من الصفر'),
        ('positive_base_groups', 'CHECK(base_groups > 0)', 'عدد المجموعات الأساسية يجب أن يكون أكبر من الصفر'),
        ('positive_repeat_step', 'CHECK(repeat_step_qty > 0)', 'كمية التكرار يجب أن تكون أكبر من الصفر'),
        ('positive_repeat_groups', 'CHECK(repeat_groups >= 0)', 'مجموعات التكرار يجب أن تكون أكبر من أو تساوي الصفر'),
        ('positive_cubes_per_group', 'CHECK(cubes_per_group > 0)', 'عدد المكعبات لكل مجموعة يجب أن يكون أكبر من الصفر'),

        ('unique_sample_type_company', 'UNIQUE(sample_type_id, company_id)', 'يمكن وجود قاعدة واحدة فقط لكل نوع عينة في الشركة'),
    ]

    @api.constrains('base_quantity', 'repeat_step_qty', 'max_small_quantity')
    def _check_quantities(self):
        """التحقق من صحة الكميات"""
        for rule in self:
            if rule.base_quantity <= 0:
                raise ValidationError(_('الكمية الأساسية يجب أن تكون أكبر من الصفر'))
            if rule.repeat_step_qty <= 0:
                raise ValidationError(_('كمية التكرار يجب أن تكون أكبر من الصفر'))
            if rule.max_small_quantity and rule.max_small_quantity < rule.base_quantity:
                raise ValidationError(_('حد الكمية الصغيرة يجب أن يكون أكبر من أو يساوي الكمية الأساسية'))

    @api.constrains('test_ages')
    def _check_test_ages(self):
        """التحقق من صحة أعمار الاختبار"""
        for rule in self:
            if rule.test_ages:
                try:
                    ages = [int(age.strip()) for age in rule.test_ages.split(',') if age.strip()]
                    if not ages:
                        raise ValidationError(_('يجب تحديد عمر واحد على الأقل للاختبار'))
                    if any(age <= 0 for age in ages):
                        raise ValidationError(_('جميع أعمار الاختبار يجب أن تكون أكبر من الصفر'))
                except ValueError:
                    raise ValidationError(_('أعمار الاختبار يجب أن تكون أرقام صحيحة مفصولة بفواصل'))

    def compute_sampling(self, planned_quantity):
        """
        حساب عدد المجموعات والمكعبات المطلوبة حسب الكمية المخططة
        
        Args:
            planned_quantity (float): الكمية المخططة بالمتر المكعب
            
        Returns:
            dict: معلومات العينات المحسوبة
        """
        self.ensure_one()
        
        if planned_quantity <= 0:
            raise UserError(_('الكمية المخططة يجب أن تكون أكبر من الصفر'))
        
        if planned_quantity <= self.max_small_quantity:
            total_groups = self.base_groups
        else:
            total_groups = self.base_groups
            
            extra_quantity = planned_quantity - self.base_quantity
            if extra_quantity > 0:
                repeat_cycles = math.ceil(extra_quantity / self.repeat_step_qty)
                total_groups += repeat_cycles * self.repeat_groups
        

        core_cubes = total_groups * self.cubes_per_group
        extra_cubes = total_groups * self.extra_cubes_per_group
        
        test_ages = []
        if self.test_ages:
            test_ages = [int(age.strip()) for age in self.test_ages.split(',') if age.strip()]
        
        twenty_eight_cubes = core_cubes
        
        additional_ages = []
        for extra_idx in range(1, self.extra_cubes_per_group + 1):
            if extra_idx <= len(test_ages):
                age = test_ages[extra_idx - 1]
                if age != 28:
                    additional_ages.append(age)
                else:
                    additional_ages.append(7)
            else:
                additional_ages.append(7)
        
        seven_day_cubes = total_groups * additional_ages.count(7)
        
        total_cubes = core_cubes + extra_cubes
        
        test_ages = []
        if self.test_ages:
            test_ages = [int(age.strip()) for age in self.test_ages.split(',') if age.strip()]
        
        return {
            'planned_quantity': planned_quantity,
            'total_groups': total_groups,
            'core_cubes': core_cubes,
            'extra_cubes': extra_cubes,
            'total_cubes': total_cubes,
            'twenty_eight_cubes': twenty_eight_cubes,
            'seven_day_cubes': seven_day_cubes,
            'test_ages': test_ages,
            'rule_applied': {
                'base_quantity': self.base_quantity,
                'base_groups': self.base_groups,
                'repeat_step_qty': self.repeat_step_qty,
                'repeat_groups': self.repeat_groups,
                'is_small_quantity': planned_quantity <= self.max_small_quantity,
            }
        }
    

    
    def action_test_calculation(self):
        """اختبار حساب العينات بكمية تجريبية"""
        self.ensure_one()
        
        test_quantities = [50, 80, 150, 200, 300, 500]
        results = []
        
        for qty in test_quantities:
            try:
                result = self.compute_sampling(qty)
                results.append({
                    'quantity': qty,
                    'groups': result['total_groups'],
                    'cubes': result['total_cubes'],
                    'is_small': result['rule_applied']['is_small_quantity']
                })
            except Exception as e:
                results.append({
                    'quantity': qty,
                    'error': str(e)
                })
        
        message_lines = ['نتائج اختبار حساب العينات:']
        summary_stats = {'total_tests': len(results), 'successful': 0, 'failed': 0}
        
        for result in results:
            if 'error' in result:
                message_lines.append(f"{result['quantity']} م³: خطأ - {result['error']}")
                summary_stats['failed'] += 1
            else:
                small_indicator = '🔹' if result['is_small'] else '🔸'
                status_text = 'كمية صغيرة' if result['is_small'] else 'كمية كبيرة'
                
                cube_details = []
                result_obj = self.compute_sampling(result['quantity'])
                if result_obj['twenty_eight_cubes'] > 0:
                    cube_details.append(f"{result_obj['twenty_eight_cubes']} مكعب (28 يوم)")
                if result_obj['seven_day_cubes'] > 0:
                    cube_details.append(f"{result_obj['seven_day_cubes']} مكعب (7 أيام)")
                
                cube_text = " + ".join(cube_details) if cube_details else f"{result['cubes']} مكعب"
                
                message_lines.append(
                    f"{small_indicator} {result['quantity']} م³ ({status_text}): "
                    f"{result['groups']} مجموعة، {cube_text}"
                )
                summary_stats['successful'] += 1
        
        message_lines.append('')
        message_lines.append(f" الملخص: {summary_stats['successful']} نجح، {summary_stats['failed']} فشل")
        message_lines.append('')
        message_lines.append(" ملاحظة: الأرقام تُظهر مكعبات 28 يوم المعروضة في الواجهة. مكعبات 7 أيام تُظهر عند التفعيل.")
        
        notification_type = 'success' if summary_stats['failed'] == 0 else 'warning'
        title = _(' نتائج اختبار الحساب') if summary_stats['failed'] == 0 else _('⚠️ نتائج اختبار الحساب (مع أخطاء)')
        
        self.message_post(body='<br/>'.join(message_lines))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': '\n'.join(message_lines),
                'type': notification_type,
                'sticky': True,
            }
        } 
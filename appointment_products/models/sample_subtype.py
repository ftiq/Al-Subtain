# -*- coding: utf-8 -*-
from odoo import fields, models, api, _, SUPERUSER_ID
from odoo.exceptions import UserError


class LabSampleSubtype(models.Model):
    """نموذج يمثل النوع الفرعي للعينة (مثلاً: خرسانة جاهزة، خرسانة سابقة الصب...)."""
    _name = 'lab.sample.subtype'
    _description = 'نوع فرعي للعينة'
    _order = 'sequence, name'

    _check_company_auto = True

    name = fields.Char(string='الاسم', required=True, translate=True)
    code = fields.Char(string='الرمز', required=True, index=True)
    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع العينة',
        required=True,
        ondelete='cascade',
    )
    description = fields.Text(string='الوصف')
    sequence = fields.Integer(string='التسلسل', default=10)
    active = fields.Boolean(string='نشط', default=True)
    

    efflorescence_levels = fields.Many2many(
        'lab.efflorescence.level',
        string='درجات التزهر المسموحة',
        help='درجات التزهر المسموحة لهذا النوع الفرعي من العينة'
    )

    efflorescence_level = fields.Selection([
        ('none', 'لا يوجد'),
        ('light', 'خفيف'),
        ('medium', 'متوسط'),
        ('high', 'عالي'),
    ], string='درجة التزهر المسموحة', default='none',
       help='درجة التزهر المسموحة لهذا النوع الفرعي من العينة - استخدم "قيم التزهر المسموحة" بدلاً من ذلك')

    allowed_efflorescence_values = fields.Char(
        string='قيم التزهر المسموحة',
        help='قيم رقمية مفصولة بفواصل (مثال: 1,2 للسماح بـ "لا يوجد" و "خفيف")',
        default='1'
    )

    hole_count = fields.Integer(
        string='عدد الفتحات',
        default=0,
        help='عدد الفتحات في هذا النوع الفرعي للطابوق/العينة'
    )

    company_id = fields.Many2one(
        'res.company',
        string='الشركة',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('unique_code_per_type', 'unique(code, sample_type_id)',
         'رمز النوع الفرعي يجب أن يكون فريداً ضمن نوع العينة!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.uid != SUPERUSER_ID:
            raise UserError(_('لا يمكن إنشاء أنواع فرعية جديدة – هذه السجلات ثابتة في النظام.'))

        # إزالة القيد الذي يمنع إنشاء أنواع فرعية غير الطابوق
        # نسمح الآن بإنشاء أنواع فرعية لجميع أنواع العينات
        
        return super().create(vals_list)

    def write(self, vals):
        masonry_type = self.env.ref('appointment_products.masonry_type', raise_if_not_found=False)

        if self.env.uid != SUPERUSER_ID:
            allowed_keys = {'hole_count', 'allowed_efflorescence_values', 'efflorescence_levels', 'efflorescence_level'}
            if set(vals.keys()) - allowed_keys:
                raise UserError(_('يُسمح بتعديل حقول "عدد الفتحات" و "قيم التزهر المسموحة" فقط.'))
            # السماح بتعديل الحقول المسموحة لجميع أنواع العينات

        # إزالة القيد على نوع العينة - السماح بجميع أنواع العينات

        return super().write(vals)

    def unlink(self):
        if self.env.uid != SUPERUSER_ID:
            raise UserError(_('لا يمكن حذف الأنواع الفرعية – هذه السجلات ثابتة في النظام.'))
        return super().unlink() 

    def get_allowed_efflorescence_values_list(self):
        """إرجاع قائمة بالقيم الرقمية المسموحة لدرجة التزهر"""
        self.ensure_one()
        
        if self.allowed_efflorescence_values:
            try:

                values = [int(v.strip()) for v in self.allowed_efflorescence_values.split(',') if v.strip()]
                return values
            except ValueError:
                return [1]
        
        old_value_map = {
            'none': 1,
            'light': 2,
            'medium': 3,
            'high': 4
        }
        return [old_value_map.get(self.efflorescence_level, 1)]

    def is_efflorescence_value_allowed(self, efflorescence_value):
        """فحص ما إذا كانت درجة التزهر المعطاة مسموحة لهذا النوع الفرعي"""
        self.ensure_one()
        allowed_values = self.get_allowed_efflorescence_values_list()
        return efflorescence_value in allowed_values

    @api.model
    def get_efflorescence_display_name(self, numeric_value):
        """إرجاع النص المقابل لدرجة التزهر الرقمية"""
        value_map = {
            1: _("لا يوجد"),
            2: _("خفيف"),
            3: _("متوسط"),
            4: _("عالي"),
        }
        return value_map.get(numeric_value, str(numeric_value)) 

    @api.model
    def update_existing_efflorescence_values(self):
        """تحديث السجلات الموجودة لتستخدم حقل القيم المتعددة الجديد"""
        
        default_mappings = {
            'A': '1,2',    
            'B': '1,2,3',  
            'C': '1',      
        }
        
        subtypes = self.search([('sample_type_id.code', '=', 'MASONRY')])
        updated_count = 0
        
        for subtype in subtypes:
            if subtype.code in default_mappings:
                new_value = default_mappings[subtype.code]
                if subtype.allowed_efflorescence_values != new_value:
                    subtype.sudo().write({
                        'allowed_efflorescence_values': new_value
                    })
                    updated_count += 1
                    
                    self.env['mail.message'].create({
                        'model': 'lab.sample.subtype',
                        'res_id': subtype.id,
                        'message_type': 'notification',
                        'body': f'تم تحديث قيم التزهر المسموحة إلى: {new_value}',
                        'author_id': self.env.user.partner_id.id,
                    })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تحديث قيم التزهر'),
                'message': f'تم تحديث {updated_count} نوع فرعي بنجاح',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_efflorescence_logic(self):
        """اختبار منطق التزهر الجديد"""
        self.ensure_one()
        
        allowed_values = self.get_allowed_efflorescence_values_list()
        test_results = []
        
        for test_value in [1, 2, 3, 4]:
            is_allowed = self.is_efflorescence_value_allowed(test_value)
            display_name = self.get_efflorescence_display_name(test_value)
            test_results.append(f"{test_value} ({display_name}): {'✅ مسموح' if is_allowed else '❌ غير مسموح'}")
        
        message = f"""
🔬 اختبار منطق التزهر لـ {self.name}:

📋 القيم المسموحة: {allowed_values}

🧪 نتائج الاختبار:
{chr(10).join(test_results)}
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'اختبار منطق التزهر - {self.name}',
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        } 
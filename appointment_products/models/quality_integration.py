# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QualityPointLabIntegration(models.Model):
    """التكامل مع نقاط الجودة للفحوصات المختبرية"""
    _inherit = 'quality.point'

    lab_test_template_id = fields.Many2one(
        'lab.test.template', 
        string='قالب الفحص المختبري',
        help='ربط نقطة الجودة بقالب الفحص المختبري'
    )
    is_lab_test = fields.Boolean(string='فحص مختبري', default=False)
    auto_create_lab_sample = fields.Boolean(
        string='إنشاء عينة مختبرية تلقائياً', 
        default=True,
        help='إنشاء عينة مختبرية تلقائياً عند إنشاء فحص الجودة'
    )

    @api.model
    def create_lab_quality_point(self, product_id, picking_type_id, lab_test_template_id):
        """إنشاء نقطة جودة للفحص المختبري"""
        product = self.env['product.product'].browse(product_id)
        template = self.env['lab.test.template'].browse(lab_test_template_id)
        
        vals = {
            'name': f"فحص مختبري - {template.name} - {product.name}",
            'title': f"فحص {template.name}",
            'product_ids': [(6, 0, [product_id])],
            'picking_type_ids': [(6, 0, [picking_type_id])],
            'test_type_id': self.env.ref('quality.test_type_instructions').id,
            'lab_test_template_id': lab_test_template_id,
            'is_lab_test': True,
            'auto_create_lab_sample': True,
            'team_id': self._get_lab_quality_team(),
            'note': f"<p>فحص مختبري تلقائي لـ {template.name}</p>",
        }
        
        return self.sudo().create(vals)

    def _get_lab_quality_team(self):
        """الحصول على فريق الجودة للمختبر"""
        lab_team = self.env['quality.alert.team'].search([
            ('name', 'ilike', 'مختبر')
        ], limit=1)
        
        if not lab_team:

            lab_team = self.env['quality.alert.team'].sudo().create({
                'name': 'فريق المختبر',
                'sequence': 10,
                'company_id': self.env.company.id,
            })
        
        return lab_team.id


class QualityCheckLabIntegration(models.Model):
    """تكامل فحوصات الجودة مع النظام المختبري"""
    _inherit = 'quality.check'

    lab_sample_id = fields.Many2one(
        'lab.sample', 
        string='العينة المختبرية',
        help='العينة المختبرية المرتبطة بهذا الفحص'
    )
    lab_result_set_ids = fields.One2many(
        'lab.result.set', 
        'quality_check_id', 
        string='مجموعات النتائج المختبرية'
    )
    lab_test_status = fields.Selection([
        ('pending', 'في الانتظار'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'مكتمل'),
        ('failed', 'فاشل')
    ], string='حالة الفحص المختبري', default='pending')

    @api.model
    def create(self, vals):
        """إنشاء عينة مختبرية تلقائياً عند إنشاء فحص جودة"""
        check = super().create(vals)
        
        if check.point_id and check.point_id.is_lab_test and check.point_id.auto_create_lab_sample:
            check._create_lab_sample()
        
        return check

    def _create_lab_sample(self):
        """إنشاء عينة مختبرية من فحص الجودة"""
        for check in self:
            if not check.lab_sample_id and check.point_id.lab_test_template_id:
                task = self.env['project.task'].search([
                    ('stock_receipt_id', '=', check.picking_id.id)
                ], limit=1)
                
                sample_vals = {
                    'product_id': check.product_id.id,
                    'task_id': task.id if task else False,
                    'state': 'received',
                    'lab_test_template_id': check.point_id.lab_test_template_id.id,
                    'quality_check_id': check.id,
                    'quantity': 1,
                    'notes': f'تم إنشاؤها تلقائياً من الانتقاء {check.picking_id.name}',
                }
                
                lab_sample = self.env['lab.sample'].sudo().create(sample_vals)
                check.lab_sample_id = lab_sample.id
                check.lab_test_status = 'pending'

    def action_start_lab_test(self):
        """بدء الفحص المختبري"""
        for check in self:
            if check.lab_sample_id:
                check.lab_sample_id.state = 'testing'
                check.lab_test_status = 'in_progress'
                
                if check.point_id.lab_test_template_id:
                    result_set = self.env['lab.result.set'].sudo().create({
                        'name': f"نتائج {check.name}",
                        'sample_id': check.lab_sample_id.id,
                        'template_id': check.point_id.lab_test_template_id.id,
                        'quality_check_id': check.id,
                        'state': 'draft'
                    })

    def action_complete_lab_test(self):
        """إنهاء الفحص المختبري"""
        for check in self:
            if check.lab_sample_id:
                check.lab_sample_id.with_context(skip_quality_update=True).write({'state': 'completed'})
                check.lab_test_status = 'completed'
                
                all_passed = all(
                    result_set.overall_conformity == 'pass' 
                    for result_set in check.lab_result_set_ids
                )
                
                if all_passed:
                    check.do_pass()
                else:
                    check.do_fail()
                    self._create_quality_alert(check)

    def _create_quality_alert(self, check):
        """إنشاء تنبيه جودة عند فشل الفحص"""
        alert_vals = {
            'name': f"فشل فحص مختبري - {check.name}",
            'description': f"فشل في الفحص المختبري لـ {check.product_id.name}",
            'check_id': check.id,
            'product_tmpl_id': check.product_id.product_tmpl_id.id,
            'product_id': check.product_id.id,
            'lot_id': check.lot_id.id if check.lot_id else False,
            'picking_id': check.picking_id.id,
            'team_id': check.team_id.id,
            'user_id': check.user_id.id,
        }
        
        self.env['quality.alert'].sudo().create(alert_vals)


class LabSampleQualityIntegration(models.Model):
    """تكامل العينات المختبرية مع الجودة"""
    _inherit = 'lab.sample'

    quality_check_id = fields.Many2one(
        'quality.check', 
        string='فحص الجودة',
        help='فحص الجودة المرتبط بهذه العينة'
    )

    def write(self, vals):
        """تحديث حالة فحص الجودة عند تغيير حالة العينة"""
        result = super().write(vals)
        
        if 'state' in vals and not self.env.context.get('skip_quality_update', False):
            for sample in self:
                if sample.quality_check_id:
                    if vals['state'] == 'testing':
                        sample.quality_check_id.sudo().write({'lab_test_status': 'in_progress'})
                    elif vals['state'] == 'completed':
                        sample.quality_check_id.sudo().action_complete_lab_test()
        
        return result

    def action_complete_lab_test(self):
        """Alias ل action_complete لدعم استدعاءات قديمة"""
        return self.action_complete()


class LabResultSetQualityIntegration(models.Model):
    """تكامل مجموعات النتائج مع الجودة"""
    _inherit = 'lab.result.set'

    quality_check_id = fields.Many2one(
        'quality.check', 
        string='فحص الجودة',
        help='فحص الجودة المرتبط بهذه المجموعة'
    )

    def write(self, vals):
        """تحديث فحص الجودة عند تغيير حالة المطابقة"""
        result = super().write(vals)
        
        if 'overall_conformity' in vals:
            for result_set in self:
                if result_set.quality_check_id and vals['overall_conformity'] == 'fail':
                    result_set.quality_check_id._create_quality_alert(result_set.quality_check_id)
        
        return result


class StockPickingQualityLabIntegration(models.Model):
    """تحسين إشعار المختبر مع التكامل مع الجودة"""
    _inherit = 'stock.picking'

    def action_notify_lab(self):
        """
        تحسين إشعار المختبر لإنشاء فحوصات جودة تلقائياً
        
        • قبل أي معالجة، نتحقق من أن كل المنتجات المرتبطة بالانتقاء الحالية تحتوي
          إما على خطة فحص (flow template) أو قوالب فحص فردية.
        • إذا وُجد منتج واحد على الأقل بلا ربط، نعرض رسالة تحذير بسيطة
          ولا نُرسل أي إشعار ولا ننشئ سجلات أو أنشطة.
        
        ملاحظة: نُبقي الزر فعّالاً ليتمكن المستخدم من إعادة المحاولة بعد
        تصحيح ربط المنتج.
        """
        for picking in self:
            missing_products = [
                ml.product_id.name for ml in picking.move_line_ids
                if ml.product_id and not (
                    ml.product_id.product_tmpl_id.test_flow_template_id or
                    ml.product_id.test_template_ids
                )
            ]

            if missing_products:
                prod_list = '\n• '.join(missing_products)
                simple_msg = _(
                    "لا يمكن إشعار المختبر. المنتجات التالية غير مرتبطة بأي خطة فحص أو قالب فحص:\n\n• {products}\n\nيرجى ربط المنتج بالفحص المختبري ثم إعادة المحاولة."
                ).format(products=prod_list)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('تحذير'),
                        'message': simple_msg,
                        'type': 'warning',
                        'sticky': False,
                    }
                }

        result = super().action_notify_lab()

        warning_action = None
        for picking in self:
            action_result = picking._create_automatic_quality_checks()
            if action_result:
                warning_action = action_result

        return warning_action if warning_action else result

    def _create_automatic_quality_checks(self):
        """إنشاء فحوصات جودة تلقائية أو عينات مختبرية حسب نوع المنتج"""
        products_without_templates = []
        
        for move_line in self.move_line_ids:
            if not move_line.product_id:
                continue
                
            task = self.env['project.task'].search([
                ('stock_receipt_id', '=', self.id)
            ], limit=1)
            
            product = move_line.product_id
            flow_template = product.product_tmpl_id.test_flow_template_id
            test_templates = product.test_template_ids
            
            if flow_template:
                existing_sample = self.env['lab.sample'].search([
                    ('product_id', '=', product.id),
                    ('task_id', '=', task.id if task else False),
                    ('state', 'in', ['draft', 'received', 'testing']),
                ], limit=1)
                
                if not existing_sample:
                    planned_qty = getattr(move_line, 'product_uom_qty', 0) or move_line.move_id.product_uom_qty
                    qty = move_line.qty_done or planned_qty or 1

                    sample_vals = {
                        'product_id': product.id,
                        'task_id': task.id if task else False,
                        'state': 'received',
                        'quantity': qty,
                        'notes': f'تم إنشاؤها تلقائياً من الانتقاء {self.name}',
                    }
                    
                    sample = self.env['lab.sample'].sudo().create(sample_vals)
                    
                    try:
                        sample.action_start_testing()
                        self.message_post(
                            body=f"تم إنشاء عينة مختبرية {sample.name} للمنتج {product.name}"
                        )
                    except Exception as e:
                        sample.sudo().unlink()
                        raise UserError(f"فشل في بدء خطة الفحص للمنتج {product.name}: {str(e)}")
                
                continue
                
            elif test_templates:
                for template in test_templates:
                    quality_point = self.env['quality.point'].search([
                        ('product_ids', 'in', product.id),
                        ('picking_type_ids', 'in', self.picking_type_id.id),
                        ('lab_test_template_id', '=', template.id)
                    ], limit=1)
                    
                    if not quality_point:
                        quality_point = self.env['quality.point'].sudo().create_lab_quality_point(
                            product.id,
                            self.picking_type_id.id,
                            template.id
                        )
                    
                    existing_check = self.env['quality.check'].search([
                        ('picking_id', '=', self.id),
                        ('point_id', '=', quality_point.id),
                        ('product_id', '=', product.id),
                        ('lot_id', '=', move_line.lot_id.id if move_line.lot_id else False),
                    ], limit=1)

                    if not existing_check:
                        self.env['quality.check'].sudo().create({
                            'name': f"فحص {template.name} - {product.name}",
                            'point_id': quality_point.id,
                            'product_id': product.id,
                            'picking_id': self.id,
                            'lot_id': move_line.lot_id.id if move_line.lot_id else False,
                            'team_id': quality_point.team_id.id,
                            'user_id': self.env.user.id,
                        })
            
            else:
                products_without_templates.append(product.name)
        
        if products_without_templates:
            message = self._build_no_templates_warning_message(products_without_templates)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تحذير - منتجات بدون قوالب فحص'),
                    'message': message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
    
    def _build_no_templates_warning_message(self, products_without_templates):
        """بناء رسالة التحذير للمنتجات بدون قوالب فحص"""
        products_list = '\n• '.join(products_without_templates)
        
        message = _(
            "تم إشعار المختبر بنجاح، ولكن المنتجات التالية لا تحتوي على قوالب فحص مختبري أو خطة فحص:\n\n"
            "• {products}\n\n"
            "📋 لربط المنتجات بالفحوصات المختبرية:\n\n"
            "🎯 الخيار الأول - خطة فحص متكاملة (موصى به):\n"
            "1️⃣ انتقل إلى: المخزون ← المنتجات ← المنتجات\n"
            "2️⃣ افتح المنتج المطلوب\n"
            "3️⃣ انتقل إلى تبويب 'الفحوصات المختبرية'\n"
            "4️⃣ اختر 'خطة الفحص الافتراضية' (تتضمن عدة مراحل)\n"
            "5️⃣ احفظ التغييرات\n\n"
            "🎯 الخيار الثاني - قوالب فحص فردية:\n"
            "1️⃣ نفس الخطوات السابقة\n"
            "2️⃣ أضف قوالب الفحص في حقل 'قوالب الفحص المتاحة'\n"
            "3️⃣ يمكنك تعيين قوالب افتراضية في 'قوالب الفحص الافتراضية'\n\n"
            "💡 ملاحظة: خطة الفحص تنشئ عينة واحدة مع مراحل متعددة، بينما القوالب الفردية تنشئ فحوص جودة منفصلة"
        ).format(products=products_list)
        
        return message 
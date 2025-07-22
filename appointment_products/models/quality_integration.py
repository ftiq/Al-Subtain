# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QualityPointLabIntegration(models.Model):
    """التكامل مع نقاط الجودة للفحوصات المختبرية"""
    _inherit = 'quality.point'

    lab_test_template_id = fields.Many2one(
        'lab.test.template', 
        string='قالب الفحص المختبري',
        help='ربط نقطة الجودة بقالب الفحص المختبري',
        index=True
    )
    is_lab_test = fields.Boolean(
        string='فحص مختبري', 
        default=False,
        index=True
    )
    auto_create_lab_sample = fields.Boolean(
        string='إنشاء عينة مختبرية تلقائياً', 
        default=True,
        help='إنشاء عينة مختبرية تلقائياً عند إنشاء فحص الجودة'
    )

    @api.model
    def create_lab_quality_point(self, product_id, picking_type_id, lab_test_template_id):
        """إنشاء نقطة جودة للفحص المختبري"""
        try:
            product = self.env['product.product'].browse(product_id)
            template = self.env['lab.test.template'].browse(lab_test_template_id)
            
            if not product.exists():
                raise UserError(_("المنتج غير موجود: %s") % product_id)
            if not template.exists():
                raise UserError(_("قالب الفحص غير موجود: %s") % lab_test_template_id)
            
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
            
            quality_point = self.sudo().create(vals)
            _logger.info("تم إنشاء نقطة جودة مختبرية: %s للمنتج: %s", quality_point.name, product.name)
            return quality_point
            
        except Exception as e:
            _logger.error("خطأ في إنشاء نقطة الجودة المختبرية: %s", str(e))
            raise UserError(_("فشل في إنشاء نقطة الجودة المختبرية: %s") % str(e))

    def _get_lab_quality_team(self):
        """الحصول على فريق الجودة للمختبر"""
        try:
            lab_team = self.env['quality.alert.team'].search([
                ('name', 'ilike', 'مختبر')
            ], limit=1)
            
            if not lab_team:
                lab_team = self.env['quality.alert.team'].sudo().create({
                    'name': 'فريق المختبر',
                    'sequence': 10,
                    'company_id': self.env.company.id,
                })
                _logger.info("تم إنشاء فريق المختبر الجديد: %s", lab_team.name)
            
            return lab_team.id
            
        except Exception as e:
            _logger.error("خطأ في الحصول على فريق المختبر: %s", str(e))
            default_team = self.env['quality.alert.team'].search([], limit=1)
            return default_team.id if default_team else False


class QualityCheckLabIntegration(models.Model):
    """تكامل فحوصات الجودة مع النظام المختبري"""
    _inherit = 'quality.check'

    lab_sample_id = fields.Many2one(
        'lab.sample', 
        string='العينة المختبرية',
        help='العينة المختبرية المرتبطة بهذا الفحص',
        index=True
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
    ], string='حالة الفحص المختبري', default='pending', index=True, tracking=True)

    @api.model
    def create(self, vals):
        """إنشاء عينة مختبرية تلقائياً عند إنشاء فحص جودة"""
        check = super().create(vals)
        
        try:
            if check.point_id and check.point_id.is_lab_test and check.point_id.auto_create_lab_sample:
                check._create_lab_sample()
                _logger.info("تم إنشاء عينة مختبرية تلقائياً لفحص الجودة: %s", check.name)
        except Exception as e:
            _logger.error("خطأ في إنشاء العينة المختبرية التلقائية: %s", str(e))
        
        return check

    def _create_lab_sample(self):
        """إنشاء عينة مختبرية من فحص الجودة"""
        for check in self:
            try:
                if not check.lab_sample_id and check.point_id.lab_test_template_id:
                    task = self.env['project.task'].search([
                        ('stock_receipt_id', '=', check.picking_id.id)
                    ], limit=1)
                    
                    move_line = False
                    if check.picking_id:
                        move_line = check.picking_id.move_line_ids.filtered(
                            lambda ml: ml.product_id.id == check.product_id.id
                        )
                        move_line = move_line[0] if move_line else False

                    sample_subtype_id = False
                    if task and task.main_sample_subtype_id:
                        is_brick = (check.product_id.product_tmpl_id.sample_type_id and 
                                 check.product_id.product_tmpl_id.sample_type_id.code == 'MASONRY')
                        if is_brick:
                            sample_subtype_id = task.main_sample_subtype_id.id
                    
                    if task and not sample_subtype_id:
                        form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == check.product_id.id)
                        if form_line and form_line.sample_subtype_id:
                            sample_subtype_id = form_line.sample_subtype_id.id

                    field_serial = False
                    lab_code = False
                    if move_line:
                        field_serial = move_line.field_serial
                        lab_code = move_line.field_code
                    
                    if check.name and "- " in check.name:
                        lab_code_from_name = check.name.split("- ")[-1].strip()
                        if lab_code_from_name and lab_code_from_name != check.product_id.name:
                            if lab_code_from_name != lab_code:
                                lab_code = lab_code_from_name
                                
                                matching_move_line = check.picking_id.move_line_ids.filtered(
                                    lambda ml: ml.product_id.id == check.product_id.id and 
                                               ml.field_code == lab_code_from_name
                                )
                                if matching_move_line:
                                    field_serial = matching_move_line[0].field_serial
                                

                    sample_vals = {
                        'product_id': check.product_id.id,
                        'task_id': task.id if task else False,
                        'state': 'received',
                        'lab_test_template_id': check.point_id.lab_test_template_id.id,
                        'quality_check_id': check.id,
                        'quantity': 1,
                        'lab_code': lab_code,
                        'field_serial': field_serial,
                        'sample_subtype_id': sample_subtype_id,
                        'notes': f'تم إنشاؤها تلقائياً من الانتقاء {check.picking_id.name}',
                    }
                    
                    lab_sample = self.env['lab.sample'].sudo().create(sample_vals)
                    check.sudo().write({
                        'lab_sample_id': lab_sample.id,
                        'lab_test_status': 'pending'
                    })
                    _logger.info("تم إنشاء عينة مختبرية %s لفحص الجودة %s", lab_sample.name, check.name)
                    
            except Exception as e:
                _logger.error("خطأ في إنشاء العينة المختبرية للفحص %s: %s", check.name, str(e))
                raise UserError(_("فشل في إنشاء العينة المختبرية للفحص %s: %s") % (check.name, str(e)))

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
        for picking in self:
            # رسالة تشخيص ابتدائية
            self.message_post(
                body=f" بدء عملية إشعار المختبر لـ {self.name}"
            )
            
            missing_products = []
            for ml in picking.move_line_ids:
                if not ml.product_id:
                    continue
                    
                product_tmpl = ml.product_id.product_tmpl_id
                

                has_lab_test_template = product_tmpl.lab_test_template_id 
                has_general_plan = product_tmpl.test_flow_template_id or ml.product_id.test_template_ids  
                has_subtype_plans = product_tmpl.has_subtype_test_plans
                

                self.message_post(
                    body=f"🔍 فحص المنتج {ml.product_id.name}:<br/>"
                         f"قالب فحص مختبري: {'✅' if has_lab_test_template else '❌'} {product_tmpl.lab_test_template_id.name if has_lab_test_template else 'غير موجود'}<br/>"
                         f"خطة فحص عامة: {'✅' if has_general_plan else '❌'}<br/>"
                         f"خطط فرعية: {'✅' if has_subtype_plans else '❌'}"
                )
                

                if not has_lab_test_template and not has_general_plan and not has_subtype_plans:
                    missing_products.append(ml.product_id.name)

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
                
            brick_without_lab_codes = []
            
            for ml in picking.move_line_ids:
                if not ml.product_id:
                    continue
                
                is_brick = (ml.product_id.product_tmpl_id.sample_type_id and 
                            ml.product_id.product_tmpl_id.sample_type_id.code == 'MASONRY')
                
                if is_brick and not ml.field_code:
                    brick_without_lab_codes.append(ml.product_id.name)
            
            if brick_without_lab_codes:
                brick_without_lab_codes = list(set(brick_without_lab_codes))
                prod_list = '\n• '.join(brick_without_lab_codes)
                brick_msg = _(
                    "لا يمكن إشعار المختبر. منتجات الطابوق التالية ليس لديها رموز مختبرية:\n\n• {products}\n\nيرجى إدخال الرموز المختبرية لجميع سطور منتجات الطابوق ثم إعادة المحاولة."
                ).format(products=prod_list)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('تحذير'),
                        'message': brick_msg,
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
        
        brick_products_lab_codes = {}
        concrete_products_data = {}  
        

        self.message_post(
            body=f"📦 عدد أسطر الحركة في {self.name}: {len(self.move_line_ids)}"
        )
        

        for move_line in self.move_line_ids:
            if not move_line.product_id:
                continue
                
            product = move_line.product_id
            is_concrete = (product.product_tmpl_id.sample_type_id and 
                          product.product_tmpl_id.sample_type_id.code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES'])
                          

            sample_type_code = product.product_tmpl_id.sample_type_id.code if product.product_tmpl_id.sample_type_id else 'لا يوجد'
            self.message_post(
                body=f"⚙️ فحص منتج: {product.name}<br/>"
                     f"نوع العينة: {sample_type_code}<br/>"
                     f"هل هو خرسانة: {'✅ نعم' if is_concrete else '❌ لا'}"
            )
                          

            if is_concrete and (move_line.group_no or move_line.age_days or move_line.cube_count):
                if product.id not in concrete_products_data:
                    concrete_products_data[product.id] = {
                        'product': product,
                        'groups': {}  
                    }
                

                group_key = f"{move_line.group_no or 0}_{move_line.age_days or ''}_{move_line.field_code or ''}"
                if group_key not in concrete_products_data[product.id]['groups']:
                    concrete_products_data[product.id]['groups'][group_key] = {
                        'group_no': move_line.group_no,
                        'age_days': move_line.age_days,
                        'field_code': move_line.field_code,
                        'field_serial': move_line.field_serial,
                        'cube_count': move_line.cube_count or 0,
                        'seven_day_cubes': move_line.seven_day_cubes or 0,
                        'twenty_eight_day_cubes': move_line.twenty_eight_day_cubes or 0,
                        'total_cubes': move_line.total_cubes or 0,
                    }
        

        for move_line in self.move_line_ids:
            if not move_line.product_id or not move_line.field_code:
                continue
                
            product = move_line.product_id
            is_brick = (product.product_tmpl_id.sample_type_id and 
                        product.product_tmpl_id.sample_type_id.code == 'MASONRY')
            
            if is_brick:
                if product.id not in brick_products_lab_codes:
                    brick_products_lab_codes[product.id] = {
                        'product': product,
                        'lab_codes': []
                    }
                
                lab_code_info = {
                    'code': move_line.field_code,
                    'serial': move_line.field_serial or False
                }
                
                existing_codes = [code_info['code'] for code_info in brick_products_lab_codes[product.id]['lab_codes']]
                if move_line.field_code not in existing_codes:
                    brick_products_lab_codes[product.id]['lab_codes'].append(lab_code_info)
        

        self.message_post(
            body=f"🔍 تشخيص بيانات الخرسانة:<br/>"
                 f"عدد منتجات الخرسانة: {len(concrete_products_data)}<br/>"
                 f"المنتجات: {[concrete_products_data[pid]['product'].name for pid in concrete_products_data.keys()]}"
        )
        

        for product_id, concrete_data in concrete_products_data.items():
            product = concrete_data['product']
            groups = concrete_data['groups']
            

            self.message_post(
                body=f" معالجة منتج خرسانة: {product.name}<br/>"
                     f"عدد المجموعات: {len(groups)}"
            )
            
            if not groups:
                continue
                
            task = self.env['project.task'].search([
                ('stock_receipt_id', '=', self.id)
            ], limit=1)
            

            lab_test_template = product.product_tmpl_id.lab_test_template_id
            

            self.message_post(
                body=f"🔍 تشخيص منتج الخرسانة {product.name}:<br/>"
                     f"قالب الفحص المختبري: {lab_test_template.name if lab_test_template else 'غير محدد'}<br/>"
                     f"رمز القالب: {lab_test_template.code if lab_test_template else 'N/A'}<br/>"
                     f"عدد المعايير: {len(lab_test_template.criterion_ids) if lab_test_template else 0}"
            )
            

            sample_subtype_id = False
            if task and task.main_sample_subtype_id:
                sample_subtype_id = task.main_sample_subtype_id.id
            elif task:
                form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product.id)
                if form_line and form_line.sample_subtype_id:
                    sample_subtype_id = form_line.sample_subtype_id.id
            

            if not lab_test_template:
                products_without_templates.append(product.name)
                self.message_post(
                    body=f"❌ خطأ: لا يوجد قالب فحص مختبري للمنتج {product.name}. "
                         f"يرجى تحديد قالب فحص مختبري في إعدادات المنتج.",
                    message_type='comment'
                )
                continue
                

            self.message_post(
                body=f"✅ القالب النهائي لمنتج {product.name}: {lab_test_template.name}"
            )
                

            existing_sample = self.env['lab.sample'].search([
                ('product_id', '=', product.id),
                ('task_id', '=', task.id if task else False),
                ('state', 'in', ['draft', 'received', 'testing']),
                ('notes', 'ilike', f'عينة خرسانة من {self.name}%'),
            ], limit=1)
            
            if not existing_sample:

                total_quantity = sum(group_data['cube_count'] for group_data in groups.values()) or 1
                

                primary_field_code = next((group['field_code'] for group in groups.values() if group['field_code']), None)
                

                plan_note = f' - قالب: {lab_test_template.name}'
                

                sample_vals = {
                    'product_id': product.id,
                    'task_id': task.id if task else False,
                    'state': 'received',
                    'quantity': total_quantity,
                    'lab_code': primary_field_code or f'CONCRETE_{self.name}_{product.id}',
                    'sample_subtype_id': sample_subtype_id,
                    'stock_picking_id': self.id,
                    'lab_test_template_id': lab_test_template.id,  
                    'notes': f'عينة خرسانة من {self.name} - عدد {len(groups)} مجموعة{plan_note}',
                }
                
                try:
                    sample = self.env['lab.sample'].sudo().create(sample_vals)
                    

                    created_sets = []
                    for group_key, group_data in groups.items():

                        num_samples = group_data['cube_count'] or 1
                        

                        result_set_vals = {
                            'sample_id': sample.id,
                            'template_id': lab_test_template.id, 
                            'state': 'draft',
                            'number_of_samples': num_samples,
                            'concrete_group_no': group_data['group_no'] or 0,
                            'concrete_age_days': group_data['age_days'] or False,
                            'concrete_field_code': group_data['field_code'] or False,
                            'concrete_field_serial': group_data['field_serial'] or False,
                            'is_concrete_sample': True,
                        }
                        
                        result_set = self.env['lab.result.set'].sudo().create(result_set_vals)
                        created_sets.append(result_set)
                        

                    
                    created_sets_count = len(created_sets)
                    

                    groups_details = []
                    for result_set in created_sets:
                        group_detail = f"مجموعة {result_set.concrete_group_no}"
                        if result_set.concrete_age_days:
                            days_display = dict(result_set._fields['concrete_age_days'].selection).get(
                                result_set.concrete_age_days, result_set.concrete_age_days)
                            group_detail += f" ({days_display})"
                        if result_set.concrete_field_code:
                            group_detail += f" [رمز: {result_set.concrete_field_code}]"
                        group_detail += f" - {result_set.number_of_samples} عينة"
                        groups_details.append(group_detail)
                    
                    groups_list = "<br/>• ".join(groups_details)
                    

                    self.message_post(
                        body=f"تم إنشاء عينة خرسانة {sample.name} للمنتج {product.name}<br/>"
                             f"تم إنشاء {created_sets_count} مجموعة نتائج: <br/>• {groups_list}{plan_note}"
                    )
                    

                    self.sampling_status = 'generated'
                    
                except Exception as e:
                    if 'sample' in locals():
                        sample.sudo().unlink()
                    raise UserError(f"فشل في إنشاء عينة الخرسانة للمنتج {product.name}: {str(e)}")
                    

        for move_line in self.move_line_ids:
            if not move_line.product_id:
                continue
                
            task = self.env['project.task'].search([
                ('stock_receipt_id', '=', self.id)
            ], limit=1)
            
            product = move_line.product_id
            flow_template = product.product_tmpl_id.test_flow_template_id
            test_templates = product.test_template_ids
            
            is_brick = (product.product_tmpl_id.sample_type_id and 
                        product.product_tmpl_id.sample_type_id.code == 'MASONRY')
            

            is_concrete = (product.product_tmpl_id.sample_type_id and 
                          product.product_tmpl_id.sample_type_id.code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES'])
            
            if is_concrete:
                continue  
            
            if is_brick and product.id in brick_products_lab_codes:
                lab_codes = brick_products_lab_codes[product.id]['lab_codes']
                
                del brick_products_lab_codes[product.id]
                
                sample_subtype_id = False
                if task and task.main_sample_subtype_id:
                    sample_subtype_id = task.main_sample_subtype_id.id
                
                if task and not sample_subtype_id:
                    form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product.id)
                    if form_line and form_line.sample_subtype_id:
                        sample_subtype_id = form_line.sample_subtype_id.id
                

                flow_template = product.product_tmpl_id.test_flow_template_id
                actual_flow_template = flow_template
                if (product.product_tmpl_id.has_subtype_test_plans and 
                    sample_subtype_id and 
                    product.product_tmpl_id.subtype_test_plans_json):
                    
                    import json
                    try:
                        subtype_plans = json.loads(product.product_tmpl_id.subtype_test_plans_json)
                        subtype_plan_id = subtype_plans.get(str(sample_subtype_id))
                        if subtype_plan_id:
                            subtype_flow_template = self.env['lab.test.flow.template'].browse(subtype_plan_id)
                            if subtype_flow_template.exists():
                                actual_flow_template = subtype_flow_template
                    except (json.JSONDecodeError, TypeError):
                        pass  
                
                if actual_flow_template:
                    for lab_code_info in lab_codes:
                        lab_code = lab_code_info['code']
                        field_serial = lab_code_info['serial']
                        
                        existing_sample = self.env['lab.sample'].search([
                            ('product_id', '=', product.id),
                            ('task_id', '=', task.id if task else False),
                            ('state', 'in', ['draft', 'received', 'testing']),
                            ('notes', 'ilike', f'الرمز المختبري: {lab_code}%'),
                        ], limit=1)
                        
                        if not existing_sample:
                            planned_qty = getattr(move_line, 'product_uom_qty', 0) or move_line.move_id.product_uom_qty
                            qty = move_line.qty_done or planned_qty or 1


                            plan_note = ''
                            if actual_flow_template != flow_template:
                                subtype = self.env['lab.sample.subtype'].browse(sample_subtype_id)
                                plan_note = f' (خطة {actual_flow_template.name} للنوع الفرعي: {subtype.name if subtype else "unknown"})'
                            
                            sample_vals = {
                                'product_id': product.id,
                                'task_id': task.id if task else False,
                                'state': 'received',
                                'quantity': qty,
                                'lab_code': lab_code,
                                'field_serial': field_serial,
                                'sample_subtype_id': sample_subtype_id,
                                'notes': f'تم إنشاؤها تلقائياً من الانتقاء {self.name} - الرمز المختبري: {lab_code}{plan_note}',
                            }
                            
                            sample = self.env['lab.sample'].sudo().create(sample_vals)
                            
                            try:

                                if actual_flow_template and actual_flow_template != flow_template:
                                    sample_with_context = sample.with_context(force_flow_template_id=actual_flow_template.id)
                                    sample_with_context.action_start_testing()
                                    plan_info = f' بخطة {actual_flow_template.name}'
                                else:
                                    sample.action_start_testing()
                                    plan_info = ''
                                    
                                self.message_post(
                                    body=f"تم إنشاء عينة مختبرية {sample.name} للمنتج {product.name} (رمز مختبري: {lab_code}){plan_info}"
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
                        
                        for lab_code_info in lab_codes:
                            lab_code = lab_code_info['code']
                            field_serial = lab_code_info['serial']
                            
                            existing_check = self.env['quality.check'].search([
                                ('picking_id', '=', self.id),
                                ('point_id', '=', quality_point.id),
                                ('product_id', '=', product.id),
                                ('name', 'ilike', f"%{lab_code}%"),
                            ], limit=1)

                            if not existing_check:
                                self.env['quality.check'].sudo().create({
                                    'name': f"فحص {template.name} - {product.name} - {lab_code}",
                                    'point_id': quality_point.id,
                                    'product_id': product.id,
                                    'picking_id': self.id,
                                    'lot_id': move_line.lot_id.id if move_line.lot_id else False,
                                    'team_id': quality_point.team_id.id,
                                    'user_id': self.env.user.id,
                                })
                    
                    continue
                
                else:
                    products_without_templates.append(product.name)
                    continue
            

            if product.product_tmpl_id.sample_type_id and product.product_tmpl_id.sample_type_id.code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES']:
                continue  
            
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
                        'lab_code': move_line.field_code if move_line.field_code else False,
                        'field_serial': move_line.field_serial if move_line.field_serial else False,
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
            "تم إشعار المختبر بنجاح، ولكن المنتجات التالية لا تحتوي على خطة فحص:\n\n"
            "• {products}\n\n"
            "📋 لربط المنتجات بالفحوصات المختبرية:\n\n"
            "🎯 الخيار الأول - خطة فحص متكاملة (موصى به):\n"
            "1️⃣ انتقل إلى: المخزون ← المنتجات ← المنتجات\n"
            "2️⃣ افتح المنتج المطلوب\n"
            "3️⃣ انتقل إلى تبويب 'الفحوصات المختبرية'\n"
            "4️⃣ اختر 'خطة الفحص الافتراضية' (تتضمن عدة مراحل)\n"
            "5️⃣ احفظ التغييرات\n\n"
        ).format(products=products_list)
        
        return message 
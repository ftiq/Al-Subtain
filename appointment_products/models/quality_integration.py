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

    @api.model_create_multi
    def create(self, vals_list):

        checks = super().create(vals_list)
        
        # When confirming a quotation, skip auto-creating lab samples from quality checks
        if self.env.context.get('skip_lab_sample_creation_on_sale_confirm'):
            return checks
        
        for check in checks:
            try:
                if check.point_id and check.point_id.is_lab_test and check.point_id.auto_create_lab_sample:
                    check._create_lab_sample()
                    _logger.info("تم إنشاء عينة مختبرية تلقائياً لفحص الجودة: %s", check.name)
            except Exception as e:
                _logger.error("خطأ في إنشاء العينة المختبرية التلقائية: %s", str(e))
        
        return checks

    def _create_lab_sample(self):
        """إنشاء عينة مختبرية من فحص الجودة"""
        for check in self:
            try:
                # Safety guard: never create lab samples during sale confirm flow
                if self.env.context.get('skip_lab_sample_creation_on_sale_confirm'):
                    continue
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
                        'state': 'draft',
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

            missing_products = []
            for ml in picking.move_line_ids:
                if not ml.product_id:
                    continue
                    
                product_tmpl = ml.product_id.product_tmpl_id
                

                has_lab_test_template = product_tmpl.lab_test_template_id 
                has_general_plan = product_tmpl.test_flow_template_id or ml.product_id.test_template_ids  
                has_subtype_plans = product_tmpl.has_subtype_test_plans
                


                

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


        task = self.env['project.task'].search([
            ('stock_receipt_id', '=', self.id)
        ], limit=1)

        for move_line in self.move_line_ids:
            if not move_line.product_id:
                continue
            
            product = move_line.product_id

            st_code = (product.product_tmpl_id.sample_type_id.code or '').upper() if product.product_tmpl_id and product.product_tmpl_id.sample_type_id else ''
            is_concrete_non_core = st_code in ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES']
            is_concrete_core = (st_code == 'CONCRETE_CORE')

            pcode = (product.default_code or '').upper()
            pname = (product.name or '')
            is_asphalt = ('ASPHALT' in st_code) or ('SURFACE' in pcode) or ('BASE' in pcode) or ('قير' in pname)


            sample_subtype_id = False
            if task and task.main_sample_subtype_id:
                sample_subtype_id = task.main_sample_subtype_id.id
            if task and not sample_subtype_id:
                form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product.id)
                if form_line and form_line.sample_subtype_id:
                    sample_subtype_id = form_line.sample_subtype_id.id


            if (is_concrete_non_core or is_concrete_core) and (move_line.group_no or move_line.age_days or move_line.cube_count):
                if product.id not in concrete_products_data:
                    concrete_products_data[product.id] = {
                        'product': product,
                        'groups': {},
                        'is_core': is_concrete_core,
                    }
                else:

                    if is_concrete_core:
                        concrete_products_data[product.id]['is_core'] = True
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

                continue




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

            test_templates = product.test_template_ids

            if actual_flow_template:
                lab_code = move_line.field_code or False
                field_serial = move_line.field_serial or False

                existing_sample = self.env['lab.sample'].search([
                    ('product_id', '=', product.id),
                    ('task_id', '=', task.id if task else False),
                    ('state', 'in', ['draft', 'received', 'testing']),
                ], limit=1)

                if not existing_sample:
                    planned_qty = getattr(move_line, 'product_uom_qty', 0) or move_line.move_id.product_uom_qty
                    qty = move_line.qty_done or planned_qty or 1

                    plan_note = ''
                    if actual_flow_template and actual_flow_template != flow_template:
                        subtype = self.env['lab.sample.subtype'].browse(sample_subtype_id)
                        plan_note = f' (خطة {actual_flow_template.name} للنوع الفرعي: {subtype.name if subtype else "unknown"})'
                    
                    sample_vals = {
                        'product_id': product.id,
                        'task_id': task.id if task else False,
                        'state': 'draft',
                        'quantity': qty,
                        'lab_code': lab_code,
                        'field_serial': field_serial,
                        'sample_subtype_id': sample_subtype_id,
                        'notes': f'تم إنشاؤها تلقائياً من الانتقاء {self.name}{plan_note}',
                    }
                    
                    sample = self.env['lab.sample'].sudo().create(sample_vals)


                    try:
                        if actual_flow_template:
                            # Use a savepoint so failures inside action_next_step do not abort the whole tx
                            with self.env.cr.savepoint():
                                flow = self.env['lab.test.flow'].sudo().create({
                                    'name': _("Flow %s") % sample.name,
                                    'sample_id': sample.id,
                                    'template_id': actual_flow_template.id,
                                })
                                flow.action_next_step()
                    except Exception as e:
                        _logger.warning("Failed to auto-start lab test flow for sample %s: %s", sample.name, str(e))
                    
                    plan_info = f' بخطة {actual_flow_template.name}' if (actual_flow_template and actual_flow_template != flow_template) else ''
                    self.message_post(
                        body=(
                            f"تم إنشاء عينة مختبرية {sample.name}<br/>"
                            f"منتج: {product.name}<br/>"
                            f"رمز مختبري: {lab_code or '-'}<br/>"
                            f"تاريخ الإنشاء: {fields.Date.today()}{plan_info}"
                        )
                    )
                    
                    continue
                else:

                    try:
                        has_rs = bool(self.env['lab.result.set'].search_count([('sample_id', '=', existing_sample.id)]))
                        has_flow = bool(self.env['lab.test.flow'].search_count([('sample_id', '=', existing_sample.id)]))

                        if actual_flow_template and (not has_rs and not has_flow):
                            # Isolate any failure with a savepoint
                            with self.env.cr.savepoint():
                                flow = self.env['lab.test.flow'].sudo().create({
                                    'name': _("Flow %s") % existing_sample.name,
                                    'sample_id': existing_sample.id,
                                    'template_id': actual_flow_template.id,
                                })
                                flow.action_next_step()
                    except Exception as e:
                        _logger.warning("Failed to ensure result sets for existing sample %s: %s", existing_sample.name, str(e))
                    
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
        

        for product_id, concrete_data in concrete_products_data.items():
            product = concrete_data['product']
            groups = concrete_data['groups']
            is_core = bool(concrete_data.get('is_core'))
            if not groups:
                continue

            lab_test_templates = product.product_tmpl_id.lab_test_template_id

            if is_core:
                core_tmpl = lab_test_templates.filtered(lambda t: t.code == 'CONCRETE_CORE_TEST')
                primary_template = core_tmpl[0] if core_tmpl else (lab_test_templates[0] if lab_test_templates else False)
            else:
                concrete_comp_template = lab_test_templates.filtered(lambda t: t.code == 'CONCRETE_COMP')
                primary_template = concrete_comp_template[0] if concrete_comp_template else (lab_test_templates[0] if lab_test_templates else False)

            sample_subtype_id = False
            if task and task.main_sample_subtype_id:
                sample_subtype_id = task.main_sample_subtype_id.id
            elif task:
                form_line = task.form_line_ids.filtered(lambda l: l.product_id.id == product.id)
                if form_line and form_line.sample_subtype_id:
                    sample_subtype_id = form_line.sample_subtype_id.id

            if not primary_template:
                products_without_templates.append(product.name)
                self.message_post(
                    body=f"خطأ: لا يوجد قالب فحص مختبري للمنتج {product.name}. يرجى تحديد قالب فحص مختبري في إعدادات المنتج.",
                    message_type='comment'
                )
                continue

            existing_sample = self.env['lab.sample'].search([
                ('product_id', '=', product.id),
                ('task_id', '=', task.id if task else False),
                ('state', 'in', ['draft', 'received', 'testing']),
                ('notes', 'ilike', f'عينة خرسانة من {self.name}%'),
            ], limit=1)

            if not existing_sample:
                total_quantity = sum(group_data['cube_count'] for group_data in groups.values()) or 1
                primary_field_code = next((group['field_code'] for group in groups.values() if group['field_code']), None)
                templates_note = f" - قوالب: {', '.join(lab_test_templates.mapped('name'))}"

                sample_vals = {
                    'product_id': product.id,
                    'task_id': task.id if task else False,
                    'state': 'draft',
                    'quantity': total_quantity,
                    'lab_code': primary_field_code or f'CONCRETE_{self.name}_{product.id}',
                    'sample_subtype_id': sample_subtype_id,
                    'stock_picking_id': self.id,
                    'lab_test_template_id': primary_template.id,
                    'notes': f'عينة خرسانة من {self.name} - عدد {len(groups)} مجموعة{templates_note}',
                }

                try:
                    sample = self.env['lab.sample'].sudo().create(sample_vals)

                    created_sets = []
                    for group_key, group_data in groups.items():
                        num_samples = group_data['cube_count'] or 1
                        result_set_vals = {
                            'sample_id': sample.id,
                            'template_id': primary_template.id,
                            'state': 'draft',
                            'number_of_samples': num_samples,
                            'concrete_group_no': group_data['group_no'] or 0,
                            'concrete_age_days': group_data['age_days'] or False,
                            'concrete_field_code': group_data['field_code'] or False,
                            'concrete_field_serial': group_data['field_serial'] or False,
                            'is_concrete_sample': True,

                            'casting_date': False if is_core else fields.Date.today(),
                            'required_age_days': False if is_core else (group_data['age_days'] or '28'),
                        }
                        result_set = self.env['lab.result.set'].sudo().create(result_set_vals)
                        created_sets.append(result_set)

                    if not is_core:
                        overall_template = lab_test_templates.filtered(lambda t: t.code == 'CONCRETE_OVERALL_AVG')
                        if overall_template:
                            overall_set_vals = {
                                'sample_id': sample.id,
                                'template_id': overall_template[0].id,
                                'state': 'draft',
                                'number_of_samples': 1,
                                'is_concrete_sample': True,
                                'casting_date': fields.Date.today(),
                            }
                            overall_set = self.env['lab.result.set'].sudo().create(overall_set_vals)
                            created_sets.append(overall_set)

                    if not is_core:
                        specific_averages_template = lab_test_templates.filtered(lambda t: t.code == 'CONCRETE_SPECIFIC_AVG')
                        if specific_averages_template:
                            specific_set_vals = {
                                'sample_id': sample.id,
                                'template_id': specific_averages_template[0].id,
                                'state': 'draft',
                                'number_of_samples': 1,
                                'is_concrete_sample': True,
                                'casting_date': fields.Date.today(),
                            }
                            specific_set = self.env['lab.result.set'].sudo().create(specific_set_vals)
                            created_sets.append(specific_set)

                    groups_info = []
                    for group_key, group_data in groups.items():
                        age_text = group_data['age_days'] or 'غير محدد'
                        field_code = group_data['field_code'] or 'غير محدد'
                        groups_info.append(
                            f"مجموعة {group_data['group_no']} - {age_text} - رمز: {field_code}"
                        )
                    groups_details = "\n• ".join(groups_info)

                    self.message_post(
                        body=f"تم إنشاء عينة خرسانة {sample.name}\n"
                             f"عدد المجموعات: {len(created_sets)}\n"
                             f"تفاصيل المجموعات:\n• {groups_details}"
                    )

                    self.sampling_status = 'generated'
                except Exception as e:
                    if 'sample' in locals():
                        sample.sudo().unlink()
                    raise UserError(f"فشل في إنشاء عينة الخرسانة للمنتج {product.name}: {str(e)}")

        
        if not products_without_templates:
            total_samples = self.env['lab.sample'].search_count([
                ('task_id.stock_receipt_id', '=', self.id)
            ])
            
            total_result_sets = self.env['lab.result.set'].search_count([
                ('sample_id.task_id.stock_receipt_id', '=', self.id)
            ])
            
            self.message_post(
                body=f"تم إشعار المختبر بنجاح<br/>"
                     f"عدد العينات المنشأة: {total_samples}<br/>"
                     f"عدد مجموعات النتائج: {total_result_sets}<br/>"
                     f"تم ملء تاريخ الصب تلقائياً لجميع العينات"
            )
        
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
            "لربط المنتجات بالفحوصات المختبرية:\n\n"
            "الخيار الأول - خطة فحص متكاملة (موصى به):\n"
            "انتقل إلى: المخزون ← المنتجات ← المنتجات\n"
            "2️⃣ افتح المنتج المطلوب\n"
            "3️⃣ انتقل إلى تبويب 'الفحوصات المختبرية'\n"
            "4️⃣ اختر 'خطة الفحص الافتراضية' (تتضمن عدة مراحل)\n"
            "5️⃣ احفظ التغييرات\n\n"
        ).format(products=products_list)
        
        return message 
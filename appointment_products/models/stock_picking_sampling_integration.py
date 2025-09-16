# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class StockPickingSamplingIntegration(models.Model):
    """تكامل حركة المخزون مع نظام العينات"""
    _inherit = 'stock.picking'

    planned_concrete_m3 = fields.Float(
        string='الكمية المخططة (م³)',
        help='كمية الخرسانة المخططة بالمتر المكعب'
    )
    
    concrete_sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع عينة الخرسانة',
        help='نوع العينة للخرسانة (أبنية، أساسات، جسور)'
    )
    
    concrete_sample_subtype_id = fields.Many2one(
        'lab.sample.subtype',
        string='النوع الفرعي',
        domain="[('sample_type_id', '=', concrete_sample_type_id)]",
        help='النوع الفرعي لعينة الخرسانة'
    )
    
    enable_7_days_samples = fields.Boolean(
        string='7 أيام',
        default=False,
        help='تفعيل عينات 7 أيام'
    )
    
    enable_reserve_samples = fields.Boolean(
        string='احتياط',
        default=False,
        help='تفعيل عينات الاحتياط'
    )
    
    seven_days_for_all_groups = fields.Boolean(
        string='7 أيام لكل المجموعات',
        default=True,
        help='إذا تم تفعيله: ينشئ عينات 7 أيام لكل المجموعات. إذا لم يتم تفعيله: ينشئ عينات 7 أيام للمجموعة الأولى فقط'
    )
    
    reserve_for_all_groups = fields.Boolean(
        string='احتياط لكل المجموعات',
        default=True,
        help='إذا تم تفعيله: ينشئ عينات احتياط لكل المجموعات. إذا لم يتم تفعيله: ينشئ عينات احتياط للمجموعة الأولى فقط' 
    )
    
    estimated_samples = fields.Integer(
        string='العينات المقدرة',
        help='عدد العينات المقدر بناءً على الكمية ونوع العينة'
    )
    
    estimated_cubes = fields.Integer(
        string='المكعبات المقدرة',
        help='عدد المكعبات المقدر بناءً على الكمية ونوع العينة'
    )
    

    
    generated_samples_count = fields.Integer(
        string='العينات المُنشأة',
        compute='_compute_generated_samples_count',
        help='عدد العينات التي تم إنشاؤها فعلياً'
    )
    
    move_lines_with_codes_count = fields.Integer(
        string='خطوط الحركة مع الأرقام',
        compute='_compute_move_lines_with_codes_count',
        help='عدد خطوط الحركة التي تحتوي على أرقام تسلسلية'
    )
    
    generated_sample_ids = fields.One2many(
        'lab.sample',
        'stock_picking_id',
        string='العينات المُنشأة',
        help='العينات التي تم إنشاؤها من هذه الحركة'
    )
    
    sampling_status = fields.Selection([
        ('none', 'لا يوجد'),
        ('required', 'مطلوب'),
        ('calculated', 'محسوب'),
        ('generated', 'تم الإنشاء'),
        ('completed', 'مكتمل')
    ], string='حالة العينات', default='none', tracking=True)
    
    sampling_notes = fields.Text(string='ملاحظات العينات')
    


    last_calculation_result = fields.Text(string='نتيجة الحساب الأخيرة', readonly=True)

    is_masonry_sample = fields.Boolean(
        string='عينة طابوق',
        compute='_compute_is_masonry_sample',
        store=True
    )


    is_concrete_sample = fields.Boolean(
        string='عينة خرسانية',
        compute='_compute_is_concrete_sample',
        store=True
    )

    @api.onchange('planned_concrete_m3', 'concrete_sample_type_id')
    def _onchange_sampling_preview(self):
        """حساب فوري للعينات عند تغيير الكمية أو النوع"""

        self = self.with_context(allow_signed_update=True)
        if self.planned_concrete_m3 and self.concrete_sample_type_id:
            rule = self.env['lab.sample.rule'].search([
                ('sample_type_id', '=', self.concrete_sample_type_id.id),
                ('active', '=', True)
            ], limit=1)
            
            if rule:
                try:
                    result = rule.compute_sampling(self.planned_concrete_m3)
                    self.estimated_samples = result['total_groups']
                    self.estimated_cubes = result['twenty_eight_cubes']
                    self.last_calculation_result = str(result)
                    
                    if self.sampling_status == 'none':
                        self.sampling_status = 'required'
                        
                except Exception as e:
                    _logger.warning('Error calculating samples for picking %s: %s', self.name or 'new', str(e))
                    self.estimated_samples = 0
                    self.estimated_cubes = 0
            else:
                self.estimated_samples = 0
                self.estimated_cubes = 0
        else:
            self.estimated_samples = 0
            self.estimated_cubes = 0
            self.sampling_status = 'none'

    @api.depends('generated_sample_ids')
    def _compute_generated_samples_count(self):
        """حساب عدد العينات المُنشأة"""
        for picking in self:
            picking.generated_samples_count = len(picking.generated_sample_ids)

    @api.depends('move_line_ids.field_code')
    def _compute_move_lines_with_codes_count(self):
        """حساب عدد خطوط الحركة التي تحتوي على أرقام تسلسلية"""
        for picking in self:
            picking.move_lines_with_codes_count = len(picking.move_line_ids.filtered(lambda line: line.field_code))

    @api.onchange('concrete_sample_type_id')
    def _onchange_concrete_sample_type_id(self):
        """تصفية الأنواع الفرعية عند تغيير نوع العينة"""
        if self.concrete_sample_type_id:
            self.concrete_sample_subtype_id = False
            return {
                'domain': {
                    'concrete_sample_subtype_id': [
                        ('sample_type_id', '=', self.concrete_sample_type_id.id)
                    ]
                }
            }
        else:
            return {
                'domain': {
                    'concrete_sample_subtype_id': []
                }
            }

    def _apply_core_defaults_to_lines(self):
        """تطبيق افتراضيات الكور الخرساني على سطور الحركة الحالية.
        - تفريغ العمر (age_days)
        - ضبط عدد المكعبات إلى 2
        - مزامنة qty_done و sample_quantity
        لا يطبق إذا كانت الحركة موقعة.
        """
        for picking in self:
            try:
                if picking.is_signed:
                    continue
                if not (picking.concrete_sample_type_id and (picking.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE'):
                    continue
                for line in picking.move_line_ids:
                    changed = False
                    if line.age_days in (False, '28'):
                        line.age_days = False
                        changed = True
                    if not line.cube_count or line.cube_count == 3:
                        line.cube_count = 2
                        changed = True
                    if changed:
                        line.qty_done = float(line.cube_count)
                        line.sample_quantity = line.cube_count
            except Exception:
                continue

    def _generate_or_update_samples(self):
        """إنشاء أو تحديث خطوط حركة العينات بناءً على القيم المقدّرة الحالية.
        """
        self.ensure_one()
        
        self = self.with_context(allow_signed_update=True)

        total_samples = self.estimated_samples
        if not total_samples:
            raise UserError(_('يجب حساب العينات أولاً.'))


        lines_per_group = 1 
        if self.enable_7_days_samples:
            lines_per_group += 1 
        if self.enable_reserve_samples:
            lines_per_group += 1 
        
        total_lines = total_samples * lines_per_group
        
        if not self.move_ids:
            move_vals = {
                'name': self.name or 'Sample Distribution',
                'picking_id': self.id,
                'product_id': self.env['product.product'].search([('name', 'ilike', 'خرسانة')], limit=1).id or 1,
                'product_uom_qty': total_lines,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            }
            move = self.env['stock.move'].create(move_vals)
        else:
            move = self.move_ids[0]
            move.product_uom_qty = total_lines

        groups_per_truck = total_samples
        remaining_groups = 0

        existing_lines = move.move_line_ids.sorted('group_no') if move.move_line_ids else self.env['stock.move.line']
        required_line_vals = []

        current_group = 1
        line_index = 0
        def _cube_distribution():
            rule = self.env['lab.sample.rule'].search([
                ('sample_type_id', '=', self.concrete_sample_type_id.id),
                ('active', '=', True)
            ], limit=1)
            if rule:
                cubes_per_group = rule.cubes_per_group
                extra_cubes_per_group = rule.extra_cubes_per_group
                test_ages = []
                if rule.test_ages:
                    test_ages = [int(a.strip()) for a in rule.test_ages.split(',') if a.strip()]
                twenty_eight = cubes_per_group
                additional_ages = []
                for extra_idx in range(1, extra_cubes_per_group + 1):
                    if extra_idx <= len(test_ages):
                        additional_ages.append(test_ages[extra_idx - 1])
                    else:
                        additional_ages.append(7)
                seven = additional_ages.count(7)
                twenty_eight += additional_ages.count(28)
                return cubes_per_group + extra_cubes_per_group, seven, twenty_eight
            return 3, 0, 3

        total_cubes_line, seven_day_default, twenty_eight_default = _cube_distribution()
        
        cubes_per_age = 3
        reserve_cubes = cubes_per_age if self.enable_reserve_samples else 0
        seven_day_cubes = cubes_per_age if self.enable_7_days_samples else 0
        twenty_eight_cubes = cubes_per_age
        
        enable_7_days = self.enable_7_days_samples
        enable_28_days = True
        enable_reserve = self.enable_reserve_samples

        created_count = 0
        updated_count = 0

        existing_lines = move.move_line_ids
        if existing_lines:
            existing_lines.unlink()
        
        is_core = bool(self.concrete_sample_type_id and (self.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE')
        for current_group in range(1, total_samples + 1):

            temp_line = self.env['stock.move.line'].new({
                'picking_id': self.id,
                'move_id': move.id
            })
            group_field_serial = temp_line._generate_field_serial()
            

            group_lab_code = self.env['stock.move.line']._generate_lab_code()

            if is_core:

                line_vals = {
                    'move_id': move.id,
                    'picking_id': self.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'qty_done': 2.0,
                    'group_no': current_group,
                    'field_code': group_lab_code,
                    'field_serial': group_field_serial,
                    'age_days': False,
                    'sample_quantity': 2,
                    'cube_count': 2,
                    'twenty_eight_day_cubes': 0,
                    'seven_day_cubes': 0,
                }
                self.env['stock.move.line'].create(line_vals)
                created_count += 1
                continue


            if enable_28_days:
                line_vals = {
                    'move_id': move.id,
                    'picking_id': self.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'qty_done': 1.0,
                    'group_no': current_group,
                    'field_code': group_lab_code,
                    'field_serial': group_field_serial,
                    'age_days': '28',
                    'sample_quantity': twenty_eight_cubes,
                    'cube_count': twenty_eight_cubes,
                    'twenty_eight_day_cubes': twenty_eight_cubes,
                    'seven_day_cubes': 0,
                }
                self.env['stock.move.line'].create(line_vals)
                created_count += 1

            should_create_7_days = enable_7_days and (
                self.seven_days_for_all_groups or current_group == 1
            )
            if should_create_7_days:
                line_vals = {
                    'move_id': move.id,
                    'picking_id': self.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'qty_done': 1.0,
                    'group_no': current_group,
                    'field_code': group_lab_code, 
                    'field_serial': group_field_serial, 
                    'age_days': '7',
                    'sample_quantity': seven_day_cubes,
                    'cube_count': seven_day_cubes,
                    'seven_day_cubes': seven_day_cubes,
                    'twenty_eight_day_cubes': 0,
                }
                self.env['stock.move.line'].create(line_vals)
                created_count += 1

            should_create_reserve = enable_reserve and (
                self.reserve_for_all_groups or current_group == 1
            )
            if should_create_reserve:
                line_vals = {
                    'move_id': move.id,
                    'picking_id': self.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'qty_done': 1.0,
                    'group_no': current_group,
                    'field_code': group_lab_code,   
                    'field_serial': group_field_serial,
                    'age_days': 'reserve',
                    'sample_quantity': reserve_cubes,
                    'cube_count': reserve_cubes,
                    'seven_day_cubes': 0,
                    'twenty_eight_day_cubes': 0,
                }
                self.env['stock.move.line'].create(line_vals)
                created_count += 1

        self._compute_generated_samples_count()
        self._compute_move_lines_with_codes_count()
        
        self.sampling_status = 'generated'
        message = _(
            'تم إنشاء توزيع العينات بنجاح.\n'
            'تم إنشاء %s سطر جديد وتحديث %s سطر موجود.'
        ) % (created_count, updated_count)
        return {
            'type': 'ir.actions.act_window',
            'name': _('حركة المخزون - عينات الخرسانة'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': {
                'default_active_tab': 'concrete_sampling',
                'show_success_message': True,
                'success_message': message,
            },
        }

    def action_recalculate_samples(self):
        """إعادة حساب العينات يدوياً مع تحديث/استكمال الخطوط"""
        self.ensure_one()
        self = self.with_context(allow_signed_update=True)
        if not self.planned_concrete_m3:
            raise UserError(_('يجب تحديد الكمية المخططة للخرسانة'))
        if not self.concrete_sample_type_id:
            raise UserError(_('يجب تحديد نوع عينة الخرسانة'))

        self._onchange_sampling_preview()

        return self._generate_or_update_samples()

    def action_generate_samples(self):
        """توزيع أو تحديث العينات عند الطلب"""
        self.ensure_one()
        if not self.estimated_samples:
            raise UserError(_('يجب حساب العينات أولاً. تأكد من إدخال الكمية ونوع العينة.'))

        result = self._generate_or_update_samples()

        return {
            'type': 'ir.actions.act_window',
            'name': _('حركة المخزون - العينات'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_calculate_samples(self):
        """استدعاء متوافق مع الإصدارات السابقة—يوجه إلى action_recalculate_samples"""
        return self.action_recalculate_samples()

    def write(self, vals):
        """تحديث حالة العينات عند تغيير الحقول"""
        result = super().write(vals)
        
        if 'planned_concrete_m3' in vals or 'concrete_sample_type_id' in vals:
            for picking in self:
                if picking.move_lines_with_codes_count == 0:
                    picking.sampling_status = 'required' if (picking.planned_concrete_m3 and picking.concrete_sample_type_id) else 'none'
        

        try:
            if 'concrete_sample_type_id' in vals:
                for picking in self:
                    if picking.concrete_sample_type_id and (picking.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                        picking._apply_core_defaults_to_lines()
        except Exception:
            pass
        
        return result

    @api.depends('concrete_sample_type_id')
    def _compute_is_masonry_sample(self):
        for rec in self:
            rec.is_masonry_sample = bool(rec.concrete_sample_type_id and rec.concrete_sample_type_id.code == 'MASONRY')

    @api.depends('concrete_sample_type_id')
    def _compute_is_concrete_sample(self):
        allowed_codes = ['CONCRETE_BUILDINGS', 'CONCRETE_FOUNDATIONS', 'CONCRETE_BRIDGES', 'CONCRETE_CORE']
        for rec in self:
            rec.is_concrete_sample = bool(rec.concrete_sample_type_id and rec.concrete_sample_type_id.code in allowed_codes)
    
    @api.model
    def _get_concrete_sample_type_domain(self):
        """
        Returns:
            list: دومين لحقل concrete_sample_type_id
        """
        product = False
        if self.task_id and self.task_id.product_id:
            product = self.task_id.product_id
        elif self.origin:
            task = self.env['project.task'].search([('stock_receipt_id', '=', self.id)], limit=1)
            if task and task.product_id:
                product = task.product_id
        
        if product and product.detailed_type == 'service':
            return [('code', 'ilike', 'CONCRETE')]
        
        return [('id', '=', -1)]  


class LabSampleStockPickingLink(models.Model):
    """ربط العينات بحركة المخزون"""
    _inherit = 'lab.sample'
    
    stock_picking_id = fields.Many2one(
        'stock.picking',
        string='حركة المخزون',
        help='حركة المخزون المرتبطة بهذه العينة'
    )
    
    planned_concrete_m3 = fields.Float(
        related='stock_picking_id.planned_concrete_m3',
        string='الكمية المخططة (م³)',
        readonly=True
    )
    
    # concrete_sample_type_id = fields.Many2one(
    #     related='stock_picking_id.concrete_sample_type_id',
    #     string='نوع عينة الخرسانة',
    #     readonly=True
    # ) 
    # Note: concrete_sample_type_id is now defined in lab_sample_clean.py as related='task_id.concrete_sample_type_id' 
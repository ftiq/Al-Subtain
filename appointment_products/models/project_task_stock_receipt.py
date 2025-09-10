# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
class ProjectTaskStockReceipt(models.Model):
    _inherit = 'project.task'

    stock_receipt_id = fields.Many2one('stock.picking', string='Stock Receipt', copy=False, readonly=True)
    

    planned_concrete_m3 = fields.Float(
        related='stock_receipt_id.planned_concrete_m3', 
        store=False, readonly=False, 
        string='Planned Concrete (m³)'
    )
    concrete_sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='نوع عينة الخرسانة',
        compute='_compute_concrete_sample_type_from_product',
        store=True,
        readonly=True,
        help='نوع العينة للخرسانة (أبنية، أساسات، جسور) - يتم تعيينه تلقائياً من المنتج المرتبط'
    )
    
    cube_compaction_method = fields.Selection([
        ('table', '/'),
        ('manual', 'يدوي'),
        ('vibration', 'الاهتزاز'),
    ], string='طريقة دمك المكعبات', 
       help='طريقة دمك مكعبات الخرسانة أثناء الفحص')
    
    sample_type_id = fields.Many2one(
        'lab.sample.type',
        string='Sample Type',
        compute='_compute_sample_type_id',
        store=True,
        help='Sample type from the product template (soil, concrete, etc.) - helps filter appropriate templates'
    )
    enable_reserve_samples = fields.Boolean(
        related='stock_receipt_id.enable_reserve_samples',
        store=False, readonly=False,
        string='Enable Reserve Samples'
    )
    concrete_sample_subtype_id = fields.Many2one(
        related='stock_receipt_id.concrete_sample_subtype_id',
        store=False, readonly=False,
        string='Concrete Sample Subtype'
    )
    estimated_samples = fields.Integer(
        related='stock_receipt_id.estimated_samples',
        store=False, readonly=True,
        string='Estimated Samples'
    )
    estimated_cubes = fields.Integer(
        related='stock_receipt_id.estimated_cubes',
        store=False, readonly=True,
        string='Estimated Cubes'
    )
    enable_7_days_samples = fields.Boolean(
        related='stock_receipt_id.enable_7_days_samples',
        store=False, readonly=False,
        string='Enable 7 Days Samples'
    )
    seven_days_for_all_groups = fields.Boolean(
        related='stock_receipt_id.seven_days_for_all_groups',
        store=False, readonly=False,
        string='7 Days for All Groups'
    )
    reserve_for_all_groups = fields.Boolean(
        related='stock_receipt_id.reserve_for_all_groups',
        store=False, readonly=False,
        string='Reserve for All Groups'
    )
    is_signed = fields.Boolean(
        related='stock_receipt_id.is_signed',
        store=False, readonly=True,
        string='Is Signed'
    )
    sampling_notes = fields.Text(
        related='stock_receipt_id.sampling_notes',
        store=False, readonly=False,
        string='Sampling Notes'
    )
    auto_sample_generation = fields.Boolean(
        string='تفعيل الإنشاء الأوتوماتيكي للعينات',
        default=False,
        help='عند التفعيل: يتم إنشاء العينات تلقائياً حسب الكمية والنوع\nعند الإلغاء: يمكن إدخال العينات يدوياً'
    )
    move_lines_with_codes_count = fields.Integer(
        related='stock_receipt_id.move_lines_with_codes_count',
        store=False, readonly=True,
        string='Move Lines Count'
    )
    move_line_ids = fields.One2many(
        related='stock_receipt_id.move_line_ids',
        store=False, readonly=False,
        string='Move Lines'
    )
    has_concrete_product = fields.Boolean(
        string='Has Concrete Product',
        compute='_compute_has_concrete_product',
        store=False,
        help='Determines if task has any concrete product'
    )

    is_concrete_core_type_selected = fields.Boolean(
        string='Concrete Core Type Selected',
        compute='_compute_is_concrete_core_type_selected',
        store=False,
        help='True if the linked picking concrete sample type is CONCRETE_CORE'
    )

    core_compaction_ratio = fields.Float(
        string='نسبة الحدل (%)',
        help='النسبة المرجعية المطلوبة للحدل لعينة الكور الخرساني في الموقع (٪)'
    )

    # حقل مخصص للواجهة لتحديد إن كانت المهمة كور خرساني (نفس منطق الأيام/المكعبات)
    is_core_ui = fields.Boolean(
        string='Is Core UI',
        compute='_compute_is_core_ui',
        store=False
    )

    @api.depends('form_line_ids.product_id.product_tmpl_id.sample_type_id')
    def _compute_concrete_sample_type_from_product(self):
        """Compute concrete sample type from the form line products."""
        for task in self:
            concrete_sample_type = False
            for line in task.form_line_ids:
                if (line.product_id and 
                    line.product_id.product_tmpl_id.sample_type_id and 
                    'CONCRETE' in (line.product_id.product_tmpl_id.sample_type_id.code or '')):
                    concrete_sample_type = line.product_id.product_tmpl_id.sample_type_id
                    break
            task.concrete_sample_type_id = concrete_sample_type

    @api.depends('form_line_ids.sample_type_id')
    def _compute_has_concrete_product(self):
        """Check if task has any concrete type product."""
        for task in self:
            task.has_concrete_product = any(
                line.sample_type_id and 'CONCRETE' in (line.sample_type_id.code or '') 
                for line in task.form_line_ids
            )
    
    @api.depends('form_line_ids.product_id.product_tmpl_id.sample_type_id')
    def _compute_sample_type_id(self):
        """Compute sample type from the main product template"""
        for task in self:
            sample_type = False
            for line in task.form_line_ids:
                if line.product_id and line.product_id.product_tmpl_id.sample_type_id:
                    sample_type = line.product_id.product_tmpl_id.sample_type_id
                    break
            task.sample_type_id = sample_type

    def _create_stock_receipt(self):

        self.ensure_one()
        if not self.form_line_ids:
            return False
        

        if self.stock_receipt_id:
            return self.stock_receipt_id

        PickingType = self.env['stock.picking.type']
        picking_type = PickingType.search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        if not picking_type:
            raise UserError(_('No incoming operation type found for the current company.'))

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'partner_id': self.env.user.partner_id.id,
            'origin': self.name or _('Task %s') % self.id,
            'user_id': self.env.user.id,
        }
        picking = self.env['stock.picking'].create(picking_vals)

        Move = self.env['stock.move']
        for line in self.form_line_ids:
            vals = {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity or 1.0,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'company_id': self.env.company.id,
            }
            move = Move.create(vals)
            line.move_id = move

        picking.action_confirm()
        self.stock_receipt_id = picking
        return picking

    @api.depends('stock_receipt_id.concrete_sample_type_id')
    def _compute_is_concrete_core_type_selected(self):
        for task in self:
            code = (task.stock_receipt_id.concrete_sample_type_id.code or '').upper() if task.stock_receipt_id and task.stock_receipt_id.concrete_sample_type_id else ''
            task.is_concrete_core_type_selected = (code == 'CONCRETE_CORE')

    @api.depends('stock_receipt_id.concrete_sample_type_id', 'main_sample_is_concrete_core')
    def _compute_is_core_ui(self):
        for task in self:
            code = (task.stock_receipt_id.concrete_sample_type_id.code or '').upper() if task.stock_receipt_id and task.stock_receipt_id.concrete_sample_type_id else ''
            is_core = (code == 'CONCRETE_CORE') or bool(getattr(task, 'main_sample_is_concrete_core', False)) or bool(getattr(task, 'is_concrete_core_type_selected', False))
            task.is_core_ui = is_core

    def _ensure_moves_for_form_lines(self):

        for task in self.filtered(lambda t: t.stock_receipt_id):
            picking = task.stock_receipt_id
            Move = self.env['stock.move']
            new_lines = task.form_line_ids.filtered(lambda l: not l.move_id)
            
            for line in new_lines:

                existing_move = Move.search([
                    ('picking_id', '=', picking.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', 'not in', ['done', 'cancel'])
                ], limit=1)
                
                if existing_move:

                    line.move_id = existing_move

                    if existing_move.product_uom_qty != (line.quantity or 1.0):
                        existing_move.write({'product_uom_qty': line.quantity or 1.0})
                else:

                    move_vals = {
                        'name': line.product_id.display_name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity or 1.0,
                        'product_uom': line.product_id.uom_id.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'picking_id': picking.id,
                        'company_id': task.env.company.id,
                    }
                    move = Move.create(move_vals)
                    line.move_id = move

            if new_lines:
                picking.action_confirm()

            # بعد التأكيد، ضمن إنشاء سطور حركة لكل مجموعة لفحوص القير (ASPHALT)
            try:
                task._ensure_asphalt_groups_move_lines()
            except Exception:
                # لا نمنع الاستمرار إن فشل هذا الجزء
                pass

    def _ensure_service_sync(self):
        ServiceLine = self.env['fsm.task.service.line']
        for task in self:
            for line in task.service_line_ids:
                if line.quantity is not None:
                    ServiceLine.browse(line.id)._sync_sale_order_line()

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if task.form_line_ids and not task.stock_receipt_id:
                task._create_stock_receipt()
            else:
                task._ensure_moves_for_form_lines()
            task._ensure_service_sync()
        return tasks

    def write(self, vals):

        if 'move_line_ids' in vals:
            filtered_commands = []
            for command in vals['move_line_ids']:
                if isinstance(command, (list, tuple)) and len(command) >= 2 and command[0] == 2:
                    line_id = command[1]
                    move_line = self.env['stock.move.line'].browse(line_id)
                    if move_line.exists():
                        move_line.unlink()
                else:

                    filtered_commands.append(command)
            

            if filtered_commands:
                vals['move_line_ids'] = filtered_commands
            else:
                vals.pop('move_line_ids', None)
        
        res = super().write(vals)

        for task in self:
            if task.form_line_ids:
                if not task.stock_receipt_id:
                    task._create_stock_receipt()
                else:
                    task._ensure_moves_for_form_lines()
                task._ensure_service_sync()
            else:
                task._ensure_service_sync()
        return res

    # ======================== دعم توزيع مجموعات القير (ASPHALT) ========================
    def _is_asphalt_product(self, product):
        """تحقق إن كان المنتج يعود لعينة قير/أسفلت."""
        try:
            st_code = (product.product_tmpl_id.sample_type_id.code or '').upper() if product and product.product_tmpl_id and product.product_tmpl_id.sample_type_id else ''
            pcode = (product.default_code or '').upper() if product else ''
            pname = product.name or ''
            return ('ASPHALT' in st_code) or ('BITUMEN' in pcode) or ('قير' in pname)
        except Exception:
            return False

    def _ensure_asphalt_groups_move_lines(self):
        """للعينات من نوع القير: أنشئ سطر حركة لكل مجموعة (1..total_samples_count)،
        مع تعيين group_no فريداً، دون التأثير على الأنواع الأخرى."""
        for task in self.filtered(lambda t: t.stock_receipt_id):
            picking = task.stock_receipt_id
            total_groups = 0
            try:
                total_groups = int(task.total_samples_count or 0)
            except Exception:
                total_groups = 0
            total_groups = max(1, total_groups)

            for form_line in task.form_line_ids:
                product = form_line.product_id
                if not product or not self._is_asphalt_product(product):
                    continue

                # ابحث عن الحركة الخاصة بهذا المنتج
                move = self.env['stock.move'].search([
                    ('picking_id', '=', picking.id),
                    ('product_id', '=', product.id),
                    ('state', 'not in', ['done', 'cancel'])
                ], limit=1)
                if not move:
                    continue

                existing_lines = move.move_line_ids
                used_groups = set([ln.group_no for ln in existing_lines if ln.group_no])

                # أعطِ group_no لأي سطر بلا قيمة حالياً
                next_no = 1
                for ln in existing_lines:
                    if not ln.group_no:
                        while next_no in used_groups:
                            next_no += 1
                        ln.group_no = next_no
                        used_groups.add(next_no)
                        next_no += 1

                # أنشئ السطور الناقصة حتى نصل إلى total_groups
                for g in range(1, total_groups + 1):
                    if g in used_groups:
                        continue
                    vals = {
                        'move_id': move.id,
                        'picking_id': picking.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id if move.product_uom else (move.product_id.uom_id.id if move.product_id and move.product_id.uom_id else self.env.ref('uom.product_uom_unit').id),
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'qty_done': 1.0,
                        'sample_quantity': 1,
                        'group_no': g,
                    }
                    self.env['stock.move.line'].create(vals)
                    used_groups.add(g)

                # حدّث كمية الطلب في الحركة لتساوي مجموع qty_done
                total_qty_done = sum(move.move_line_ids.mapped('qty_done')) or 0
                if total_qty_done > 0 and move.product_uom_qty != total_qty_done:
                    move.write({'product_uom_qty': total_qty_done})

    def action_open_concrete_sampling(self):
        self.ensure_one()
        if not self.stock_receipt_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Concrete Sampling'),
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.stock_receipt_id.id,
            'context': {
                'default_picking_type_id': self.stock_receipt_id.picking_type_id.id,
                'concrete_sample_domain': [('code', 'ilike', 'CONCRETE')],
            },
        }
        
    def action_recalculate_samples(self):
        self.ensure_one()
        
        if not self.auto_sample_generation:
            raise UserError(_('الإنشاء الأوتوماتيكي للعينات غير مفعل. يرجى تفعيله أولاً أو إضافة العينات يدوياً.'))
        
        if self.stock_receipt_id:
            self.stock_receipt_id.action_recalculate_samples()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return False
        
    def unlink_move_line(self, line_id):
        self.ensure_one()
        if self.stock_receipt_id:
            move_line = self.env['stock.move.line'].browse(line_id)
            if move_line.picking_id == self.stock_receipt_id:
                return move_line.unlink()
        return False
    
    def action_add_manual_sample(self):
        """إضافة عينة واحدة يدوياً"""
        self.ensure_one()
        
        if self.auto_sample_generation:
            raise UserError(_('الإنشاء الأوتوماتيكي مفعل. يرجى إلغاء تفعيله لإضافة العينات يدوياً.'))
        
        if not self.stock_receipt_id:

            picking_vals = {
                'name': f'Samples - {self.name}',
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'location_id': self.env.ref('stock.stock_location_stock').id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                'origin': self.name,
            }
            self.stock_receipt_id = self.env['stock.picking'].create(picking_vals)
        
        existing_groups = self.move_line_ids.mapped('group_no')
        next_group = max(existing_groups) + 1 if existing_groups else 1
        
        if not self.stock_receipt_id.move_ids:

            product = self.env['product.product'].search([('name', 'ilike', 'خرسانة')], limit=1)
            if not product:
                product = self.env['product.product'].browse(1) 
            

            product_uom = product.uom_id if product.uom_id else self.env.ref('uom.product_uom_unit')
            
            move_vals = {
                'name': 'Manual Sample',
                'picking_id': self.stock_receipt_id.id,
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product_uom.id,
                'location_id': self.stock_receipt_id.location_id.id,
                'location_dest_id': self.stock_receipt_id.location_dest_id.id,
            }
            move = self.env['stock.move'].create(move_vals)
        else:
            move = self.stock_receipt_id.move_ids[0]

            if not move.product_uom:
                move.product_uom = move.product_id.uom_id if move.product_id.uom_id else self.env.ref('uom.product_uom_unit')
        
        # تحديد ما إذا كانت العينة الرئيسية من نوع كور خرساني لتخصيص الافتراضيات
        is_concrete_core = False
        try:
            # يعتمد على الحقل المحسوب في fsm_task_form_line.ProjectTask
            is_concrete_core = bool(self.main_sample_is_concrete_core)
        except Exception:
            # احتياط: فحص نوع المنتج في الحركة إن وجد
            try:
                prod = move.product_id
                st_code = (prod.product_tmpl_id.sample_type_id.code or '').upper() if prod else ''
                is_concrete_core = (st_code == 'CONCRETE_CORE')
            except Exception:
                is_concrete_core = False

        cube_count = 2 if is_concrete_core else 3 
        line_vals = {
            'move_id': move.id,
            'picking_id': self.stock_receipt_id.id,
            'product_id': move.product_id.id,
            'product_uom_id': move.product_uom.id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'qty_done': float(cube_count), 
            'group_no': next_group,
            'field_code': '',
            'field_serial': '',
            'age_days': False if is_concrete_core else '28',
            'sample_quantity': cube_count,
            'cube_count': cube_count,
        }
        self.env['stock.move.line'].create(line_vals)
        
        self._update_move_demand_quantity()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _update_move_demand_quantity(self):
        """تحديث الكمية المطلوبة في الحركة لتتطابق مع الكميات المنجزة"""
        self.ensure_one()
        if self.stock_receipt_id and self.stock_receipt_id.move_ids:
            for move in self.stock_receipt_id.move_ids:
                total_qty_done = sum(move.move_line_ids.mapped('qty_done'))
                if total_qty_done > 0 and move.product_uom_qty != total_qty_done:
                    move.write({'product_uom_qty': total_qty_done})

    def action_generate_codes(self):
        """دالة معطلة - الرموز الحقلية يدخلها الموضف بنفسه"""
        self.ensure_one()
        raise UserError(_('توليد الرموز الحقلية معطل. يرجى إدخال الرموز يدوياً في الحقول المخصصة.'))
    
    def action_clear_samples(self):
        """حذف جميع العينات الموجودة"""
        self.ensure_one()
        
        if self.move_line_ids:
            self.move_line_ids.unlink()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        
    def action_generate_samples(self):
        """Generate samples for concrete sampling."""
        self.ensure_one()
        if self.stock_receipt_id:
            self.stock_receipt_id.action_generate_samples()
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        return False 
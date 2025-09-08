# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLineFieldCode(models.Model):
    _inherit = 'stock.move.line'

    field_code = fields.Char(
        string='الرمز المختبري', 
        copy=False,
        help='يمكن كتابة الرمز فقط بعد التوقيع على الطلبية'
    )
    
    field_serial = fields.Char(
        string='الرمز الحقلي',
        copy=False,
        help='الرمز الحقلي للعينة - يتم إضافة رقم عرض السعر تلقائياً'
    )
    
    sample_quantity = fields.Float(
        string='كمية العينة',
        default=0.0,
        help='عدد العينات في هذا السطر'
    )
    
    age_days = fields.Selection([
        ('7', '7 أيام'),
        ('28', '28 يوم'),
        ('reserve', 'احتياط')
    ], string='عمر المكعبات', default='28', 
       help='عمر المكعبات بالأيام')
    
    cube_count = fields.Integer(
        string='عدد المكعبات',
        default=3,
        help='عدد المكعبات لهذا العمر'
    )
    
    seven_day_cubes = fields.Integer(
        string='مكعبات 7 أيام',
        default=0,
        help='عدد مكعبات الاختبار ذات عمر 7 أيام'
    )

    twenty_eight_day_cubes = fields.Integer(
        string='مكعبات 28 يوم',
        default=0,
        help='عدد مكعبات الاختبار ذات عمر 28 يوم (تشمل المكعبات الأساسية)'
    )

    total_cubes = fields.Integer(
        string='إجمالي المكعبات',
        compute='_compute_total_cubes',
        store=True,
        help='إجمالي المكعبات في هذا السطر'
    )
    
    group_no = fields.Integer(
        string='رقم المجموعة',
        help='رقم المجموعة'
    )
    
    is_signed = fields.Boolean(
        string='Is Signed',
        related='picking_id.is_signed',
        store=False, readonly=True,
        help='Whether the picking is signed electronically'
    )

    @api.depends('seven_day_cubes', 'twenty_eight_day_cubes', 'cube_count')
    def _compute_total_cubes(self):
        """حساب إجمالي المكعبات تلقائياً"""
        for rec in self:
            if rec.cube_count > 0:
                rec.total_cubes = rec.cube_count
                if rec.age_days == '7':
                    rec.seven_day_cubes = rec.cube_count
                    rec.twenty_eight_day_cubes = 0
                elif rec.age_days == '28':
                    rec.twenty_eight_day_cubes = rec.cube_count
                    rec.seven_day_cubes = 0
            else:
                rec.total_cubes = (rec.seven_day_cubes or 0) + (rec.twenty_eight_day_cubes or 0)
                if rec.seven_day_cubes > 0 and rec.twenty_eight_day_cubes == 0:
                    rec.age_days = '7'
                    rec.cube_count = rec.seven_day_cubes
                elif rec.twenty_eight_day_cubes > 0 and rec.seven_day_cubes == 0:
                    rec.age_days = '28'
                    rec.cube_count = rec.twenty_eight_day_cubes
    
    @api.onchange('age_days')
    def _onchange_age_days_auto_cube_count(self):
        """تعيين عدد المكعبات تلقائياً بناءً على عدد الأيام: 28 يوم = 3 مكعبات، غير ذلك = 1 مكعب"""
        for rec in self:
            if rec.age_days == '28':
                rec.cube_count = 3
            elif rec.age_days in ['7', 'reserve']:
                rec.cube_count = 1
    
    @api.onchange('age_days', 'cube_count')
    def _onchange_age_days_cube_count(self):
        """تحديث الحقول القديمة عند تغيير الحقول الجديدة ومزامنة كمية المخزون"""
        for rec in self:
            if rec.age_days == '7':
                rec.seven_day_cubes = rec.cube_count
                rec.twenty_eight_day_cubes = 0
            elif rec.age_days == '28':
                rec.twenty_eight_day_cubes = rec.cube_count
                rec.seven_day_cubes = 0
            

            if rec.cube_count and rec.cube_count > 0:
                rec.qty_done = float(rec.cube_count)
                rec.sample_quantity = rec.cube_count
    
    @api.onchange('seven_day_cubes', 'twenty_eight_day_cubes')
    def _onchange_old_cube_fields(self):
        """تحديث الحقول الجديدة عند تغيير الحقول القديمة ومزامنة كمية المخزون"""
        for rec in self:
            if rec.seven_day_cubes > 0 and rec.twenty_eight_day_cubes == 0:
                rec.age_days = '7'
                rec.cube_count = rec.seven_day_cubes
                rec.qty_done = float(rec.seven_day_cubes)
                rec.sample_quantity = rec.seven_day_cubes
            elif rec.twenty_eight_day_cubes > 0 and rec.seven_day_cubes == 0:
                rec.age_days = '28'
                rec.cube_count = rec.twenty_eight_day_cubes
                rec.qty_done = float(rec.twenty_eight_day_cubes)
                rec.sample_quantity = rec.twenty_eight_day_cubes
    
    is_picking_signed = fields.Boolean(
        string='تم التوقيع على الطلبية',
        related='picking_id.is_signed',
        store=True
    )

    @api.model
    def default_get(self, fields_list):
        """تعيين افتراضيات ديناميكية عند إنشاء سطر جديد من واجهة المهمة:
        • إذا كان نوع العينة كور خرساني ⇒ age_days = False، cube_count = 2، مع مزامنة الكميات.
        """
        res = super().default_get(fields_list)
        try:
            # الحصول على picking من الـ context أو من القيم الافتراضية
            picking_id = self.env.context.get('default_picking_id') or res.get('picking_id')
            if not picking_id and res.get('move_id'):
                move = self.env['stock.move'].browse(res['move_id'])
                if move.exists():
                    picking_id = move.picking_id.id

            is_concrete_core = False
            if picking_id:
                picking = self.env['stock.picking'].browse(picking_id)
                if picking and picking.concrete_sample_type_id and (picking.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                    is_concrete_core = True
                if not is_concrete_core:
                    # احتياط: اكتشاف من المهمة المرتبطة بالـ picking
                    task = self.env['project.task'].search([('stock_receipt_id', '=', picking_id)], limit=1)
                    if task and (task.main_sample_is_concrete_core or getattr(task, 'is_concrete_core_type_selected', False)):
                        is_concrete_core = True

            if is_concrete_core:
                # فرض القيم بغض النظر عن fields_list لضمان ظهورها في محرر القوائم
                res['age_days'] = False
                res['cube_count'] = 2
                if not res.get('qty_done'):
                    res['qty_done'] = 2.0
                if not res.get('sample_quantity'):
                    res['sample_quantity'] = 2
        except Exception:
            # لا نمنع إنشاء السجل عند حدوث أي خطأ
            pass
        return res

    @api.onchange('picking_id')
    def _onchange_picking_id_apply_core_defaults(self):
        """عند ضبط/تغيير الـ picking في السطر، طبق افتراضيات الكور إن لزم.
        لا تتجاوز تعديلات المستخدم إن كانت موجودة مسبقاً.
        """
        for rec in self:
            try:
                is_core = False
                picking = rec.picking_id
                if picking and picking.concrete_sample_type_id and (picking.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                    is_core = True
                if not is_core and picking:
                    task = self.env['project.task'].search([('stock_receipt_id', '=', picking.id)], limit=1)
                    if task and (task.main_sample_is_concrete_core or getattr(task, 'is_concrete_core_type_selected', False)):
                        is_core = True

                if is_core:
                    if rec.age_days in (False, '28'):
                        rec.age_days = False
                    if not rec.cube_count or rec.cube_count == 3:
                        rec.cube_count = 2
                    if not rec.qty_done:
                        rec.qty_done = float(rec.cube_count)
                    if not rec.sample_quantity:
                        rec.sample_quantity = rec.cube_count
            except Exception:
                continue



    @api.constrains('field_code', 'company_id')
    def _check_unique_lab_code(self):
        """يمنع التكرار إذا كان الإعداد لا يسمح بذلك."""
        allow_duplicates = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.allow_lab_code_duplicates', 'False') == 'True'
        if allow_duplicates:
            return
        for rec in self:
            if rec.field_code:
                domain = [
                    ('field_code', '=', rec.field_code),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain):
                    raise ValidationError(_('لا يمكن تكرار الرمز المختبري داخل نفس الشركة.'))

    def _generate_lab_code(self):
        """توليد رمز مختبري جديد"""
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'appointment_products.lab_code')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Lab Code',
                'code': 'appointment_products.lab_code',
                'implementation': 'no_gap',
                'prefix': 'LC',
                'padding': 5,
                'company_id': self.env.company.id,
            })
        return seq.next_by_id()
    
    def _should_auto_generate_codes(self):
        """تحديد ما إذا كان يجب توليد الرموز تلقائياً"""
        auto_field_code = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.auto_field_code_on_creation', 'False') == 'True'
        auto_lab_code = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.auto_generate_lab_code', 'False') == 'True'
        return auto_field_code, auto_lab_code

    def _generate_field_serial(self):
        """إنشاء رقم تسلسلي للرمز الحقلي مع إضافة رقم عرض السعر تلقائياً"""
        seq = self.env['ir.sequence'].sudo().search([('code', '=', 'appointment_products.field_serial')], limit=1)
        if not seq:
            seq = self.env['ir.sequence'].sudo().create({
                'name': 'Field Serial',
                'code': 'appointment_products.field_serial',
                'implementation': 'no_gap',
                'prefix': 'FC',
                'padding': 5,
                'company_id': self.env.company.id,
            })
        
        base_serial = seq.next_by_id()
        
        # إضافة رقم عرض السعر تلقائياً إذا كان متوفراً
        sale_order_name = self._get_related_sale_order_name()
        if sale_order_name:
            return f"{sale_order_name}/{base_serial}"
        
        return base_serial

    @api.onchange('field_code')
    def _onchange_field_code(self):
        """التحقق من التوقيع قبل السماح بكتابة الرمز"""
        if self.field_code and not self.is_picking_signed:
            self.field_code = False

    @api.onchange('group_no')
    def _onchange_group_no(self):
        """تلقائياً تعيين نفس الرمز الحقلي للمجموعة نفسها أو توليد رمز جديد"""
        if self.group_no and self.picking_id:
            # البحث عن سطر آخر في نفس الطلبية بنفس رقم المجموعة
            existing_line = self.picking_id.move_line_ids.filtered(
                lambda l: l.group_no == self.group_no and l.field_serial and l.id != self.id
            )
            
            if existing_line:
                # استخدام الرمز الحقلي الموجود
                self.field_serial = existing_line[0].field_serial
                self.lot_name = self.field_serial
            else:
                # توليد رمز حقلي جديد للمجموعة
                auto_field_code, auto_lab_code = self._should_auto_generate_codes()
                if auto_field_code and not self.field_serial:
                    self.field_serial = self._generate_field_serial()
                    self.lot_name = self.field_serial

    @api.onchange('field_serial')
    def _onchange_field_serial(self):
        """تحديث الرمز الحقلي بإضافة رقم عرض السعر إذا لم يكن موجوداً"""
        if self.field_serial and not self._context.get('skip_field_serial_update'):
            sale_order_name = self._get_related_sale_order_name()
            if sale_order_name:
                if not self.field_serial.startswith(sale_order_name + '/'):
                    parts = self.field_serial.split('/')
                    if len(parts) > 1:
                        user_code = parts[-1]
                    else:
                        user_code = self.field_serial
                    
                    self.field_serial = sale_order_name + '/' + user_code
                    self.lot_name = self.field_serial

    def _get_related_sale_order_name(self):
        """الحصول على رقم عرض السعر المرتبط بهذه الحركة"""
        self.ensure_one()
        origin = None
        if self.picking_id and self.picking_id.origin:
            origin = self.picking_id.origin
        elif self.move_id and self.move_id.origin:
            origin = self.move_id.origin
        
        if origin:
            parts = origin.split(' - ')
            if len(parts) > 1:

                first_part = parts[0].strip()
                if first_part and (first_part[0].isalpha() and any(c.isdigit() for c in first_part)):
                    return first_part
            
            return origin
        
        return None
    
    @api.model
    def _ensure_required_fields(self, vals):
        """ضمان وجود الحقول المطلوبة للعينات اليدوية"""

        if not vals.get('move_id') and vals.get('picking_id'):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            if picking.exists():
                if picking.move_ids:

                    vals['move_id'] = picking.move_ids[0].id
                else:

                    product = self.env['product.product'].search([('name', 'ilike', 'خرسانة')], limit=1)
                    if not product:
                        product = self.env['product.product'].browse(1)  # منتج افتراضي
                    
                    move_vals = {
                        'name': 'Manual Sample',
                        'picking_id': picking.id,
                        'product_id': product.id,
                        'product_uom_qty': 1,
                        'product_uom': product.uom_id.id if product.uom_id else self.env.ref('uom.product_uom_unit').id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': picking.location_dest_id.id,
                    }
                    move = self.env['stock.move'].create(move_vals)
                    vals['move_id'] = move.id
        
        if not vals.get('product_id') and vals.get('move_id'):
            move = self.env['stock.move'].browse(vals['move_id'])
            if move.exists():
                vals['product_id'] = move.product_id.id
            
        if not vals.get('product_uom_id'):
            if vals.get('move_id'):
                move = self.env['stock.move'].browse(vals['move_id'])
                if move.exists() and move.product_uom:
                    vals['product_uom_id'] = move.product_uom.id
                elif vals.get('product_id'):
                    product = self.env['product.product'].browse(vals['product_id'])
                    if product.exists() and product.uom_id:
                        vals['product_uom_id'] = product.uom_id.id
            
            if not vals.get('product_uom_id'):
                vals['product_uom_id'] = self.env.ref('uom.product_uom_unit').id
        
        if not vals.get('location_id') or not vals.get('location_dest_id'):
            if vals.get('picking_id'):
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                if picking.exists():
                    vals['location_id'] = picking.location_id.id
                    vals['location_dest_id'] = picking.location_dest_id.id
            elif vals.get('move_id'):
                move = self.env['stock.move'].browse(vals['move_id'])
                if move.exists():
                    vals['location_id'] = move.location_id.id
                    vals['location_dest_id'] = move.location_dest_id.id
        
        if not vals.get('qty_done'):
            vals['qty_done'] = 1.0   
        
        return vals
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء السجل مع معالجة الرموز بناءً على الإعدادات"""
        
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        auto_field_code, auto_lab_code = self._should_auto_generate_codes()
        
        for vals in vals_list:
            self._ensure_required_fields(vals)
            
            # تخصيص افتراضيات عينات كور الخرسانة فقط (CONCRETE_CORE)
            # الهدف:
            # - جعل العمر (age_days) فارغاً بدل 28 يوماً
            # - جعل عدد المكعبات الافتراضي 2
            # - مزامنة qty_done و sample_quantity مع عدد المكعبات
            try:
                is_concrete_core = False
                # 1) التحقق من الـ picking المرتبط (أوثق مصدر)
                picking_id = vals.get('picking_id')
                if not picking_id and vals.get('move_id'):
                    mv = self.env['stock.move'].browse(vals['move_id'])
                    if mv.exists():
                        picking_id = mv.picking_id.id
                if picking_id:
                    pk = self.env['stock.picking'].browse(picking_id)
                    if pk and pk.concrete_sample_type_id and (pk.concrete_sample_type_id.code or '').upper() == 'CONCRETE_CORE':
                        is_concrete_core = True
                # 2) احتياط: التحقق من المنتج المرتبط
                if not is_concrete_core:
                    product_id = vals.get('product_id')
                    if product_id:
                        prod = self.env['product.product'].browse(product_id)
                        st_code = (prod.product_tmpl_id.sample_type_id.code or '').upper()
                        is_concrete_core = (st_code == 'CONCRETE_CORE')
                # 3) احتياط إضافي: من الحركة
                if not is_concrete_core and vals.get('move_id'):
                    move = self.env['stock.move'].browse(vals['move_id'])
                    if move.exists() and move.product_id:
                        st_code = (move.product_id.product_tmpl_id.sample_type_id.code or '').upper()
                        is_concrete_core = (st_code == 'CONCRETE_CORE')

                if is_concrete_core:
                    # تفريغ العمر إذا كان محتوياً على القيمة الافتراضية أو غير موجود في vals
                    if 'age_days' not in vals or vals.get('age_days') == '28':
                        vals['age_days'] = False
                    # ضبط عدد المكعبات الافتراضي إلى 2 إن لم يُحدد أو كان 3 (الافتراضي الحالي)
                    if not vals.get('cube_count') or vals.get('cube_count') == 3:
                        vals['cube_count'] = 2
                    # مزامنة الكميات مع عدد المكعبات لكي يظهر مباشرة في الواجهة
                    if not vals.get('qty_done'):
                        vals['qty_done'] = float(vals['cube_count'])
                    if not vals.get('sample_quantity'):
                        vals['sample_quantity'] = vals['cube_count']
            except Exception:
                # في حال حدوث أي خطأ، لا نمنع إنشاء السجل
                pass
            
            # تعيين عدد المكعبات تلقائياً بناءً على age_days إذا لم يتم تحديد cube_count
            if vals.get('age_days') and not vals.get('cube_count'):
                if vals['age_days'] == '28':
                    vals['cube_count'] = 3
                elif vals['age_days'] in ['7', 'reserve']:
                    vals['cube_count'] = 1
            
            # معالجة الرمز الحقلي بناءً على رقم المجموعة
            if auto_field_code and not vals.get('field_serial') and vals.get('picking_id'):
                group_no = vals.get('group_no')
                picking_id = vals.get('picking_id')
                
                if group_no and picking_id:
                    # البحث عن سطر آخر بنفس رقم المجموعة
                    existing_lines = self.env['stock.move.line'].search([
                        ('picking_id', '=', picking_id),
                        ('group_no', '=', group_no),
                        ('field_serial', '!=', False)
                    ], limit=1)
                    
                    if existing_lines:
                        # استخدام الرمز الحقلي الموجود لنفس المجموعة
                        vals['field_serial'] = existing_lines.field_serial
                    else:
                        # توليد رمز حقلي جديد للمجموعة
                        temp_record = self.env['stock.move.line'].new(vals)
                        vals['field_serial'] = temp_record._generate_field_serial()
                else:
                    # توليد رمز حقلي عادي إذا لم يكن هناك رقم مجموعة
                    temp_record = self.env['stock.move.line'].new(vals)
                    vals['field_serial'] = temp_record._generate_field_serial()
            
            picking = self.env['stock.picking'].browse(vals.get('picking_id'))
            if auto_lab_code and not vals.get('field_code') and picking:
                if picking.is_signed:
                    vals['field_code'] = self.env['stock.move.line']._generate_lab_code()
            
            # تعيين lot_name إذا وجد field_serial
            if vals.get('field_serial') and not vals.get('lot_name'):
                vals['lot_name'] = vals['field_serial']
        
        return super().create(vals_list)
    
    def write(self, vals):
        """تحديث السجل مع معالجة الرموز بناءً على الإعدادات"""
        

        allow_update = self.env.context.get('allow_signed_update', False)
        
        if not allow_update:
            protected_fields = ['field_code', 'field_serial', 'age_days', 'cube_count', 'group_no']
            for record in self:
                if record.is_signed:
                    for field in protected_fields:
                        if field in vals:
                            current_value = getattr(record, field, None)
                            new_value = vals[field]
                            
                            if current_value != new_value:
                                raise ValidationError(_(
                                    'لا يمكن تعديل حقل "%s" بعد التوقيع الإلكتروني على حركة المخزون.'
                                ) % self.env[self._name]._fields[field].string)
        
        auto_field_code, auto_lab_code = self._should_auto_generate_codes()
        prevent_edit = self.env['ir.config_parameter'].sudo().get_param(
            'appointment_products.prevent_edit_lab_code', 'False') == 'True'
        

        if 'field_code' in vals:
            for record in self:
                if vals['field_code'] and not record.is_picking_signed:
                    vals['field_code'] = False
                
                if prevent_edit and record.field_code and vals['field_code'] != record.field_code:
                    raise ValidationError(_('لا يمكن تعديل الرمز المختبري بعد إنشائه.'))

        if 'field_serial' in vals and vals['field_serial'] and not self._context.get('skip_field_serial_update'):
            for record in self:
                sale_order_name = record._get_related_sale_order_name()
                if sale_order_name:
                    if not vals['field_serial'].startswith(sale_order_name + '/'):
                        parts = vals['field_serial'].split('/')
                        if len(parts) > 1:
                            user_code = parts[-1]
                        else:
                            user_code = vals['field_serial']
                        
                        vals['field_serial'] = sale_order_name + '/' + user_code

        if 'field_serial' in vals and vals['field_serial'] and 'lot_name' not in vals:
            vals['lot_name'] = vals['field_serial']

        res = super().write(vals)


        if 'cube_count' in vals or 'seven_day_cubes' in vals or 'twenty_eight_day_cubes' in vals:
            for record in self:
                if record.cube_count and record.cube_count > 0:

                    super(StockMoveLineFieldCode, record).write({
                        'qty_done': float(record.cube_count),
                        'sample_quantity': record.cube_count
                    })
                elif record.seven_day_cubes > 0:
                    super(StockMoveLineFieldCode, record).write({
                        'qty_done': float(record.seven_day_cubes),
                        'sample_quantity': record.seven_day_cubes
                    })
                elif record.twenty_eight_day_cubes > 0:
                    super(StockMoveLineFieldCode, record).write({
                        'qty_done': float(record.twenty_eight_day_cubes),
                        'sample_quantity': record.twenty_eight_day_cubes
                    })

        try:
            if auto_field_code:
                for rec in self:
                    if not rec.field_serial:
                        rec.with_context(skip_field_serial_update=True).field_serial = rec._generate_field_serial()

            if auto_lab_code:
                for rec in self:
                    if not rec.field_code and rec.is_picking_signed:
                        rec.with_context(allow_signed_update=True).write({
                            'field_code': rec._generate_lab_code()
                        })
        except Exception:
            pass

        return res 
    
    def unlink(self):
        """منع حذف خطوط العينات بعد التوقيع الإلكتروني فقط"""
        for record in self:
            if record.is_signed:
                raise ValidationError(_(
                    'لا يمكن حذف خطوط العينات بعد التوقيع الإلكتروني على حركة المخزون.'
                ))
        
        return super().unlink()
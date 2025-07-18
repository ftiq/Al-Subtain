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
    ], string='عمر المكعبات', default='28', help='عمر المكعبات بالأيام')
    
    cube_count = fields.Integer(
        string='عدد المكعبات',
        default=0,
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
    
    @api.onchange('age_days', 'cube_count')
    def _onchange_age_days_cube_count(self):
        """تحديث الحقول القديمة عند تغيير الحقول الجديدة"""
        for rec in self:
            if rec.age_days == '7':
                rec.seven_day_cubes = rec.cube_count
                rec.twenty_eight_day_cubes = 0
            elif rec.age_days == '28':
                rec.twenty_eight_day_cubes = rec.cube_count
                rec.seven_day_cubes = 0
    
    @api.onchange('seven_day_cubes', 'twenty_eight_day_cubes')
    def _onchange_old_cube_fields(self):
        """تحديث الحقول الجديدة عند تغيير الحقول القديمة"""
        for rec in self:
            if rec.seven_day_cubes > 0 and rec.twenty_eight_day_cubes == 0:
                rec.age_days = '7'
                rec.cube_count = rec.seven_day_cubes
            elif rec.twenty_eight_day_cubes > 0 and rec.seven_day_cubes == 0:
                rec.age_days = '28'
                rec.cube_count = rec.twenty_eight_day_cubes
    
    is_picking_signed = fields.Boolean(
        string='تم التوقيع على الطلبية',
        related='picking_id.is_signed',
        store=True
    )

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
        """إنشاء رقم تسلسلي للرمز الحقلي"""
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
        return seq.next_by_id()

    @api.onchange('field_code')
    def _onchange_field_code(self):
        """التحقق من التوقيع قبل السماح بكتابة الرمز"""
        if self.field_code and not self.is_picking_signed:
            self.field_code = False

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
        if self.picking_id and self.picking_id.origin:
            task = self.env['project.task'].search([
                ('stock_receipt_id', '=', self.picking_id.id)
            ], limit=1)
            
            if task and task.sale_order_id:
                return task.sale_order_id.name
        
        return None
    
    @api.model_create_multi
    def create(self, vals_list):
        """إنشاء السجل مع معالجة الرموز بناءً على الإعدادات"""
        auto_field_code, auto_lab_code = self._should_auto_generate_codes()
        
        for vals in vals_list:
            if vals.get('field_code'):
                picking = self.env['stock.picking'].browse(vals.get('picking_id'))
                if picking and not picking.is_signed:
                    vals['field_code'] = False
            elif vals.get('picking_id') and auto_lab_code:
                picking = self.env['stock.picking'].browse(vals['picking_id'])
                if picking.is_signed:
                    vals['field_code'] = self._generate_lab_code()
            

            if auto_field_code and vals.get('picking_id'):
                if not vals.get('field_serial'):
                    vals['field_serial'] = self._generate_field_serial()
                    

            if vals.get('field_serial') and not vals.get('lot_name'):
                vals['lot_name'] = vals['field_serial']
        
        return super().create(vals_list)
    
    def write(self, vals):
        """تحديث السجل مع معالجة الرموز بناءً على الإعدادات"""
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


        try:
            if auto_field_code:
                for rec in self:
                    if not rec.field_serial:
                        rec.with_context(skip_field_serial_update=True).field_serial = rec._generate_field_serial()

            if auto_lab_code:
                for rec in self:
                    if not rec.field_code and rec.is_picking_signed:
                        rec.field_code = rec._generate_lab_code()
        except Exception:
            pass

        return res 
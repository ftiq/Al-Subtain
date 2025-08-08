# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    partner_phone = fields.Char(
        string='هاتف العميل',
        related='partner_id.phone',
        readonly=True,
        store=False
    )
    
    partner_email = fields.Char(
        string='بريد العميل',
        related='partner_id.email', 
        readonly=True,
        store=False
    )
    

    products_info = fields.Json(
        string='معلومات المنتجات',
        compute='_compute_products_info',
        store=False
    )
    
    currency_symbol = fields.Char(
        string='رمز العملة',
        related='currency_id.symbol',
        readonly=True,
        store=False
    )
    
    currency_name = fields.Char(
        string='اسم العملة',
        related='currency_id.name', 
        readonly=True,
        store=False
    )
    

    fsm_tasks_info = fields.Json(
        string='معلومات مهام الخدمة الميدانية',
        compute='_compute_fsm_tasks_info',
        store=False
    )
    
    fsm_tasks_count = fields.Integer(
        string='عدد مهام الخدمة الميدانية',
        compute='_compute_fsm_tasks_info',
        store=False
    )
    

    lab_samples_info = fields.Json(
        string='معلومات عينات الفحص',
        compute='_compute_lab_samples_info',
        store=False
    )
    
    lab_samples_count = fields.Integer(
        string='عدد عينات الفحص',
        compute='_compute_lab_samples_info',
        store=False
    )

    @api.depends('order_line.product_id', 'order_line.product_uom_qty', 'currency_id')
    def _compute_products_info(self):
        """حساب معلومات المنتجات لعرضها في الـ widget"""
        for order in self:
            products = []
            currency_symbol = order.currency_id.symbol if order.currency_id else ''
            for line in order.order_line.filtered(lambda l: l.product_id and l.display_type in (False, 'product')):
                products.append({
                    'name': line.product_id.name,
                    'qty': line.product_uom_qty,
                    'uom': line.product_uom.name if line.product_uom else '',
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                    'currency_symbol': currency_symbol,
                    'currency_name': order.currency_id.name if order.currency_id else '',
                })
            order.products_info = products
    
    def _compute_fsm_tasks_info(self):
        """حساب معلومات مهام الخدمة الميدانية المرتبطة بعرض السعر"""
        for order in self:
            tasks_info = []
            tasks_count = 0
            
            if hasattr(order, 'tasks_ids'):
                fsm_tasks = order.tasks_ids.filtered(lambda t: t.is_fsm)
                for task in fsm_tasks:
                    tasks_info.append({
                        'id': task.id,
                        'name': task.name,
                        'state': task.state,
                        'state_text': self._get_task_state_text(task.state),
                        'user_id': task.user_ids[0].name if task.user_ids else 'غير محدد',
                        'partner_id': task.partner_id.name if task.partner_id else 'غير محدد',
                        'project_name': task.project_id.name if task.project_id else 'غير محدد',
                        'planned_date_begin': task.planned_date_begin.strftime('%Y-%m-%d %H:%M') if task.planned_date_begin else 'غير محدد',
                        'date_deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else 'غير محدد',
                        'fsm_done': task.fsm_done if hasattr(task, 'fsm_done') else False,
                        'priority': task.priority,
                        'description': task.description or '',
                    })
                tasks_count += len(fsm_tasks)
            

            try:

                if order.partner_id:
                    helpdesk_tickets = self.env['helpdesk.ticket'].search([
                        ('partner_id', '=', order.partner_id.id),
                        ('sale_order_id', '=', order.id) if 'sale_order_id' in self.env['helpdesk.ticket']._fields else ('id', '!=', 0)
                    ])
                    
                    for ticket in helpdesk_tickets:
                        if hasattr(ticket, 'fsm_task_ids'):
                            for task in ticket.fsm_task_ids:
                                tasks_info.append({
                                    'id': task.id,
                                    'name': task.name,
                                    'state': task.state,
                                    'state_text': self._get_task_state_text(task.state),
                                    'user_id': task.user_ids[0].name if task.user_ids else 'غير محدد',
                                    'partner_id': task.partner_id.name if task.partner_id else 'غير محدد',
                                    'project_name': task.project_id.name if task.project_id else 'غير محدد',
                                    'planned_date_begin': task.planned_date_begin.strftime('%Y-%m-%d %H:%M') if task.planned_date_begin else 'غير محدد',
                                    'date_deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else 'غير محدد',
                                    'fsm_done': task.fsm_done if hasattr(task, 'fsm_done') else False,
                                    'priority': task.priority,
                                    'description': task.description or '',
                                    'helpdesk_ticket': ticket.name,
                                })
                            tasks_count += len(ticket.fsm_task_ids)
            except Exception:

                pass
            
            order.fsm_tasks_info = tasks_info
            order.fsm_tasks_count = tasks_count
    
    def _get_task_state_text(self, state):
        """تحويل حالة المهمة إلى نص عربي"""
        state_map = {
            '01_in_progress': 'جارية',
            '02_changes_requested': 'مطلوب تغييرات',
            '03_approved': 'معتمدة',
            '04_waiting_normal': 'في الانتظار',
            '1_done': 'منجزة',
            '1_canceled': 'ملغاة',
            'draft': 'مسودة',
        }
        return state_map.get(state, state or 'غير محدد')
    
    def _compute_lab_samples_info(self):
        """حساب معلومات عينات الفحص المرتبطة بعرض السعر"""
        for order in self:
            samples_info = []
            samples_count = 0
            

            if hasattr(order, 'tasks_ids'):
                for task in order.tasks_ids:
                    try:
                        lab_samples = self.env['lab.sample'].search([
                            ('task_id', '=', task.id)
                        ])
                        
                        for sample in lab_samples:

                            result_sets_info = []
                            for result_set in sample.result_set_ids:
                                result_sets_info.append({
                                    'id': result_set.id,
                                    'name': result_set.name,
                                    'state': result_set.state,
                                    'state_text': self._get_sample_state_text(result_set.state),
                                    'template_name': result_set.template_id.name if result_set.template_id else 'غير محدد',
                                    'technician': result_set.technician_id.name if result_set.technician_id else 'غير محدد',
                                    'start_date': result_set.start_date.strftime('%Y-%m-%d %H:%M') if result_set.start_date else 'غير محدد',
                                    'overall_result': result_set.overall_result,
                                    'overall_result_text': self._get_test_result_text(result_set.overall_result),
                                    'progress_percentage': getattr(result_set, 'progress_percentage', 0) * 100,
                                    'number_of_samples': result_set.number_of_samples,
                                    'testing_date': result_set.testing_date.strftime('%Y-%m-%d') if hasattr(result_set, 'testing_date') and result_set.testing_date else 'غير محدد',
                                })
                            
                            samples_info.append({
                                'id': sample.id,
                                'name': sample.name,
                                'state': sample.state,
                                'state_text': self._get_sample_state_text(sample.state),
                                'product_name': sample.product_id.name if sample.product_id else 'غير محدد',
                                'sample_subtype': sample.sample_subtype_id.name if sample.sample_subtype_id else 'غير محدد',
                                'collection_date': sample.collection_date.strftime('%Y-%m-%d') if sample.collection_date else 'غير محدد',
                                'received_date': sample.received_date.strftime('%Y-%m-%d %H:%M') if sample.received_date else 'غير محدد',
                                'quantity': sample.quantity,
                                'overall_result': sample.overall_result,
                                'overall_result_text': self._get_test_result_text(sample.overall_result),
                                'task_name': task.name,
                                'result_sets': result_sets_info,
                                'result_sets_count': len(result_sets_info),
                            })
                        samples_count += len(lab_samples)
                    except Exception:

                        pass
            

            try:
                if order.partner_id:

                    partner_tasks = self.env['project.task'].search([
                        ('partner_id', '=', order.partner_id.id),
                        ('sale_order_id', '=', order.id) if 'sale_order_id' in self.env['project.task']._fields else ('id', '!=', 0)
                    ])
                    
                    for task in partner_tasks:
                        if task.id not in [t.id for t in order.tasks_ids] if hasattr(order, 'tasks_ids') else []:
                            lab_samples = self.env['lab.sample'].search([
                                ('task_id', '=', task.id)
                            ])
                            
                            for sample in lab_samples:
                                result_sets_info = []
                                for result_set in sample.result_set_ids:
                                    result_sets_info.append({
                                        'id': result_set.id,
                                        'name': result_set.name,
                                        'state': result_set.state,
                                        'state_text': self._get_sample_state_text(result_set.state),
                                        'template_name': result_set.template_id.name if result_set.template_id else 'غير محدد',
                                        'technician': result_set.technician_id.name if result_set.technician_id else 'غير محدد',
                                        'start_date': result_set.start_date.strftime('%Y-%m-%d %H:%M') if result_set.start_date else 'غير محدد',
                                        'overall_result': result_set.overall_result,
                                        'overall_result_text': self._get_test_result_text(result_set.overall_result),
                                        'progress_percentage': getattr(result_set, 'progress_percentage', 0) * 100,
                                        'number_of_samples': result_set.number_of_samples,
                                        'testing_date': result_set.testing_date.strftime('%Y-%m-%d') if hasattr(result_set, 'testing_date') and result_set.testing_date else 'غير محدد',
                                    })
                                
                                samples_info.append({
                                    'id': sample.id,
                                    'name': sample.name,
                                    'state': sample.state,
                                    'state_text': self._get_sample_state_text(sample.state),
                                    'product_name': sample.product_id.name if sample.product_id else 'غير محدد',
                                    'sample_subtype': sample.sample_subtype_id.name if sample.sample_subtype_id else 'غير محدد',
                                    'collection_date': sample.collection_date.strftime('%Y-%m-%d') if sample.collection_date else 'غير محدد',
                                    'received_date': sample.received_date.strftime('%Y-%m-%d %H:%M') if sample.received_date else 'غير محدد',
                                    'quantity': sample.quantity,
                                    'overall_result': sample.overall_result,
                                    'overall_result_text': self._get_test_result_text(sample.overall_result),
                                    'task_name': task.name,
                                    'result_sets': result_sets_info,
                                    'result_sets_count': len(result_sets_info),
                                })
                            samples_count += len(lab_samples)
            except Exception:

                pass
            
            order.lab_samples_info = samples_info
            order.lab_samples_count = samples_count
    
    def _get_sample_state_text(self, state):
        """تحويل حالة العينة إلى نص عربي"""
        state_map = {
            'draft': 'مسودة',
            'received': 'مستلمة',
            'testing': 'قيد الفحص',
            'completed': 'مكتملة',
            'rejected': 'مرفوضة',
            'in_progress': 'قيد التنفيذ',
            'calculated': 'تم الحساب',
            'review': 'قيد المراجعة',
            'approved': 'معتمد',
            'cancelled': 'ملغى',
        }
        return state_map.get(state, state or 'غير محدد')
    
    def _get_test_result_text(self, result):
        """تحويل نتيجة الفحص إلى نص عربي"""
        result_map = {
            'pass': 'ناجح',
            'fail': 'فاشل',
            'pending': 'قيد الانتظار',
        }
        return result_map.get(result, result or 'غير محدد') 
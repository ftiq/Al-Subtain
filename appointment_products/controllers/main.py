# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment
from odoo.tools.mail import email_normalize
from odoo.addons.phone_validation.tools import phone_validation
from odoo.osv import expression


class WebsiteAppointmentProducts(WebsiteAppointment):
    """Extends website appointment flow to generate a Sale Quotation with optional products."""

    def _handle_appointment_form_submission(
        self, appointment_type,
        date_start, date_end, duration,
        answer_input_values, name, customer, appointment_invite, guests=None,
        staff_user=None, asked_capacity=1, booking_line_values=None
    ):
        if customer == request.env['res.partner'] or (customer and customer.name == 'Public user'):
            email = request.params.get('email')
            phone = request.params.get('phone')
            form_name = request.params.get('name')
            
            if email and form_name:
                normalized_email = email_normalize(email)
                existing_partner = False
                
                if normalized_email:
                    existing_partner = request.env['res.partner'].sudo().search([
                        '|',
                        ('email_normalized', '=', normalized_email),
                        ('email', '=ilike', email)
                    ], limit=1)
                
                if not existing_partner and phone:
                    country = self._get_customer_country()
                    phone_e164 = phone_validation.phone_format(phone, country.code, country.phone_code, 
                                                              force_format="E164", raise_exception=False)
                    search_domain_phone = [('phone', '=', phone)]
                    if phone_e164:
                        search_domain_phone = expression.OR([[('phone', '=', phone_e164)], [('phone', '=', phone)]])
                    
                    existing_partner = request.env['res.partner'].sudo().search(search_domain_phone, limit=1)
                
                if existing_partner:
                    vals = {}
                    if not existing_partner.name or existing_partner.name == 'Public user':
                        vals['name'] = form_name
                    if not existing_partner.email and email:
                        vals['email'] = email
                    if not existing_partner.phone and phone:
                        vals['phone'] = phone
                        
                    if vals:
                        existing_partner.sudo().write(vals)
                    
                    customer = existing_partner
                else:
                    customer = request.env['res.partner'].sudo().create({
                        'name': form_name,
                        'email': email,
                        'phone': phone,
                        'lang': request.lang.code,
                    })
        
        response = super()._handle_appointment_form_submission(
            appointment_type,
            date_start, date_end, duration,
            answer_input_values, name, customer, appointment_invite, guests,
            staff_user, asked_capacity, booking_line_values,
        )

        if customer and customer.id:
            request.session['appointment_partner_id'] = customer.id

        sale_lines = []
        for key, value in request.params.items():
            if key.startswith("product_qty_"):
                try:
                    product_id = int(key.replace("product_qty_", ""))
                    qty = float(value or 0)
                except (ValueError, TypeError):
                    continue
                if qty > 0:
                    sale_lines.append((product_id, qty))

        if not sale_lines:
            return response

        order = request.website.sale_get_order(force_create=True)

        if order.partner_id != customer:
            order.sudo().write({
                'partner_id': customer.id,
                'partner_invoice_id': customer.id,
                'partner_shipping_id': customer.id,
            })

        for product_id, qty in sale_lines:
            try:
                existing_line = order.order_line.filtered(lambda l: l.product_id.id == product_id)
                if existing_line:
                    continue
                order.sudo()._cart_update(product_id=product_id, add_qty=qty)
            except Exception:
                existing_line = order.order_line.filtered(lambda l: l.product_id.id == product_id)
                if existing_line:
                    existing_line.product_uom_qty += qty
                else:
                    order.write({'order_line': [(0, 0, {
                        'product_id': product_id,
                        'product_uom_qty': qty,
                    })]})

        if not order.origin:
            order.origin = f"Appointment / {appointment_type.name}"

        return response


    @http.route('/appointment_products/get_sale_order', type='json', auth='public', website=True)
    def get_sale_order(self):
        order = request.website.sale_get_order()
        return {'order_id': order.id if order else False}


    @http.route('/appointment/create_or_update_partner', type='json', auth='public', website=True)
    def create_or_update_partner(self, name=None, email=None, phone=None):
        if not email or not name:
            return {'success': False, 'error': 'Missing required fields'}
        
        normalized_email = email_normalize(email)
        existing_partner = False
        
        if normalized_email:
            existing_partner = request.env['res.partner'].sudo().search([
                '|',
                ('email_normalized', '=', normalized_email),
                ('email', '=ilike', email)
            ], limit=1)
        
        if not existing_partner and phone:
            country = self._get_customer_country()
            phone_e164 = phone_validation.phone_format(phone, country.code, country.phone_code, 
                                                     force_format="E164", raise_exception=False)
            search_domain_phone = [('phone', '=', phone)]
            if phone_e164:
                search_domain_phone = expression.OR([[('phone', '=', phone_e164)], [('phone', '=', phone)]])
            
            existing_partner = request.env['res.partner'].sudo().search(search_domain_phone, limit=1)
        
        if existing_partner:
            vals = {}
            if not existing_partner.name or existing_partner.name == 'Public user':
                vals['name'] = name
            if not existing_partner.email and email:
                vals['email'] = email
            if not existing_partner.phone and phone:
                vals['phone'] = phone
                
            if vals:
                existing_partner.sudo().write(vals)
            
            partner = existing_partner
        else:
            partner = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
                'lang': request.lang.code,
            })
        
        return {
            'success': True,
            'partner_id': partner.id,
            'name': partner.name,
            'email': partner.email,
            'phone': partner.phone
        }


    @http.route('/shop/cart/update_partner', type='json', auth='public', website=True)
    def update_cart_partner(self, partner_id=None, order_id=None):
        if not partner_id or not order_id:
            return {'success': False, 'error': 'Missing required fields'}
        
        try:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))
            order = request.env['sale.order'].sudo().browse(int(order_id))
            
            if not partner.exists() or not order.exists():
                return {'success': False, 'error': 'Partner or Order not found'}
            
            order.sudo().write({
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
            })
            
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}


    @http.route('/appointment_products/upload_attachment', type='http', auth='public', website=True, csrf=False)
    def upload_attachment(self, order_id, **post):
        try:
            order = request.env['sale.order'].sudo().browse(int(order_id))
        except Exception:
            return http.Response(status=404)

        if not order:
            return http.Response(status=404)

        from base64 import b64encode
        file_storage = post.get('ufile')
        if not file_storage:
            return http.Response(status=400)

        request.env['ir.attachment'].sudo().create({
            'name': file_storage.filename,
            'datas': b64encode(file_storage.read()),
            'res_model': 'sale.order',
            'res_id': order.id,
            'mimetype': file_storage.mimetype,
            'type': 'binary',
        })

        return http.Response(status=200)

    def _get_customer_partner(self):
        partner = super()._get_customer_partner()
        if partner:
            return partner

        email = request.params.get('email')
        phone = request.params.get('phone')
        name = request.params.get('name')

        if email:
            normalized = email_normalize(email)
            partner = request.env['res.partner'].sudo().search([('email_normalized', '=', normalized)], limit=1)
            if partner:
                return partner

        if phone:
            country = self._get_customer_country()
            phone_e164 = phone_validation.phone_format(phone, country.code, country.phone_code, force_format="E164", raise_exception=False)
            search_domain_phone = [('phone', '=', phone)]
            if phone_e164:
                search_domain_phone = expression.OR([[('phone', '=', phone_e164)], [('phone', '=', phone)]])
            partner = request.env['res.partner'].sudo().search(search_domain_phone, limit=1)
            if partner:
                return partner

        if name:
            partner = request.env['res.partner'].sudo().search([('name', '=', name)], limit=1)
            if partner:
                return partner

        return request.env['res.partner']

    @http.route('/appointment/get_session_partner', type='json', auth='public', website=True)
    def get_session_partner(self):
        partner_id = request.session.get('appointment_partner_id')
        
        if not partner_id:
            return {'success': False, 'error': 'No partner in session'}
        
        try:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))
            
            if not partner.exists():
                return {'success': False, 'error': 'Partner not found'}
            
            return {
                'success': True,
                'partner_id': partner.id,
                'name': partner.name,
                'email': partner.email,
                'phone': partner.phone
            }
        except Exception as e:
            return {'success': False, 'error': str(e)} 
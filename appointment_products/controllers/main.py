# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.website_appointment.controllers.appointment import WebsiteAppointment
from odoo.tools.mail import email_normalize
from odoo.addons.phone_validation.tools import phone_validation
from odoo.osv import expression
import logging
import re
from datetime import datetime, timedelta
import json
from urllib.parse import unquote_plus
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as dtf


class WebsiteAppointmentProducts(WebsiteAppointment):
    """Extends website appointment flow to generate a Sale Quotation with optional products."""

    def _handle_appointment_form_submission(
        self, appointment_type,
        date_start, date_end, duration,
        answer_input_values, name, customer, appointment_invite, guests=None,
        staff_user=None, asked_capacity=1, booking_line_values=None
    ):

        if not customer or customer.name == 'Public user':
            customer = False 


        partner_id_param = request.params.get('partner_id')
        if partner_id_param:
            try:
                partner_record = request.env['res.partner'].sudo().browse(int(partner_id_param))
                if partner_record.exists():
                    customer = partner_record
            except Exception:
                pass
        

        form_name = request.params.get('name')
        email = request.params.get('email')
        phone = request.params.get('phone')
        
        if form_name and (email or phone):
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
            
            if existing_partner and existing_partner.name != 'Public user':
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
            

            if customer and customer.id:
                request.session['appointment_partner_id'] = customer.id
        
        _logger = logging.getLogger(__name__)
        _logger.info(f"Customer before submission: {customer.name} (ID: {customer.id})")
        
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

                    if qty > 1:
                        qty = 1
                except (ValueError, TypeError):
                    continue
                if qty > 0:
                    sale_lines.append((product_id, qty))

        if not sale_lines:
            order_tmp = request.website.sale_get_order()
            try:
                if order_tmp and answer_input_values:
                    body_parts = [f"<p><b>{request.env['appointment.question'].sudo().browse(val.get('question_id')).name}:</b> "
                                  f"{(request.env['appointment.answer'].sudo().browse(val['value_answer_id']).name if val.get('value_answer_id') else val.get('value_text_box', ''))}</p>"
                                  for val in answer_input_values]
                    if body_parts:
                        order_tmp.message_post(body="".join(body_parts), message_type='comment', subtype_xmlid='mail.mt_comment')

                        qa_vals = []
                        for val in answer_input_values:
                            qa_val = {
                                'question_id': val.get('question_id'),
                                'partner_id': customer.id if customer else False,
                            }
                            if val.get('value_answer_id'):
                                qa_val['value_answer_id'] = val['value_answer_id']
                            if val.get('value_text_box'):
                                qa_val['value_text_box'] = val['value_text_box']
                            qa_vals.append((0, 0, qa_val))

                        if qa_vals:
                            order_tmp.sudo().write({'appointment_answer_ids': qa_vals})


                    try:
                        if order_tmp:
                            order_tmp.sudo().write({'appointment_datetime': date_start})
                    except Exception as dt_err:
                        _logger = logging.getLogger(__name__)
                        _logger.warning(f"Failed to write appointment_datetime (no sale lines): {dt_err}")
            except Exception as post_err:
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Failed to post Q&A when no sale lines: {post_err}")
            return response

        order = request.website.sale_get_order()

        if order and order.partner_id != customer:
            request.session.pop('sale_order_id', None)
            order = request.website.sale_get_order(force_create=True)

        if not order:
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

        try:
            if order and answer_input_values:

                qa_vals = []
                for val in answer_input_values:
                    qa_val = {
                        'question_id': val.get('question_id'),
                        'partner_id': customer.id if customer else False,
                    }
                    if val.get('value_answer_id'):
                        qa_val['value_answer_id'] = val['value_answer_id']
                    if val.get('value_text_box'):
                        qa_val['value_text_box'] = val['value_text_box']
                    qa_vals.append((0, 0, qa_val))

                if qa_vals:
                    order.sudo().write({'appointment_answer_ids': qa_vals})

                body_parts = []
                for val in answer_input_values:
                    question = request.env['appointment.question'].sudo().browse(val.get('question_id'))
                    answer_text = ''
                    if val.get('value_answer_id'):
                        answer_rec = request.env['appointment.answer'].sudo().browse(val['value_answer_id'])
                        answer_text = answer_rec.name
                    elif val.get('value_text_box'):
                        answer_text = val['value_text_box']

                    if question and answer_text:
                        body_parts.append(f"<p><b>{question.name}:</b> {answer_text}</p>")

                if body_parts:
                    body_html = "".join(body_parts)
                    order.message_post(body=body_html, message_type='comment', subtype_xmlid='mail.mt_comment')
        except Exception as chat_err:
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Failed to post Q&A to order chatter: {chat_err}")


        try:
            if order:
                order.sudo().write({'appointment_datetime': date_start})
        except Exception as dt_err:
            _logger = logging.getLogger(__name__)
            _logger.warning(f"Failed to write appointment_datetime: {dt_err}")

        return response


    @http.route('/appointment_products/get_sale_order', type='json', auth='public', website=True)
    def get_sale_order(self):
        order = request.website.sale_get_order()
        return {'order_id': order.id if order else False}


    @http.route('/appointment/create_or_update_partner', type='json', auth='public', website=True)
    def create_or_update_partner(self, name=None, email=None, phone=None):
        if not name:
            return {'success': False, 'error': 'Missing required name'}
        
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
        
        if existing_partner and existing_partner.name != 'Public user':
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
        

        if partner and partner.id:
            request.session['appointment_partner_id'] = partner.id
            

            _logger = logging.getLogger(__name__)
            _logger.info(f"Partner created/updated: {partner.name} (ID: {partner.id})")
        
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

            if order.partner_id and order.partner_id != partner:
                request.session.pop('sale_order_id', None)
                new_order = request.website.sale_get_order(force_create=True)
                for line in order.order_line:
                    new_order.write({'order_line': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'price_unit': line.price_unit,
                    })]})

                new_order.sudo().write({
                    'partner_id': partner.id,
                    'partner_invoice_id': partner.id,
                    'partner_shipping_id': partner.id,
                })
                return {'success': True, 'order_id': new_order.id}


            order.sudo().write({
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
            })
            return {'success': True, 'order_id': order.id}
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
        files = post.getlist('ufile') if hasattr(post, 'getlist') else [post.get('ufile')]
        if not files or not files[0]:
            return http.Response(status=400)

        attachment_ids = []
        for file_storage in files:
            attach = request.env['ir.attachment'].sudo().create({
            'name': file_storage.filename,
            'datas': b64encode(file_storage.read()),
            'res_model': 'sale.order',
            'res_id': order.id,
            'mimetype': file_storage.mimetype,
            'type': 'binary',
        })
            attachment_ids.append(attach.id)


        if attachment_ids:
            order.message_post(body=_('تم رفع مرفقات للموعد.'), attachment_ids=attachment_ids, message_type='comment', subtype_xmlid='mail.mt_comment')

        return http.Response(status=200)

    def _get_customer_partner(self):

        partner_id_param = request.params.get('partner_id')
        if partner_id_param:
            try:
                partner_rec = request.env['res.partner'].sudo().browse(int(partner_id_param))
                if partner_rec.exists():
                    request.session['appointment_partner_id'] = partner_rec.id
                    return partner_rec
            except Exception:
                pass


        partner_id = request.session.get('appointment_partner_id')
        if partner_id:
            partner = request.env['res.partner'].sudo().browse(int(partner_id))
            if partner.exists() and partner.name != 'Public user':
                return partner

        name = request.params.get('name')
        email = request.params.get('email')
        phone = request.params.get('phone')

        if name:
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
            
            if existing_partner and existing_partner.name != 'Public user':
                vals = {}
                if not existing_partner.name or existing_partner.name == 'Public user':
                    vals['name'] = name
                if not existing_partner.email and email:
                    vals['email'] = email
                if not existing_partner.phone and phone:
                    vals['phone'] = phone
                    
                if vals:
                    existing_partner.sudo().write(vals)
                
                request.session['appointment_partner_id'] = existing_partner.id
                return existing_partner
            elif name and email:
                new_partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'lang': request.lang.code,
                })
                
                request.session['appointment_partner_id'] = new_partner.id
                return new_partner
        

        if not email and not phone and not name:
            return request.env['res.partner']

        new_partner = request.env['res.partner'].sudo().create({
            'name': name or 'Guest',
            'email': email or False,
            'phone': phone or False,
            'lang': request.lang.code,
        })
        request.session['appointment_partner_id'] = new_partner.id
        return new_partner

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

    @http.route('/appointment/ensure_partner', type='json', auth='public', website=True)
    def ensure_partner(self):
        name = request.params.get('name')
        email = request.params.get('email')
        phone = request.params.get('phone')
        
        if name:
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
            

            if existing_partner and existing_partner.name != 'Public user':
                vals = {}
                if not existing_partner.name or existing_partner.name == 'Public user':
                    vals['name'] = name
                if not existing_partner.email and email:
                    vals['email'] = email
                if not existing_partner.phone and phone:
                    vals['phone'] = phone
                    
                if vals:
                    existing_partner.sudo().write(vals)
                
                request.session['appointment_partner_id'] = existing_partner.id
                return {
                    'success': True,
                    'partner_id': existing_partner.id,
                    'name': existing_partner.name,
                    'email': existing_partner.email,
                    'phone': existing_partner.phone
                }
            else:

                new_partner = request.env['res.partner'].sudo().create({
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'lang': request.lang.code,
                })
                
                request.session['appointment_partner_id'] = new_partner.id
                return {
                    'success': True,
                    'partner_id': new_partner.id,
                    'name': new_partner.name,
                    'email': new_partner.email,
                    'phone': new_partner.phone
                }
        

        return {'success': False, 'error': 'No partner found or created'}

    @http.route(['/appointment/<int:appointment_type_id>/submit'],
                type='http', auth="public", website=True, methods=["POST"])
    def appointment_form_submit(self, appointment_type_id, datetime_str, duration_str, name, phone, email, staff_user_id=None, available_resource_ids=None, asked_capacity=1,
                                guest_emails_str=None, **kwargs):
      
      
        _logger = logging.getLogger(__name__)
        _logger.info(f"Starting appointment form submit with name: {name}, email: {email}")
        

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
        
        if existing_partner and existing_partner.name != 'Public user':
            _logger.info(f"Found existing partner: {existing_partner.name} (ID: {existing_partner.id})")

            vals = {}
            if not existing_partner.name or existing_partner.name == 'Public user':
                vals['name'] = name
            if not existing_partner.email and email:
                vals['email'] = email
            if not existing_partner.phone and phone:
                vals['phone'] = phone
                
            if vals:
                existing_partner.sudo().write(vals)
            
            customer = existing_partner
        else:

            _logger.info(f"Creating new partner with name: {name}, email: {email}")
            customer = request.env['res.partner'].sudo().create({
                'name': name,
                'email': email,
                'phone': phone,
                'lang': request.lang.code,
            })
        

        if customer and customer.id:
            request.session['appointment_partner_id'] = customer.id
            _logger.info(f"Saved partner ID in session: {customer.id}")
        

        staff_user = None
        if staff_user_id:
            staff_user = request.env['res.users'].sudo().browse(int(staff_user_id))
        

        domain = self._appointments_base_domain(
            filter_appointment_type_ids=kwargs.get('filter_appointment_type_ids'),
            search=kwargs.get('search'),
            invite_token=kwargs.get('invite_token')
        )
        
        available_appointments = self._fetch_and_check_private_appointment_types(
            kwargs.get('filter_appointment_type_ids'),
            kwargs.get('filter_staff_user_ids'),
            kwargs.get('filter_resource_ids'),
            kwargs.get('invite_token'),
            domain=domain,
        )
        
        appointment_type = available_appointments.filtered(lambda appt: appt.id == int(appointment_type_id))
        
        if not appointment_type:
            return request.not_found()
        

        datetime_str = unquote_plus(datetime_str)
        duration = float(duration_str)
        
        date_start = datetime.strptime(datetime_str, dtf)
        date_end = date_start + timedelta(hours=duration)
        

        check_kwargs = {k: v for k, v in kwargs.items() if k != 'duration'}
        if not self._check_appointment_is_valid_slot(appointment_type, staff_user_id, None, available_resource_ids, datetime_str, duration, asked_capacity, **check_kwargs):
            return request.redirect(f'/appointment/{appointment_type_id}?state=failed-staff-user')
        

        guests = []
        if guest_emails_str:
            guest_emails = [email.strip() for email in guest_emails_str.split(',') if email.strip()]
            guests = [
                request.env['res.partner'].sudo().search([('email', '=ilike', email)], limit=1) or
                request.env['res.partner'].sudo().create({'email': email, 'name': email.split('@')[0]})
                for email in guest_emails
            ]
        

        partner_inputs = {}
        appointment_question_ids = appointment_type.question_ids.ids
        for k_key, k_value in [item for item in kwargs.items() if item[1]]:
            question_id_str = re.match(r"\bquestion_([0-9]+)\b", k_key)
            if question_id_str and int(question_id_str.group(1)) in appointment_question_ids:
                partner_inputs[int(question_id_str.group(1))] = k_value
                continue
            checkbox_ids_str = re.match(r"\bquestion_([0-9]+)_answer_([0-9]+)\b", k_key)
            if checkbox_ids_str:
                question_id, answer_id = [int(checkbox_ids_str.group(1)), int(checkbox_ids_str.group(2))]
                if question_id in appointment_question_ids:
                    partner_inputs[question_id] = partner_inputs.get(question_id, []) + [answer_id]
        

        answer_input_values = []
        base_answer_input_vals = {
            'appointment_type_id': appointment_type.id,
            'partner_id': customer.id,
        }
        
        for question in appointment_type.question_ids.filtered(lambda question: question.id in partner_inputs.keys()):
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda answer: answer.id in partner_inputs[question.id])
                answer_input_values.extend([
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=answer.id) for answer in answers
                ])
            elif question.question_type in ['select', 'radio']:
                answer_input_values.append(
                    dict(base_answer_input_vals, question_id=question.id, value_answer_id=int(partner_inputs[question.id]))
                )
            elif question.question_type in ['char', 'text']:
                answer_input_values.append(
                    dict(base_answer_input_vals, question_id=question.id, value_text_box=partner_inputs[question.id].strip())
                )
        

        booking_line_values = []
        if appointment_type.schedule_based_on == 'resources' and available_resource_ids:
            resources = request.env['appointment.resource'].sudo().search([
                ('id', 'in', json.loads(available_resource_ids)),
                ('appointment_type_ids', 'in', appointment_type.id),
            ])
            booking_line_values = [
                {
                    'resource_id': resource.id,
                    'capacity_used': asked_capacity,
                } for resource in resources
            ]
        

        _logger.info(f"Calling _handle_appointment_form_submission with customer: {customer.name} (ID: {customer.id})")
        appointment_invite = request.env['appointment.invite'].browse(int(kwargs.get('invite_token'))) if kwargs.get('invite_token') else request.env['appointment.invite']
        return self._handle_appointment_form_submission(
            appointment_type,
            date_start, date_end, duration,
            answer_input_values, name, customer, appointment_invite, guests,
            staff_user, asked_capacity, booking_line_values,
        ) 
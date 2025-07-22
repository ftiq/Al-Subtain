/** @odoo-module **/

odoo.define('appointment_products.appointment_cart', [
    '@web/legacy/js/public/public_widget',
    '@website_sale/js/website_sale_utils',
    '@web/core/network/rpc'
], function (require) {
    'use strict';

    const publicWidget = require('@web/legacy/js/public/public_widget')[Symbol.for('default')];
    const wSaleUtils = require('@website_sale/js/website_sale_utils')[Symbol.for('default')];
    const $ = window.jQuery || window.$;
    const { rpc } = require('@web/core/network/rpc');

    const AppointmentForm = publicWidget.registry.appointmentForm;

    if (AppointmentForm) {
        const newEvents = {};
        newEvents['click .o_appointment_create_quote_btn'] = '_onCreateQuotation';

        const originalConfirm = AppointmentForm.prototype._onConfirmAppointment;
        AppointmentForm.include({
            events: Object.assign({}, AppointmentForm.prototype.events || {}, newEvents),
            
            async _addProductsToCart() {
                const self = this;
                const $cards = $('.appointment_product_card');

                await rpc('/shop/cart/clear', {});

                for (const card of $cards.toArray()) {
                    const $card = $(card);
                    const qty = parseFloat($card.find('.quantity').val() || 0);
                    if (qty > 0) {
                        const productId = parseInt($card.data('product-id'));
                        const data = await rpc('/shop/cart/update_json', {
                            product_id: productId,
                            add_qty: qty,
                            display: false,
                            force_create: true,
                        });

                        wSaleUtils.updateCartNavBar(data);
                        wSaleUtils.showWarning(data.notification_info.warning);
                        wSaleUtils.showCartNotification(self.call.bind(self), data.notification_info);
                    }
                }
            },

            async _createOrUpdatePartner() {
                const name = $('input[name="name"]').val();
                const email = $('input[name="email"]').val();
                const phone = $('input[name="phone"]').val();
                
                if (!name) {
                    console.log('Missing required partner info', { name, email });
                    return null;
                }
                
                try {
                    const result = await rpc('/appointment/create_or_update_partner', {
                        name: name,
                        email: email,
                        phone: phone
                    });
                    
                    if (result && result.success) {
                        console.log('Partner created/updated successfully', result);
                        return result;
                    } else {
                        console.error('Failed to create/update partner', result);
                        return null;
                    }
                } catch (error) {
                    console.error('Error creating/updating partner:', error);
                    return null;
                }
            },

            async _onCreateQuotation(event) {
                event.preventDefault();
                
                const partnerData = await this._createOrUpdatePartner();
                
                await this._addProductsToCart();

                const orderInfo = await rpc('/appointment_products/get_sale_order', {});
                const orderId = orderInfo.order_id;
                
                if (orderId && partnerData && partnerData.partner_id) {
                    try {
                        const updateResult = await rpc('/shop/cart/update_partner', {
                            partner_id: partnerData.partner_id,
                            order_id: orderId
                        });
                        
                        if (!updateResult || !updateResult.success) {
                            console.error('Failed to update order with partner info', updateResult);
                        }
                    } catch (error) {
                        console.error('Error updating order with partner info:', error);
                    }
                } else if (orderId) {
                    try {
                        const sessionPartnerResult = await rpc('/appointment/get_session_partner', {});
                        if (sessionPartnerResult && sessionPartnerResult.partner_id) {
                            await rpc('/shop/cart/update_partner', {
                                partner_id: sessionPartnerResult.partner_id,
                                order_id: orderId
                            });
                        }
                    } catch (error) {
                        console.error('Error getting partner from session:', error);
                    }
                }

                const filesInput = document.querySelector('.o_appt_files');
                if (filesInput && filesInput.files.length && orderId) {
                    try {
                            for (const file of filesInput.files) {
                                const formData = new FormData();
                                formData.append('ufile', file);
                                formData.append('model', 'sale.order');
                                formData.append('id', orderId);
                                if (odoo.csrf_token) {
                                    formData.append('csrf_token', odoo.csrf_token);
                                }
                                await fetch('/appointment_products/upload_attachment?order_id=' + orderId, {
                                    method: 'POST',
                                    body: formData,
                                });
                        }
                    } catch (e) {
                        console.error('Attachment upload failed', e);
                    }
                }

                window.location.href = '/shop/cart';
            },

            async _onConfirmAppointment(event) {
                event.preventDefault();
                
                const name = $('input[name="name"]').val();
                const email = $('input[name="email"]').val();
                const phone = $('input[name="phone"]').val();
                
                if (!name) {
                    console.error('Missing required fields');
                    return originalConfirm.call(this, event);
                }
                
                try {
                    console.log('Creating partner with:', { name, email, phone });
                    const partnerResult = await rpc('/appointment/create_or_update_partner', {
                        name: name,
                        email: email,
                        phone: phone
                    });
                    
                    if (!partnerResult || !partnerResult.success) {
                        console.error('Failed to create partner');
                        return originalConfirm.call(this, event);
                    }
                    
                    console.log('Partner created successfully:', partnerResult);


                    await this._addProductsToCart();

                    try {
                        const orderInfo = await rpc('/appointment_products/get_sale_order', {});
                        const orderId = orderInfo && orderInfo.order_id;
                        if (orderId && partnerResult.partner_id) {
                            await rpc('/shop/cart/update_partner', {
                                partner_id: partnerResult.partner_id,
                                order_id: orderId,
                            });
                        }
                    } catch (updateErr) {
                        console.error('Error updating cart partner on confirm:', updateErr);
                    }

                    try {
                        const finalOrderInfo = await rpc('/appointment_products/get_sale_order', {});
                        const finalOrderId = finalOrderInfo && finalOrderInfo.order_id;
                        const filesInput = document.querySelector('.o_appt_files');
                        if (filesInput && filesInput.files.length && finalOrderId) {
                            for (const file of filesInput.files) {
                                const formData = new FormData();
                                formData.append('ufile', file);
                                formData.append('model', 'sale.order');
                                formData.append('id', finalOrderId);
                                if (odoo.csrf_token) {
                                    formData.append('csrf_token', odoo.csrf_token);
                                }
                                await fetch('/appointment_products/upload_attachment?order_id=' + finalOrderId, {
                                    method: 'POST',
                                    body: formData,
                                });
                            }
                        }
                    } catch (attachErr) {
                        console.error('Attachment upload failed on confirm', attachErr);
                    }

                    const $form = this.$el.closest('form');
                    
                    $form.find('input[name="partner_id"]').remove();
                    
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = 'partner_id';
                    hiddenInput.value = partnerResult.partner_id;
                    $form[0].appendChild(hiddenInput);
                    
                    console.log('Added partner_id to form:', partnerResult.partner_id);
                    
                    const confirmFlagInput = document.createElement('input');
                    confirmFlagInput.type = 'hidden';
                    confirmFlagInput.name = 'custom_confirm_flag';
                    confirmFlagInput.value = '1';
                    $form[0].appendChild(confirmFlagInput);
                    
                    const appointmentForm = document.querySelector('.appointment_submit_form');
                    if (appointmentForm.reportValidity()) {
                        console.log('Form is valid, submitting...');
                        appointmentForm.submit();
                    }
                } catch (error) {
                    console.error('Error in appointment confirmation:', error);
                return originalConfirm.call(this, event);
                }
            },
        });
    }
}); 
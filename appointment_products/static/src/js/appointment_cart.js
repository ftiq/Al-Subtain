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

    console.log('appointment_cart.js loaded');
    console.log('AppointmentForm:', AppointmentForm);

    if (AppointmentForm) {
        const newEvents = {};
        newEvents['click .o_appointment_create_quote_btn'] = '_onCreateQuotation';

        const originalConfirm = AppointmentForm.prototype._onConfirmAppointment;
        console.log('originalConfirm:', originalConfirm);
        
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
                console.log('_onConfirmAppointment called!');
                event.preventDefault();
                
                const name = $('input[name="name"]').val();
                const email = $('input[name="email"]').val();
                const phone = $('input[name="phone"]').val();
                
                console.log('Form data:', { name, email, phone });
                
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


                    const $form = this.$el.closest('form');
                    const $cards = $('.appointment_product_card');
                    
                    console.log(`Found ${$cards.length} product cards`);
                    console.log('Form element:', $form[0]);
                    

                    $form.find('input[name^="product_qty_"]').remove();
                    
                    let productsAdded = 0;

                    $cards.each(function() {
                        const $card = $(this);
                        const qty = parseFloat($card.find('.quantity').val() || 0);
                        const productId = parseInt($card.data('product-id'));
                        console.log(`Product ${productId}: quantity = ${qty}`);
                        
                        if (qty > 0) {
                            const hiddenInput = document.createElement('input');
                            hiddenInput.type = 'hidden';
                            hiddenInput.name = `product_qty_${productId}`;
                            hiddenInput.value = qty;
                            $form[0].appendChild(hiddenInput);
                            productsAdded++;
                            console.log(`Added hidden field: product_qty_${productId} = ${qty}`);
                        }
                    });
                    
                    console.log(`Total products with quantity > 0: ${productsAdded}`);
                    
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
    } else {
        console.error('AppointmentForm not found in publicWidget.registry');
    }


    $(document).ready(function() {
        console.log('Document ready - adding fallback handler');
        

        const $cards = $('.appointment_product_card');
        console.log(`Found ${$cards.length} product cards on page load`);
        
        $cards.each(function(index) {
            const $card = $(this);
            const productId = $card.data('product-id');
            const productName = $card.data('name');
            const qty = $card.find('.quantity').val();
            console.log(`Product ${index + 1}: ID=${productId}, Name=${productName}, Current Qty=${qty}`);
        });
        

        $(document).on('change', '.appointment_product_card .quantity', function() {
            const $input = $(this);
            const $card = $input.closest('.appointment_product_card');
            const productId = $card.data('product-id');
            const qty = $input.val();
            console.log(`Quantity changed for product ${productId}: ${qty}`);
        });
        

        $(document).on('submit', '.appointment_submit_form', function(e) {
            console.log('Form submit event captured by fallback handler');
            
            const $form = $(this);
            const $cards = $('.appointment_product_card');
            
            console.log(`Fallback: Found ${$cards.length} product cards`);
            

            $form.find('input[name^="product_qty_"]').remove();
            
            let productsAdded = 0;

            $cards.each(function() {
                const $card = $(this);
                const qty = parseFloat($card.find('.quantity').val() || 0);
                const productId = parseInt($card.data('product-id'));
                console.log(`Fallback: Product ${productId}: quantity = ${qty}`);
                
                if (qty > 0) {
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.name = `product_qty_${productId}`;
                    hiddenInput.value = qty;
                    $form[0].appendChild(hiddenInput);
                    productsAdded++;
                    console.log(`Fallback: Added hidden field: product_qty_${productId} = ${qty}`);
                }
            });
            
            console.log(`Fallback: Total products with quantity > 0: ${productsAdded}`);
        });
    });
}); 
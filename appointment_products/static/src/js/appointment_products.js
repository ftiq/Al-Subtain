/* Copyright 2023 Odoo Custom
 * License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

odoo.define('appointment_products.appointment_products', [], function (require) {
    'use strict';

    const $ = window.jQuery || window.$;
    
    $(document).ready(function () {
        function filterAppointmentProducts() {
            const query = ($('.js_appt_product_search').val() || '').toLowerCase();
            const categId = $('.js_appt_product_category').val();

            $('.appointment_product_card').each(function () {
                const $card = $(this);
                const name = ($card.data('name') || '').toString().toLowerCase();
                const defCode = ($card.data('default-code') || '').toString().toLowerCase();
                const cardCateg = $card.data('categ-id') ? $card.data('categ-id').toString() : '';

                const matchQuery = !query || name.includes(query) || defCode.includes(query);
                const matchCateg = !categId || !cardCateg || categId === cardCateg;

                $card.closest('.col-md-4, .col-sm-6').toggle(matchQuery && matchCateg);
            });
        }

        $(document).on('input', '.js_appt_product_search', filterAppointmentProducts);
        $(document).on('change', '.js_appt_product_category', filterAppointmentProducts);

        filterAppointmentProducts();

        $('.appointment_product_card').each(function () {
            const $card = $(this);

            $card.on('click', '.js_add_cart_json', function (ev) {
                ev.preventDefault();
                const $link = $(this);
                const $input = $link.closest('.input-group').find('.quantity');
                const min = parseFloat($input.attr('min') || 0);
                const max = parseFloat($input.attr('max') || Infinity);
                const previousQty = parseFloat($input.val() || 0, 10);
                const quantity = ($link.find('.fa-minus').length ? -1 : 1) + previousQty;
                const newQty = Math.max(min, Math.min(max, quantity));
                if (newQty !== previousQty) {
                    $input.val(newQty).trigger('change');
                }
            });

            $card.on('change', '.quantity', function () {
                const $input = $(this);
                const basePrice = parseFloat($input.data('price') || 0);
                const quantity = parseFloat($input.val() || 0);
                const $totalPrice = $card.find('.product_total_price');
                const totalPrice = basePrice * quantity;
                $totalPrice.text(totalPrice.toFixed(2));
            });
        });
    });
}); 
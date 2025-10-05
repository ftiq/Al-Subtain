# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AppointmentSaleAnswerInput(models.Model):

    _name = 'appointment.sale.answer.input'
    _description = 'Appointment Answer Inputs linked to Sale Order'
    _rec_name = 'question_id'
    _order = 'id desc'

    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    question_id = fields.Many2one('appointment.question', string='Question', required=True, ondelete='cascade')
    value_answer_id = fields.Many2one('appointment.answer', string='Selected Answer', ondelete='restrict')
    value_text_box = fields.Text('Text Answer')

    appointment_type_id = fields.Many2one(related='question_id.appointment_type_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer')
    question_type = fields.Selection(related='question_id.question_type', store=True, readonly=True)

    _sql_constraints = [
        (
            'value_check',
            "CHECK(value_answer_id IS NOT NULL OR COALESCE(value_text_box, '') <> '')",
            _('An answer input must either reference a predefined answer or contain a text value.')
        )
    ]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    appointment_answer_ids = fields.One2many(
        'appointment.sale.answer.input',
        'sale_order_id',
        string='Appointment Questions & Answers'
    )

    appointment_attachment_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        string='مرفقات الموعد',
        domain=[('res_model', '=', 'sale.order')]
    )



    def action_confirm(self):
        """On confirmation, copy appointment answers to the linked FSM task(s)."""
        self = self.with_context(skip_lab_sample_creation_on_sale_confirm=True)
        res = super().action_confirm()
        self._transfer_appointment_answers_to_tasks()
        return res

    def _transfer_appointment_answers_to_tasks(self):

        FsmAnswer = self.env['fsm.task.answer.input']
        Task = self.env['project.task']

        for order in self:
            if not order.appointment_answer_ids:
                continue

            tasks = order.order_line.mapped('task_id') | self.env['project.task'].search([('sale_order_id', '=', order.id)])
            if not tasks:
                continue

            for task in tasks:
                existing_map = {r.question_id.id: r for r in task.fsm_question_ids}
                to_create = []
                to_update = []

                for ans in order.appointment_answer_ids:
                    rec = existing_map.get(ans.question_id.id)
                    vals_common = {
                        'value_answer_id': ans.value_answer_id.id,
                        'value_text_box': ans.value_text_box,
                        'partner_id': order.partner_id.id,
                    }

                    if rec:

                        diff = {k: v for k, v in vals_common.items() if v and rec[k] != v}
                        if diff:
                            to_update.append((rec, diff))
                    else:
                        to_create.append({
                            **vals_common,
                            'task_id': task.id,
                            'question_id': ans.question_id.id,
                        })

                if to_create:
                    FsmAnswer.create(to_create)
                for rec, vals in to_update:
                    rec.write(vals) 
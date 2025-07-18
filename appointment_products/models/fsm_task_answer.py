# -*- coding: utf-8 -*-
from odoo import fields, models, _


class FsmTaskAnswerInput(models.Model):
    _name = 'fsm.task.answer.input'
    _description = 'FSM Task Questions Answers'
    _rec_name = 'question_id'
    _order = 'id desc'

    task_id = fields.Many2one('project.task', string='Task', required=True, ondelete='cascade')
    question_id = fields.Many2one('appointment.question', string='Question', required=True, ondelete='cascade')
    value_answer_id = fields.Many2one('appointment.answer', string='Selected Answer', ondelete='restrict')
    value_text_box = fields.Text(string='Text Answer')
    partner_id = fields.Many2one('res.partner', string='Customer')
    question_type = fields.Selection(related='question_id.question_type', store=True, readonly=True)
    appointment_type_id = fields.Many2one(related='question_id.appointment_type_id', store=True, readonly=True)

    _sql_constraints = [
        ('value_check',
         "CHECK(value_answer_id IS NOT NULL OR COALESCE(value_text_box,'')!='')",
         _('An answer must have a predefined value or a text value.')),
    ]


class ProjectTask(models.Model):
    _inherit = 'project.task'

    fsm_question_ids = fields.One2many(
        'fsm.task.answer.input',
        'task_id',
        string='الأسئلة'
    )

    fsm_signature = fields.Binary(string='التوقيع', attachment=True) 
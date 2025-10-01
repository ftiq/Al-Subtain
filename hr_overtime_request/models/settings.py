# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    attendance_autogen_enabled = fields.Boolean(
        string='Auto-generate Overtime Requests from Attendance',
        config_parameter='hr_overtime_request.attendance_autogen_enabled',
        default=True,
    )
    attendance_window_days = fields.Integer(
        string='Attendance Window (days)',
        config_parameter='hr_overtime_request.attendance_window_days',
        default=30,
        help='How many past days to scan for attendance overtime when generating requests.'
    )
    attendance_use_real = fields.Boolean(
        string='Use Real Overtime (with thresholds)',
        config_parameter='hr_overtime_request.attendance_use_real',
        default=True,
        help='If enabled, use duration_real from attendance overtime instead of duration.'
    )

# -*- coding: utf-8 -*-
{
    "name": "FTIQ Work Entry Request",
    "version": "1.0.0",
    "author": "FTIQ",
    "website": "https://example.com",
    "license": "LGPL-3",
    "category": "Human Resources",
    "summary": "Unified Work Entry Requests with Approval Rules (Odoo 18)",
    "depends": ["hr", "hr_attendance", "hr_holidays", "hr_work_entry", "approvals", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/work_entry_request_views.xml",
        "data/ir_cron.xml",
        "data/mail_template.xml",
    ],
    "application": True,
    "installable": True,
}

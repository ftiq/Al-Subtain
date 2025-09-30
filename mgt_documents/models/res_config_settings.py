# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    

    documents_approvals_settings = fields.Boolean(
        string='Enable document approvals',
        config_parameter='mgt_documents.documents_approvals_settings',
        help='Enable or disable document approvals'
    )
    

    documents_auto_archive_enabled = fields.Boolean(
        string='Enable automatic archiving',
        config_parameter='mgt_documents.auto_archive_enabled',
        help='Enable or disable automatic archiving of documents'
    )
    
    documents_auto_archive_days = fields.Integer(
        string='Number of days for automatic archiving',
        config_parameter='mgt_documents.auto_archive_days',
        default=365,
        help='Number of days after approval for automatic archiving of documents'
    )
    

    documents_notification_enabled = fields.Boolean(
        string='Enable document notifications',
        config_parameter='mgt_documents.notification_enabled',
        default=True,
        help='Enable or disable document notifications'
    )
    
    
    documents_escalation_enabled = fields.Boolean(
        string='Enable automatic escalation',
        config_parameter='mgt_documents.escalation_enabled',
        help='Enable or disable automatic escalation of document approvals'
    )
    
    documents_escalation_days = fields.Integer(
        string='Number of days for automatic escalation',
        config_parameter='mgt_documents.escalation_days',
        default=7,
        help='Number of days before automatic escalation of document approvals'
    )
    

    enable_hierarchical_approvals = fields.Boolean(
        string='Enable hierarchical approvals',
        config_parameter='mgt_documents.enable_hierarchical_approvals',
        default=True,
        help='Enable or disable hierarchical approvals'
    )
    
    max_approval_levels = fields.Integer(
        string='Maximum approval levels',
        config_parameter='mgt_documents.max_approval_levels',
        default=5,
        help='Maximum number of approval levels in the hierarchical approval chain'
    )
    
    include_department_manager_first = fields.Boolean(
        string='Include department manager first',
        config_parameter='mgt_documents.include_department_manager_first',
        default=True,
        help='Include department manager first in the hierarchical approval chain'
    )
    
    @api.onchange('documents_approvals_settings')
    def _onchange_documents_approvals_settings(self):
        """Update related settings when document approvals settings change"""
        if not self.documents_approvals_settings:
            self.documents_escalation_enabled = False
            self.enable_hierarchical_approvals = False

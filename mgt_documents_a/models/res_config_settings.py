# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    

    documents_approvals_settings = fields.Boolean(
        string='تفعيل نظام الموافقات للوثائق',
        config_parameter='mgt_documents.documents_approvals_settings',
        help='تفعيل أو إلغاء تفعيل نظام الموافقات للوثائق'
    )
    

    documents_auto_archive_enabled = fields.Boolean(
        string='تفعيل الأرشفة التلقائية',
        config_parameter='mgt_documents.auto_archive_enabled',
        help='تفعيل الأرشفة التلقائية للوثائق المعتمدة'
    )
    
    documents_auto_archive_days = fields.Integer(
        string='عدد أيام الأرشفة التلقائية',
        config_parameter='mgt_documents.auto_archive_days',
        default=365,
        help='عدد الأيام بعد الاعتماد لأرشفة الوثيقة تلقائياً'
    )
    

    documents_notification_enabled = fields.Boolean(
        string='تفعيل إشعارات الوثائق',
        config_parameter='mgt_documents.notification_enabled',
        default=True,
        help='إرسال إشعارات للمستخدمين عند تغيير حالة الوثائق'
    )
    
    
    documents_escalation_enabled = fields.Boolean(
        string='تفعيل التصعيد التلقائي',
        config_parameter='mgt_documents.escalation_enabled',
        help='تصعيد طلبات الموافقة المعلقة تلقائياً'
    )
    
    documents_escalation_days = fields.Integer(
        string='أيام التصعيد',
        config_parameter='mgt_documents.escalation_days',
        default=7,
        help='عدد الأيام قبل تصعيد طلب الموافقة المعلق'
    )
    

    enable_hierarchical_approvals = fields.Boolean(
        string='تفعيل الموافقات الهرمية',
        config_parameter='mgt_documents.enable_hierarchical_approvals',
        default=True,
        help='تفعيل النظام الهرمي التلقائي للموافقات'
    )
    
    max_approval_levels = fields.Integer(
        string='الحد الأقصى لمستويات الموافقة',
        config_parameter='mgt_documents.max_approval_levels',
        default=5,
        help='الحد الأقصى لعدد مستويات الموافقة في السلسلة الهرمية'
    )
    
    include_department_manager_first = fields.Boolean(
        string='إدراج مدير القسم أولاً',
        config_parameter='mgt_documents.include_department_manager_first',
        default=True,
        help='بدء السلسلة الهرمية بمدير القسم'
    )
    
    @api.onchange('documents_approvals_settings')
    def _onchange_documents_approvals_settings(self):
        """تحديث الإعدادات المرتبطة عند تغيير إعدادات الموافقات"""
        if not self.documents_approvals_settings:
            self.documents_escalation_enabled = False
            self.enable_hierarchical_approvals = False

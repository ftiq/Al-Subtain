# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class LabDashboardStats(models.Model):
    """
    موديل لحفظ وحساب إحصائيات المختبر لتحسين أداء لوحة المعلومات
    """
    _name = 'lab.dashboard.stats'
    _description = 'Lab Dashboard Statistics'
    _order = 'create_date desc'


    name = fields.Char('اسم الإحصائية', required=True)
    date_from = fields.Date('من تاريخ', required=True)
    date_to = fields.Date('إلى تاريخ', required=True)
    

    total_samples = fields.Integer('إجمالي العينات')
    draft_samples = fields.Integer('عينات مسودة')
    received_samples = fields.Integer('عينات مستلمة')
    testing_samples = fields.Integer('عينات قيد الفحص')
    completed_samples = fields.Integer('عينات مكتملة')
    rejected_samples = fields.Integer('عينات مرفوضة')
    

    total_results = fields.Integer('إجمالي النتائج')
    passed_results = fields.Integer('نتائج نجح')
    failed_results = fields.Integer('نتائج فشل')
    pending_results = fields.Integer('نتائج معلقة')
    

    pass_rate = fields.Float('معدل النجاح (%)', digits=(5, 2))
    fail_rate = fields.Float('معدل الفشل (%)', digits=(5, 2))
    completion_rate = fields.Float('معدل الإكمال (%)', digits=(5, 2))
    

    avg_processing_time = fields.Float('متوسط وقت المعالجة (أيام)', digits=(5, 2))
    overdue_tests = fields.Integer('فحوصات متأخرة')
    today_tests = fields.Integer('فحوصات اليوم')
    

    active_templates = fields.Integer('قوالب نشطة')
    most_used_template_id = fields.Many2one('lab.test.template', 'القالب الأكثر استخداماً')
    

    quality_alerts = fields.Integer('تنبيهات الجودة')
    

    company_id = fields.Many2one('res.company', 'الشركة', required=True, default=lambda self: self.env.company)
    

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('computed', 'محسوبة'),
        ('archived', 'مؤرشفة')
    ], 'الحالة', default='draft')
    

    detailed_data = fields.Text('بيانات تفصيلية (JSON)')
    
    @api.model
    def compute_daily_stats(self):
        """
        حساب الإحصائيات اليومية
        """
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        

        existing_stats = self.search([
            ('date_from', '=', today),
            ('date_to', '=', today),
            ('company_id', '=', self.env.company.id)
        ])
        
        if existing_stats:
            stats = existing_stats[0]
        else:
            stats = self.create({
                'name': f'إحصائيات يوم {today}',
                'date_from': today,
                'date_to': today,
                'company_id': self.env.company.id
            })
        

        stats._compute_sample_stats()
        stats._compute_result_stats()
        stats._compute_performance_rates()
        stats._compute_time_stats()
        stats._compute_template_stats()
        stats._compute_quality_alerts()
        
        stats.state = 'computed'
        
        return stats
    
    def _compute_sample_stats(self):
        """
        حساب إحصائيات العينات
        """
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]
        
        samples = self.env['lab.sample'].search(domain)
        
        self.total_samples = len(samples)
        self.draft_samples = len(samples.filtered(lambda s: s.state == 'draft'))
        self.received_samples = len(samples.filtered(lambda s: s.state == 'received'))
        self.testing_samples = len(samples.filtered(lambda s: s.state == 'testing'))
        self.completed_samples = len(samples.filtered(lambda s: s.state == 'completed'))
        self.rejected_samples = len(samples.filtered(lambda s: s.state == 'rejected'))
    
    def _compute_result_stats(self):
        """
        حساب إحصائيات النتائج
        """
        domain = [
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]
        
        results = self.env['lab.result.set'].search(domain)
        
        self.total_results = len(results)
        self.passed_results = len(results.filtered(lambda r: r.overall_result == 'pass'))
        self.failed_results = len(results.filtered(lambda r: r.overall_result == 'fail'))
        self.pending_results = len(results.filtered(lambda r: r.overall_result == 'pending'))
    
    def _compute_performance_rates(self):
        """
        حساب معدلات الأداء
        """
        if self.total_results > 0:
            self.pass_rate = (self.passed_results / self.total_results) * 100
            self.fail_rate = (self.failed_results / self.total_results) * 100
        else:
            self.pass_rate = 0
            self.fail_rate = 0
        
        if self.total_samples > 0:
            self.completion_rate = (self.completed_samples / self.total_samples) * 100
        else:
            self.completion_rate = 0
    
    def _compute_time_stats(self):
        """
        حساب إحصائيات الوقت
        """

        completed_samples = self.env['lab.sample'].search([
            ('state', '=', 'completed'),
            ('received_date', '!=', False),
            ('write_date', '>=', self.date_from),
            ('write_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ])
        
        if completed_samples:
            total_time = sum([
                (fields.Datetime.from_string(sample.write_date) - 
                 fields.Datetime.from_string(sample.received_date)).days
                for sample in completed_samples
                if sample.received_date and sample.write_date
            ])
            self.avg_processing_time = total_time / len(completed_samples)
        else:
            self.avg_processing_time = 0
        

        self.overdue_tests = self.env['lab.sample'].search_count([
            ('activity_state', '=', 'overdue'),
            ('company_id', '=', self.company_id.id)
        ])
        

        today = fields.Date.today()
        self.today_tests = self.env['lab.sample'].search_count([
            ('create_date', '>=', today),
            ('create_date', '<', today + timedelta(days=1)),
            ('company_id', '=', self.company_id.id)
        ])
    
    def _compute_template_stats(self):
        """
        حساب إحصائيات القوالب
        """
        self.active_templates = self.env['lab.test.template'].search_count([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id)
        ])
        

        template_usage = self.env['lab.sample'].read_group(
            domain=[
                ('lab_test_template_id', '!=', False),
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id)
            ],
            fields=['lab_test_template_id'],
            groupby=['lab_test_template_id'],
            orderby='lab_test_template_id_count desc',
            limit=1
        )
        
        if template_usage:
            self.most_used_template_id = template_usage[0]['lab_test_template_id'][0]
    
    def _compute_quality_alerts(self):
        """
        حساب تنبيهات الجودة
        """
        try:
            self.quality_alerts = self.env['quality.alert'].search_count([
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
                ('company_id', '=', self.company_id.id)
            ])
        except Exception as e:
            _logger.warning(f"Quality module not available: {e}")
            self.quality_alerts = 0
    
    @api.model
    def get_dashboard_data(self):
        """
        الحصول على بيانات لوحة المعلومات
        """

        latest_stats = self.search([
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'computed')
        ], limit=1)
        
        if not latest_stats:

            latest_stats = self.compute_daily_stats()
        

        week_ago = fields.Date.today() - timedelta(days=7)
        month_ago = fields.Date.today() - timedelta(days=30)
        
        week_samples = self.env['lab.sample'].search_count([
            ('create_date', '>=', week_ago),
            ('company_id', '=', self.env.company.id)
        ])
        
        month_samples = self.env['lab.sample'].search_count([
            ('create_date', '>=', month_ago),
            ('company_id', '=', self.env.company.id)
        ])
        
        return {
            'totalSamples': latest_stats.total_samples,
            'pendingSamples': latest_stats.received_samples,
            'testingSamples': latest_stats.testing_samples,
            'completedSamples': latest_stats.completed_samples,
            'rejectedSamples': latest_stats.rejected_samples,
            'totalResults': latest_stats.total_results,
            'passedResults': latest_stats.passed_results,
            'failedResults': latest_stats.failed_results,
            'pendingResults': latest_stats.pending_results,
            'passRate': latest_stats.pass_rate,
            'failRate': latest_stats.fail_rate,
            'avgProcessingTime': latest_stats.avg_processing_time,
            'overdueTests': latest_stats.overdue_tests,
            'todayTests': latest_stats.today_tests,
            'thisWeekSamples': week_samples,
            'thisMonthSamples': month_samples,
            'activeTemplates': latest_stats.active_templates,
            'qualityAlerts': latest_stats.quality_alerts,
        }
    
    @api.model
    def get_trend_data(self, period='week'):
        """
        الحصول على بيانات الاتجاهات
        """
        if period == 'week':
            days = 7
        elif period == 'month':
            days = 30
        else:
            days = 7
        
        start_date = fields.Date.today() - timedelta(days=days)
        
        trends = self.search([
            ('date_from', '>=', start_date),
            ('company_id', '=', self.env.company.id),
            ('state', '=', 'computed')
        ], order='date_from asc')
        
        return [{
            'date': trend.date_from,
            'samples': trend.total_samples,
            'passed': trend.passed_results,
            'failed': trend.failed_results,
            'completion_rate': trend.completion_rate
        } for trend in trends]
    
    @api.model
    def cleanup_old_stats(self):
        """
        تنظيف الإحصائيات القديمة (أكثر من 3 أشهر)
        """
        cutoff_date = fields.Date.today() - timedelta(days=90)
        old_stats = self.search([
            ('create_date', '<', cutoff_date),
            ('state', '!=', 'archived')
        ])
        
        old_stats.write({'state': 'archived'})
        
        return len(old_stats)
    
    def action_recompute(self):
        """
        إعادة حساب الإحصائيات
        """
        self.ensure_one()
        self._compute_sample_stats()
        self._compute_result_stats()
        self._compute_performance_rates()
        self._compute_time_stats()
        self._compute_template_stats()
        self._compute_quality_alerts()
        self.state = 'computed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('تم إعادة حساب الإحصائيات بنجاح'),
                'type': 'success',
                'sticky': False,
            }
        } 
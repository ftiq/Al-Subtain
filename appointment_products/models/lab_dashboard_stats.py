# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class LabDashboardStats(models.Model):
    """
    Model to save and compute laboratory statistics to improve dashboard performance
    """
    _name = 'lab.dashboard.stats'
    _description = 'Lab Dashboard Statistics'
    _order = 'create_date desc'


    name = fields.Char('Statistic Name', required=True)
    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', required=True)
    

    total_samples = fields.Integer('Total Samples')
    draft_samples = fields.Integer('Draft Samples')
    received_samples = fields.Integer('Received Samples')
    testing_samples = fields.Integer('Testing Samples')
    completed_samples = fields.Integer('Completed Samples')
    rejected_samples = fields.Integer('Rejected Samples')
    

    total_results = fields.Integer('Total Results')
    passed_results = fields.Integer('Passed Results')
    failed_results = fields.Integer('Failed Results')
    pending_results = fields.Integer('Pending Results')
    

    pass_rate = fields.Float('Pass Rate (%)', digits=(5, 2))
    fail_rate = fields.Float('Fail Rate (%)', digits=(5, 2))
    completion_rate = fields.Float('Completion Rate (%)', digits=(5, 2))
    

    avg_processing_time = fields.Float('Average Processing Time (days)', digits=(5, 2))
    overdue_tests = fields.Integer('Overdue Tests')
    today_tests = fields.Integer('Today Tests')
    

    active_templates = fields.Integer('Active Templates')
    most_used_template_id = fields.Many2one('lab.test.template', 'Most Used Template')
    

    quality_alerts = fields.Integer('Quality Alerts')
    

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    

    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('archived', 'Archived')
    ], 'State', default='draft')
    

    detailed_data = fields.Text('Detailed Data (JSON)')
    
    @api.model
    def compute_daily_stats(self):
        """
        Compute daily statistics
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
        Compute sample statistics
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
        Compute result statistics
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
        Compute performance rates
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
        Compute time statistics
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
        Compute template statistics
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
        Compute quality alerts
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
        Get dashboard data - use current stats directly
        """

        today = fields.Date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        

        total_samples = self.env['lab.sample'].search_count([])
        pending_samples = self.env['lab.sample'].search_count([('state', '=', 'received')])
        testing_samples = self.env['lab.sample'].search_count([('state', '=', 'testing')])
        completed_samples = self.env['lab.sample'].search_count([('state', '=', 'completed')])
        rejected_samples = self.env['lab.sample'].search_count([('state', '=', 'rejected')])
        
        total_results = self.env['lab.result.set'].search_count([])
        passed_results = self.env['lab.result.set'].search_count([('overall_result', '=', 'pass')])
        failed_results = self.env['lab.result.set'].search_count([('overall_result', '=', 'fail')])
        pending_results = self.env['lab.result.set'].search_count([('overall_result', '=', 'pending')])
        
        pass_rate = (passed_results / total_results * 100) if total_results > 0 else 0
        fail_rate = (failed_results / total_results * 100) if total_results > 0 else 0
        
        week_samples = self.env['lab.sample'].search_count([
            ('create_date', '>=', week_ago)
        ])
        
        month_samples = self.env['lab.sample'].search_count([
            ('create_date', '>=', month_ago)
        ])
        
        today_tests = self.env['lab.sample'].search_count([
            ('create_date', '>=', today)
        ])
        
        overdue_tests = self.env['lab.sample'].search_count([
            ('activity_state', '=', 'overdue')
        ])
        
        active_templates = self.env['lab.test.template'].search_count([('active', '=', True)])
        
        try:
            quality_alerts = self.env['quality.alert'].search_count([
                ('stage_id.name', '!=', 'Closed')
            ])
        except Exception:
            quality_alerts = 0
        

        avg_processing_time = self._calculate_avg_processing_time()
        
        return {
            'totalSamples': total_samples,
            'pendingSamples': pending_samples,
            'testingSamples': testing_samples,
            'completedSamples': completed_samples,
            'rejectedSamples': rejected_samples,
            'totalResults': total_results,
            'passedResults': passed_results,
            'failedResults': failed_results,
            'pendingResults': pending_results,
            'passRate': round(pass_rate, 1),
            'failRate': round(fail_rate, 1),
            'avgProcessingTime': avg_processing_time,
            'overdueTests': overdue_tests,
            'todayTests': today_tests,
            'thisWeekSamples': week_samples,
            'thisMonthSamples': month_samples,
            'activeTemplates': active_templates,
            'qualityAlerts': quality_alerts,
        }
    
    def _calculate_avg_processing_time(self):
        """
        Calculate average processing time for completed samples
        """
        completed_samples = self.env['lab.sample'].search([
            ('state', '=', 'completed'),
            ('received_date', '!=', False),
            ('write_date', '!=', False)
        ], limit=100)
        
        if not completed_samples:
            return 0
        
        total_time_days = 0
        count = 0
        
        for sample in completed_samples:
            if sample.received_date and sample.write_date:
                received_dt = fields.Datetime.from_string(sample.received_date)
                completed_dt = fields.Datetime.from_string(sample.write_date)
                time_diff = completed_dt - received_dt
                total_time_days += time_diff.days
                count += 1
        
        return round(total_time_days / count, 1) if count > 0 else 0
    
    @api.model
    def get_trend_data(self, period='week'):
        """
        Get trend data
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
        Clean up old stats (more than 3 months old)
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
        Recompute statistics
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
                'message': _('Statistics recomputed successfully'),
                'type': 'success',
                'sticky': False,
            }
        } 
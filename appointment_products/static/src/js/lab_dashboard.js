/** @odoo-module **/

import { Component, onWillStart, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LabDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        
        this.state = useState({
            kpiData: {
                totalSamples: 0,
                pendingSamples: 0,
                testingSamples: 0,
                completedSamples: 0,
                rejectedSamples: 0,
                totalResults: 0,
                passedResults: 0,
                failedResults: 0,
                pendingResults: 0,
                passRate: 0,
                failRate: 0,
                avgProcessingTime: 0,
                overdueTests: 0,
                todayTests: 0,
                thisWeekSamples: 0,
                thisMonthSamples: 0,
                activeTemplates: 0,
                qualityAlerts: 0,
                timersReady: 0
            },
            recentActivities: [],
            loading: true,
            error: null
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.setupAutoRefresh();
        });

        this.__destroyed = false;
        onWillUnmount(() => {
            this.__destroyed = true;
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    setupAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, 300000);
    }


    safeUpdateKpiData(data) {
        const defaultKpiData = {
            totalSamples: 0,
            pendingSamples: 0,
            testingSamples: 0,
            completedSamples: 0,
            rejectedSamples: 0,
            totalResults: 0,
            passedResults: 0,
            failedResults: 0,
            pendingResults: 0,
            passRate: 0,
            failRate: 0,
            avgProcessingTime: 0,
            overdueTests: 0,
            todayTests: 0,
            thisWeekSamples: 0,
            thisMonthSamples: 0,
            activeTemplates: 0,
            qualityAlerts: 0,
            timersReady: 0
        };
        

        return { ...defaultKpiData, ...data };
    }

    async loadDashboardData() {
        try {
            this.state.loading = true;
            this.state.error = null;

            try {
                const dashboardData = await this.orm.call(
                    "lab.dashboard.stats",
                    "get_dashboard_data",
                    []
                );
                
                const timersReady = await this.loadTimersReady();
                const recentActivities = await this.loadRecentActivities();
                
                if (!this.__destroyed) {
                    this.state.kpiData = this.safeUpdateKpiData(dashboardData);
                    this.state.kpiData.timersReady = timersReady;
                    this.state.recentActivities = recentActivities || [];
                }
            } catch (statsError) {
                console.warn("Dashboard stats model not available, using fallback:", statsError);
                await this.loadDashboardDataFallback();
            }
            
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.error = "حدث خطأ في تحميل البيانات";
            

            await this.loadDashboardDataFallback();
        } finally {
            if (this.__destroyed) return;
            this.state.loading = false;
        }
    }

    async loadDashboardDataFallback() {
        if (this.__destroyed) return;
        
        const sampleStats = await this.loadSampleStats();
        const resultStats = await this.loadResultStats();
        const qualityAlerts = await this.loadQualityAlerts();
        const timersReady = await this.loadTimersReady();
        const recentActivities = await this.loadRecentActivities();
        

        const passRate = resultStats.totalResults > 0 ? 
            (resultStats.passedResults / resultStats.totalResults * 100).toFixed(1) : 0;
        const failRate = resultStats.totalResults > 0 ? 
            (resultStats.failedResults / resultStats.totalResults * 100).toFixed(1) : 0;

        const avgProcessingTime = await this.calculateAvgProcessingTime();
        
        if (!this.__destroyed) {
            this.state.kpiData = this.safeUpdateKpiData({
                totalSamples: sampleStats.totalSamples,
                pendingSamples: sampleStats.pendingSamples,
                testingSamples: sampleStats.testingSamples,
                completedSamples: sampleStats.completedSamples,
                rejectedSamples: sampleStats.rejectedSamples,
                totalResults: resultStats.totalResults,
                passedResults: resultStats.passedResults,
                failedResults: resultStats.failedResults,
                pendingResults: resultStats.pendingResults,
                passRate: passRate,
                failRate: failRate,
                avgProcessingTime: avgProcessingTime,
                overdueTests: sampleStats.overdueTests,
                todayTests: sampleStats.todayTests,
                thisWeekSamples: sampleStats.thisWeekSamples,
                thisMonthSamples: sampleStats.thisMonthSamples,
                activeTemplates: await this.loadActiveTemplates(),
                qualityAlerts: qualityAlerts,
                timersReady: timersReady
            });
            
            this.state.recentActivities = recentActivities || [];
        }
    }

    async loadSampleStats() {
        const today = new Date().toISOString().split('T')[0];
        const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
        const monthAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

        const [
            totalSamples,
            pendingSamples,
            testingSamples,
            completedSamples,
            rejectedSamples,
            thisWeekSamples,
            thisMonthSamples,
            todayTests,
            overdueTests
        ] = await Promise.all([
            this.orm.searchCount("lab.sample", []),
            this.orm.searchCount("lab.sample", [["state", "=", "received"]]),
            this.orm.searchCount("lab.sample", [["state", "=", "testing"]]),
            this.orm.searchCount("lab.sample", [["state", "=", "completed"]]),
            this.orm.searchCount("lab.sample", [["state", "=", "rejected"]]),
            this.orm.searchCount("lab.sample", [["create_date", ">=", weekAgo]]),
            this.orm.searchCount("lab.sample", [["create_date", ">=", monthAgo]]),
            this.orm.searchCount("lab.sample", [["create_date", ">=", today]]),
            this.orm.searchCount("lab.sample", [["activity_state", "=", "overdue"]])
        ]);

        return {
            totalSamples,
            pendingSamples,
            testingSamples,
            completedSamples,
            rejectedSamples,
            thisWeekSamples,
            thisMonthSamples,
            todayTests,
            overdueTests
        };
    }

    async loadResultStats() {
        const [
            totalResults,
            passedResults,
            failedResults,
            pendingResults
        ] = await Promise.all([
            this.orm.searchCount("lab.result.set", []),
            this.orm.searchCount("lab.result.set", [["overall_result", "=", "pass"]]),
            this.orm.searchCount("lab.result.set", [["overall_result", "=", "fail"]]),
            this.orm.searchCount("lab.result.set", [["overall_result", "=", "pending"]])
        ]);

        return {
            totalResults,
            passedResults,
            failedResults,
            pendingResults
        };
    }

    async loadRecentActivities() {
        const recentSamples = await this.orm.searchRead(
            "lab.sample",
            [],
            ["name", "state", "create_date", "product_id"],
            { limit: 10, order: "create_date desc" }
        );
        return recentSamples;
    }

    async loadQualityAlerts() {
        try {
            const qualityAlerts = await this.orm.searchCount("quality.alert", [["stage_id.name", "!=", "Closed"]]);
            return qualityAlerts;
        } catch (error) {
            console.warn("Quality module not available:", error);
            return 0;
        }
    }

    async loadTimersReady() {
        const nowIso = new Date().toISOString().split(".")[0].replace('T', ' ');
        const count = await this.orm.searchCount(
            "lab.result.set",
            [
                ["timer_start", "!=", false],
                ["timer_ready", "<=", nowIso]
            ]
        );
        return count;
    }

    async loadActiveTemplates() {
        const count = await this.orm.searchCount("lab.test.template", [["active", "=", true]]);
        return count;
    }

    async calculateAvgProcessingTime() {
        try {
            const completedSamples = await this.orm.searchRead(
                "lab.sample",
                [["state", "=", "completed"], ["received_date", "!=", false]],
                ["received_date", "write_date"],
                { limit: 100 }
            );

            if (completedSamples.length === 0) return 0;

            const totalTime = completedSamples.reduce((sum, sample) => {
                const receivedDate = new Date(sample.received_date);
                const completedDate = new Date(sample.write_date);
                return sum + (completedDate - receivedDate);
            }, 0);

            const avgTimeMs = totalTime / completedSamples.length;
            return Math.round(avgTimeMs / (1000 * 60 * 60 * 24));
        } catch (error) {
            console.warn("Error calculating processing time:", error);
            return 0;
        }
    }

    async openSamples(domain = []) {
        console.log('Opening samples with domain:', domain);
        
        const action = {
            type: 'ir.actions.act_window',
            name: 'الفحوصات والنتائج',
            res_model: 'lab.sample',
            view_mode: 'kanban,list,form,calendar,pivot,graph,activity',
            views: [
                [false, 'kanban'],
                [false, 'list'],
                [false, 'form'],
                [false, 'calendar'],
                [false, 'pivot'],
                [false, 'graph'],
                [false, 'activity']
            ],
            target: 'current',
            context: {
                'search_default_group_by_state': 1
            }
        };
        

        if (Array.isArray(domain) && domain.length > 0) {
            action.domain = domain;
        }
        
        console.log('Executing action:', action);
        return this.actionService.doAction(action);
    }

    async openResults(domain = []) {
        const action = {
            type: "ir.actions.act_window",
            name: "نتائج الفحوصات",
            res_model: "lab.result.set",
            view_mode: "list,form",
            views: [[false,'list'],[false,'form']],
            target: "current"
        };
        

        if (Array.isArray(domain) && domain.length > 0) {
            action.domain = domain;
        }
        
        return this.actionService.doAction(action);
    }

    getStateColor(state) {
        const colors = {
            'draft': 'secondary',
            'received': 'warning',
            'testing': 'info',
            'completed': 'success',
            'rejected': 'danger'
        };
        return colors[state] || 'secondary';
    }

    getResultColor(result) {
        const colors = {
            'pass': 'success',
            'fail': 'danger',
            'pending': 'warning'
        };
        return colors[result] || 'secondary';
    }

    formatDate(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('ar-EG');
    }

    refreshDashboard() {
        this.loadDashboardData();
    }
}

LabDashboard.template = "appointment_products.LabDashboard";

registry.category("actions").add("lab_dashboard", LabDashboard); 
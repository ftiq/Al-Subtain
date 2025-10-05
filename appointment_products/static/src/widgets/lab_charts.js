/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const SIEVE_SIZES = [75, 50, 25, 9.5, 4.75, 2.36, 0.3, 0.075];
const PASS_CODES = {
    75: "PASS_75MM_PCT",
    50: "PASS_50MM_PCT",
    25: "PASS_25MM_PCT",
    9.5: "PASS_9_5MM_PCT",
    4.75: "PASS_4_75MM_PCT",
    2.36: "PASS_2_36MM_PCT",
    0.3: "PASS_0_3MM_PCT",
    0.075: "PASS_0_075MM_PCT",
};

function lr(x, y) {
    // simple linear regression y = a + b*x
    const n = Math.min(x.length, y.length);
    if (n < 2) return { a: 0, b: 0 };
    let sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (let i = 0; i < n; i++) {
        sx += x[i];
        sy += y[i];
        sxx += x[i] * x[i];
        sxy += x[i] * y[i];
    }
    const denom = n * sxx - sx * sx;
    if (denom === 0) return { a: 0, b: 0 };
    const b = (n * sxy - sx * sy) / denom;
    const a = (sy - b * sx) / n;
    return { a, b };
}

export class LabChart extends Component {
    static template = "appointment_products.LabChart";
    setup() {
        this.orm = useService("orm");
        this.state = useState({ loading: true, error: "", title: "", subtitle: "" });
        this.canvasRef = useRef("canvas");
        onMounted(() => this._init());
        onWillUnmount(() => { if (this.chart) { try { this.chart.destroy(); } catch(_){} } });
    }

    get _chartLib() {
        return window.Chart || null;
    }

    get _chartVersionMajor() {
        const C = this._chartLib;
        if (!C || !C.version) return null;
        const maj = parseInt(String(C.version).split(".")[0], 10);
        return Number.isFinite(maj) ? maj : null;
    }

    _normalizeConfigForV2(config) {
        // Transform a Chart.js v3/v4-style config into a v2-compatible one.
        try {
            const cfg = JSON.parse(JSON.stringify(config));
            cfg.options = cfg.options || {};

            // Map plugins -> v2 top-level options
            if (cfg.options.plugins) {
                const p = cfg.options.plugins;
                if (p.title) {
                    cfg.options.title = Object.assign({}, p.title);
                }
                if (p.tooltip || p.tooltips) {
                    cfg.options.tooltips = Object.assign({}, p.tooltip || p.tooltips);
                }
                if (p.legend && !cfg.options.legend) {
                    cfg.options.legend = Object.assign({}, p.legend);
                }
                delete cfg.options.plugins;
            }

            // Map scales x/y -> xAxes/yAxes
            if (cfg.options.scales) {
                const x = cfg.options.scales.x || cfg.options.scales["x-axis-0"]; // fallback
                const y = cfg.options.scales.y || cfg.options.scales["y-axis-0"]; // fallback
                const xAxes = [];
                const yAxes = [];
                if (x) {
                    const x2 = Object.assign({}, x);
                    if (x2.title) {
                        x2.scaleLabel = { display: !!x2.title.display, labelString: x2.title.text };
                        delete x2.title;
                    }
                    if (x2.min != null || x2.max != null || x2.beginAtZero != null) {
                        x2.ticks = Object.assign({}, x2.ticks || {});
                        if (x2.min != null) x2.ticks.min = x2.min;
                        if (x2.max != null) x2.ticks.max = x2.max;
                        if (x2.beginAtZero != null) x2.ticks.beginAtZero = x2.beginAtZero;
                        delete x2.min; delete x2.max; delete x2.beginAtZero;
                    }
                    xAxes.push(x2);
                }
                if (y) {
                    const y2 = Object.assign({}, y);
                    if (y2.title) {
                        y2.scaleLabel = { display: !!y2.title.display, labelString: y2.title.text };
                        delete y2.title;
                    }
                    if (y2.min != null || y2.max != null || y2.beginAtZero != null) {
                        y2.ticks = Object.assign({}, y2.ticks || {});
                        if (y2.min != null) y2.ticks.min = y2.min;
                        if (y2.max != null) y2.ticks.max = y2.max;
                        if (y2.beginAtZero != null) y2.ticks.beginAtZero = y2.beginAtZero;
                        delete y2.min; delete y2.max; delete y2.beginAtZero;
                    }
                    yAxes.push(y2);
                }
                cfg.options.scales = { xAxes, yAxes };
            }

            // Datasets: tension -> lineTension; drop parsing
            if (cfg.data && Array.isArray(cfg.data.datasets)) {
                for (const ds of cfg.data.datasets) {
                    if (ds.tension != null && ds.lineTension == null) {
                        ds.lineTension = ds.tension;
                    }
                    if ("parsing" in ds) delete ds.parsing;
                }
            }

            return cfg;
        } catch (_e) {
            return config;
        }
    }

    async _ensureChartLoaded() {
        if (this._chartLib) return true;
        // Dynamically load Chart.js (UMD) if not present
        const url = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js";
        if (document.querySelector(`script[src='${url}']`)) {
            // Already loading, wait a bit
            await new Promise((r) => setTimeout(r, 300));
            return !!this._chartLib;
        }
        await new Promise((resolve, reject) => {
            const s = document.createElement("script");
            s.src = url;
            s.async = true;
            s.onload = () => resolve();
            s.onerror = () => reject(new Error("Failed to load Chart.js"));
            document.head.appendChild(s);
        });
        return !!this._chartLib;
    }

    async _init() {
        if (!(await this._ensureChartLoaded())) {
            this.state.error = "تعذّر تحميل مكتبة Chart.js";
            this.state.loading = false;
            return;
        }
        try {
            let type = this.props.type;
            if (!type) {
                // Fallback: infer from result set template code
                try {
                    const rsId = this.props.recordId;
                    if (rsId) {
                        const recs = await this.orm.read("lab.result.set", [rsId], ["template_id"]);
                        const tplId = recs && recs[0] && recs[0].template_id;
                        if (tplId && Array.isArray(tplId)) {
                            const tpl = await this.orm.read("lab.test.template", [tplId[0]], ["code"]);
                            const code = tpl && tpl[0] && (tpl[0].code || "").toUpperCase();
                            if (code === "AGG_PROCTOR_D698") type = "proctor";
                            else if (code === "AGG_QUALITY_SIEVE") type = "agg_sieve";
                            else if (code === "LL_PL_D4318") type = "ll_pl";
                        }
                    }
                } catch (infErr) {
                    // eslint-disable-next-line no-console
                    console.debug("LabChart: infer type failed", infErr);
                }
            }
            type = type || "proctor";
            // eslint-disable-next-line no-console
            console.debug("LabChart: rendering type=", type, "props=", this.props);
            if (type === "proctor") {
                await this._renderProctor();
            } else if (type === "agg_sieve") {
                await this._renderAggSieve();
            } else if (type === "ll_pl") {
                await this._renderLLPL();
            }
        } catch (e) {
            // eslint-disable-next-line no-console
            console.error("LabChart render error", e);
            this.state.error = (e && e.message) || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    async _searchLines(codes) {
        const rsId = this.props.recordId;
        if (!rsId) return [];
        const domain = [["result_set_id", "=", rsId], ["criterion_id.code", "in", codes]];
        const fields = ["criterion_code", "criterion_id", "sample_no", "value_numeric"]; 
        const lines = await this.orm.searchRead("lab.result.line", domain, fields);
        return lines || [];
    }

    _destroyChart() {
        if (this.chart) {
            try { this.chart.destroy(); } catch(_){}
            this.chart = null;
        }
    }

    _makeChart(config) {
        const el = this.canvasRef && this.canvasRef.el;
        if (!el) {
            // wait a tick for DOM to be ready (e.g., tab just switched)
            this._retryCount = (this._retryCount || 0) + 1;
            if (this._retryCount <= 5) {
                setTimeout(() => this._makeChart(config), 80);
                return;
            }
            this.state.error = "Canvas not ready";
            return;
        }
        const ctx = el.getContext("2d");
        if (!ctx) {
            this.state.error = "Canvas 2D context unavailable";
            return;
        }
        this._destroyChart();
        let finalCfg = config;
        const major = this._chartVersionMajor;
        if (major && major < 3) {
            finalCfg = this._normalizeConfigForV2(config);
        }
        this.chart = new this._chartLib(ctx, finalCfg);
    }

    async _renderProctor() {
        this.state.title = "منحنى الرطوبة - الكثافة (بروكتر)";
        const lines = await this._searchLines(["MOISTURE_CONTENT", "DRY_DENSITY_KG_M3"]);
        const map = {};
        for (const l of lines) {
            const code = l.criterion_code || ((l.criterion_id && l.criterion_id[1]) || "");
            const v = Number(l.value_numeric);
            map[l.sample_no] = map[l.sample_no] || {};
            map[l.sample_no][code] = Number.isFinite(v) ? v : 0;
        }
        const points = [];
        let best = { y: -Infinity, x: 0 };
        for (const k of Object.keys(map).sort((a,b)=>Number(a)-Number(b))) {
            const mc = map[k].MOISTURE_CONTENT;
            const dd = map[k].DRY_DENSITY_KG_M3;
            if (mc != null && dd != null && isFinite(mc) && isFinite(dd) && dd > 0) {
                points.push({ x: Number(mc), y: Number(dd) });
                if (dd > best.y) best = { x: mc, y: dd };
            }
        }
        points.sort((a,b)=>a.x-b.x);
        if (!points.length) {
            this.state.error = "لا توجد نقاط صالحة للرسم. تحقق من قيم الكثافة الجافة (يجب أن تكون > 0) والمحتوى الرطوبي.";
            // eslint-disable-next-line no-console
            console.debug("LabChart[proctor]: lines=", lines);
        }
        const config = {
            type: "line",
            data: {
                datasets: [
                    {
                        label: "Moisture-Density",
                        data: points,
                        parsing: false,
                        borderColor: "#6f42c1",
                        backgroundColor: "rgba(111,66,193,0.2)",
                        tension: 0.3,
                        pointRadius: 4,
                    },
                    {
                        label: "MDD (OMC)",
                        type: "scatter",
                        data: best.y > 0 ? [{ x: best.x, y: best.y }] : [],
                        pointBackgroundColor: "#dc3545",
                        pointBorderColor: "#dc3545",
                        pointRadius: 6,
                        showLine: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: { mode: "nearest", intersect: false },
                    title: { display: true, text: "Moisture vs Dry Density" },
                },
                scales: {
                    x: { title: { display: true, text: "% الرطوبة" } },
                    y: { title: { display: true, text: "الكثافة الجافة (كغم/م³)" }, beginAtZero: false },
                },
            },
        };
        this._makeChart(config);
    }

    async _renderAggSieve() {
        this.state.title = "منحنى التدرج (Sieve Passing %)";
        const codes = SIEVE_SIZES.map((s) => PASS_CODES[s]);
        const lines = await this._searchLines(codes);
        const byCode = {};
        for (const l of lines) {
            const code = l.criterion_code || ((l.criterion_id && l.criterion_id[1]) || "");
            const v = Number(l.value_numeric);
            byCode[code] = Number.isFinite(v) ? v : null;
        }
        const points = [];
        for (const size of SIEVE_SIZES) {
            const val = byCode[PASS_CODES[size]];
            if (val != null && isFinite(val)) points.push({ x: size, y: Number(val) });
        }
        const config = {
            type: "line",
            data: {
                datasets: [
                    {
                        label: "% Passing",
                        data: points,
                        parsing: false,
                        borderColor: "#198754",
                        backgroundColor: "rgba(25,135,84,0.15)",
                        pointBackgroundColor: "#198754",
                        tension: 0,
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: { mode: "nearest", intersect: false },
                    title: { display: true, text: "Sieve Size (mm) vs % Passing" },
                },
                scales: {
                    x: {
                        type: "logarithmic",
                        title: { display: true, text: "Sieve (mm)" },
                        ticks: {
                            callback: (v) => {
                                const lbls = [0.075, 0.3, 2.36, 4.75, 9.5, 25, 50, 75];
                                return lbls.includes(Number(v)) ? String(v) : null;
                            },
                        },
                    },
                    y: {
                        title: { display: true, text: "% Passing" },
                        min: 0, max: 100,
                    },
                },
            },
        };
        this._makeChart(config);
    }

    async _renderLLPL() {
        this.state.title = "منحنى الجريان (LL) وحد اللدونة (PL)";
        const lines = await this._searchLines(["NB_LL", "MC_LL_PERCENT", "LL_PERCENT", "PL_PERCENT"]);
        const map = {};
        let LL = null, PL = null;
        for (const l of lines) {
            const code = l.criterion_code || ((l.criterion_id && l.criterion_id[1]) || "");
            if (code === "LL_PERCENT") LL = l.value_numeric;
            else if (code === "PL_PERCENT") PL = l.value_numeric;
            else {
                map[l.sample_no] = map[l.sample_no] || {};
                const v = Number(l.value_numeric);
                map[l.sample_no][code] = Number.isFinite(v) ? v : 0;
            }
        }
        const pts = [];
        const xs = [], ys = [];
        for (const k of Object.keys(map)) {
            const n = map[k].NB_LL;
            const mc = map[k].MC_LL_PERCENT;
            if (n && mc != null && n > 0) {
                pts.push({ x: n, y: mc });
                xs.push(Math.log10(n));
                ys.push(mc);
            }
        }
        pts.sort((a,b)=>a.x-b.x);
        let regLine = [];
        let ll25 = null;
        if (xs.length >= 2) {
            const { a, b } = lr(xs, ys);
            const xMin = Math.min(...pts.map(p=>p.x));
            const xMax = Math.max(...pts.map(p=>p.x));
            const pred = (x) => a + b * Math.log10(x);
            regLine = [ { x: xMin, y: pred(xMin) }, { x: xMax, y: pred(xMax) } ];
            ll25 = { x: 25, y: pred(25) };
        }
        const datasets = [
            {
                label: "Flow curve points",
                data: pts,
                parsing: false,
                type: "scatter",
                borderColor: "#0d6efd",
                backgroundColor: "#0d6efd",
                pointRadius: 5,
            },
        ];
        if (!pts.length) {
            this.state.error = "لا توجد نقاط صالحة للرسم. أدخل قراءات عدد الطرقات (NB_LL) مع محتوى الرطوبة المحسوب.";
            // eslint-disable-next-line no-console
            console.debug("LabChart[ll_pl]: lines=", lines);
        }
        if (regLine.length) {
            datasets.push({ label: "Trend (log10 N)", data: regLine, parsing: false, type: "line", borderDash: [6,4], borderColor: "#0d6efd" });
        }
        if (ll25) {
            datasets.push({ label: "LL@25",
                data: [ ll25 ], type: "scatter", parsing: false,
                pointBackgroundColor: "#dc3545", pointBorderColor: "#dc3545", pointRadius: 6 });
        }
        if (PL != null && pts.length) {
            const xMin = Math.min(...pts.map(p=>p.x));
            const xMax = Math.max(...pts.map(p=>p.x));
            datasets.push({ label: "PL", data: [ {x:xMin, y: PL}, {x:xMax, y: PL} ], type: "line", borderColor: "#198754", borderDash: [4,4], parsing: false });
        }
        if (LL != null) {
            datasets.push({ label: "LL (manual)", data: [ { x: 25, y: LL } ], type: "scatter", parsing:false, pointBackgroundColor: "#ffc107", pointBorderColor: "#ffc107", pointRadius: 6 });
        }

        const config = {
            type: "scatter",
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    tooltip: { mode: "nearest", intersect: false },
                    title: { display: true, text: "No. of Blows (log) vs Moisture %" },
                },
                scales: {
                    x: { type: "logarithmic", title: { display: true, text: "عدد الطرقات" }, min: 10, max: Math.max(30, Math.max(...pts.map(p=>p.x), 26)) },
                    y: { title: { display: true, text: "% رطوبة" } },
                },
            },
        };
        this._makeChart(config);
    }
}

class LabChartField extends Component {
    static template = "appointment_products.LabChartField";
    static props = standardFieldProps;
    static components = { LabChart };

    setup() {}

    get recordId() {
        return this.props.record && this.props.record.resId;
    }

    get chartType() {
        const opt = this.props.options || {};
        return opt.type || "proctor";
    }

    get height() {
        const opt = this.props.options || {};
        return opt.height || 420;
    }
}

registry.category("fields").add("lab_chart", {
    component: LabChartField,
    supportedTypes: ["char", "text"],
});

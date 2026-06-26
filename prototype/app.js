// ─── INDUSTRY BENCHMARKS ─────────────────────────────────────────────────────
const INDUSTRY_BENCHMARKS = {
  retail: {
    label: "Retail",
    receivablesDays: 18, inventoryDays: 45, grossMargin: 0.32, currentRatio: 1.1,
    debtToEquity: 1.4, interestCoverage: 4.5, assetTurnover: 1.8, revenueGrowth: 0.05
  },
  technology: {
    label: "Technology",
    receivablesDays: 55, inventoryDays: 30, grossMargin: 0.58, currentRatio: 2.2,
    debtToEquity: 0.6, interestCoverage: 12.0, assetTurnover: 0.7, revenueGrowth: 0.14
  },
  manufacturing: {
    label: "Manufacturing",
    receivablesDays: 48, inventoryDays: 62, grossMargin: 0.28, currentRatio: 1.5,
    debtToEquity: 0.9, interestCoverage: 5.5, assetTurnover: 0.9, revenueGrowth: 0.04
  },
  financial: {
    label: "Financial Services",
    receivablesDays: 30, inventoryDays: 0, grossMargin: 0.45, currentRatio: 1.3,
    debtToEquity: 3.5, interestCoverage: 3.0, assetTurnover: 0.1, revenueGrowth: 0.07
  },
  healthcare: {
    label: "Healthcare",
    receivablesDays: 61, inventoryDays: 40, grossMargin: 0.52, currentRatio: 1.8,
    debtToEquity: 0.8, interestCoverage: 8.0, assetTurnover: 0.6, revenueGrowth: 0.09
  },
  energy: {
    label: "Energy",
    receivablesDays: 42, inventoryDays: 35, grossMargin: 0.22, currentRatio: 1.2,
    debtToEquity: 1.1, interestCoverage: 6.5, assetTurnover: 0.5, revenueGrowth: 0.03
  }
};

// ─── BENEISH M-SCORE ─────────────────────────────────────────────────────────
function calcBeneish(curr, prev) {
  if (!prev) return null;
  const safe = (n, d) => d === 0 ? 1 : n / d;

  // DSRI: Days Sales in Receivables Index
  const dsri = safe(
    (curr.receivables / curr.revenue) / safe(prev.receivables, prev.revenue), 1
  );
  // GMI: Gross Margin Index
  const prevGM = safe(prev.revenue - prev.cogs, prev.revenue);
  const currGM = safe(curr.revenue - curr.cogs, curr.revenue);
  const gmi = safe(prevGM, currGM);
  // AQI: Asset Quality Index
  const prevAQ = safe(prev.totalAssets - prev.currentAssets - prev.ppe, prev.totalAssets);
  const currAQ = safe(curr.totalAssets - curr.currentAssets - curr.ppe, curr.totalAssets);
  const aqi = safe(currAQ, prevAQ);
  // SGI: Sales Growth Index
  const sgi = safe(curr.revenue, prev.revenue);
  // DEPI: Depreciation Index
  const prevDepi = safe(prev.depreciation, prev.depreciation + prev.ppe);
  const currDepi = safe(curr.depreciation, curr.depreciation + curr.ppe);
  const depi = safe(prevDepi, currDepi);
  // SGAI: SGA Expense Index
  const sgai = safe(
    safe(curr.sga, curr.revenue),
    safe(prev.sga, prev.revenue)
  );
  // TATA: Total Accruals to Total Assets
  const tata = safe(
    (curr.netIncome - curr.operatingCashFlow),
    curr.totalAssets
  );
  // LVGI: Leverage Index
  const prevLev = safe(prev.totalDebt, prev.totalAssets);
  const currLev = safe(curr.totalDebt, curr.totalAssets);
  const lvgi = safe(currLev, prevLev);

  const m = -4.84 + 0.92*dsri + 0.528*gmi + 0.404*aqi + 0.892*sgi
            + 0.115*depi - 0.172*sgai + 4.679*tata - 0.327*lvgi;

  // fraud probability using logistic function approximation
  const fraudProb = 1 / (1 + Math.exp(-m - 0.5));

  return {
    score: +m.toFixed(3),
    fraudProb: +(fraudProb * 100).toFixed(1),
    isManipulator: m > -1.78,
    components: {
      DSRI: +dsri.toFixed(3), GMI: +gmi.toFixed(3), AQI: +aqi.toFixed(3),
      SGI: +sgi.toFixed(3), DEPI: +depi.toFixed(3), SGAI: +sgai.toFixed(3),
      TATA: +tata.toFixed(3), LVGI: +lvgi.toFixed(3)
    }
  };
}

// ─── FINANCIAL RATIOS ────────────────────────────────────────────────────────
function calcRatios(data) {
  const safe = (n, d) => d === 0 ? null : +(n / d).toFixed(2);
  return {
    receivablesDays: safe(data.receivables * 365, data.revenue),
    inventoryDays: safe(data.inventory * 365, data.cogs || data.revenue * 0.7),
    grossMargin: safe(data.revenue - data.cogs, data.revenue),
    currentRatio: safe(data.currentAssets, data.currentLiabilities),
    debtToEquity: safe(data.totalDebt, data.equity),
    interestCoverage: safe(data.ebit, data.interestExpense),
    assetTurnover: safe(data.revenue, data.totalAssets),
    revenueGrowth: data.prevRevenue ? safe(data.revenue - data.prevRevenue, data.prevRevenue) : null
  };
}

// ─── BENCHMARK COMPARISON ────────────────────────────────────────────────────
function benchmarkRatios(ratios, industry) {
  const bench = INDUSTRY_BENCHMARKS[industry];
  if (!bench) return [];
  const fmt = (v, decimals = 1) => v == null ? "N/A" : +v.toFixed(decimals);

  return [
    {
      label: "Receivables Days",
      company: ratios.receivablesDays,
      industry: bench.receivablesDays,
      higherIsBad: true,
      unit: "days",
      flag: ratios.receivablesDays > bench.receivablesDays * 1.3 ? "high" :
            ratios.receivablesDays > bench.receivablesDays * 1.1 ? "medium" : "ok"
    },
    {
      label: "Gross Margin",
      company: ratios.grossMargin != null ? +(ratios.grossMargin * 100).toFixed(1) : null,
      industry: +(bench.grossMargin * 100).toFixed(1),
      higherIsBad: false,
      unit: "%",
      flag: ratios.grossMargin < bench.grossMargin * 0.8 ? "high" :
            ratios.grossMargin < bench.grossMargin * 0.9 ? "medium" : "ok"
    },
    {
      label: "Current Ratio",
      company: ratios.currentRatio,
      industry: bench.currentRatio,
      higherIsBad: false,
      unit: "x",
      flag: ratios.currentRatio < 1.0 ? "high" : ratios.currentRatio < bench.currentRatio * 0.85 ? "medium" : "ok"
    },
    {
      label: "Debt / Equity",
      company: ratios.debtToEquity,
      industry: bench.debtToEquity,
      higherIsBad: true,
      unit: "x",
      flag: ratios.debtToEquity > bench.debtToEquity * 1.5 ? "high" :
            ratios.debtToEquity > bench.debtToEquity * 1.2 ? "medium" : "ok"
    },
    {
      label: "Interest Coverage",
      company: ratios.interestCoverage,
      industry: bench.interestCoverage,
      higherIsBad: false,
      unit: "x",
      flag: ratios.interestCoverage < 2.0 ? "high" : ratios.interestCoverage < bench.interestCoverage * 0.7 ? "medium" : "ok"
    },
    {
      label: "Asset Turnover",
      company: ratios.assetTurnover,
      industry: bench.assetTurnover,
      higherIsBad: false,
      unit: "x",
      flag: ratios.assetTurnover < bench.assetTurnover * 0.6 ? "medium" : "ok"
    }
  ];
}

// ─── CLAUDE API CALL ─────────────────────────────────────────────────────────
async function extractFinancialsWithClaude(pdfText, yearLabel) {
  const prompt = `You are an expert financial analyst. Extract key financial figures from this annual report text.

Return ONLY valid JSON with NO markdown, no explanation, no backticks. Use null for missing values. All monetary values in millions (same currency as the report).

Required JSON structure:
{
  "companyName": "string",
  "year": "${yearLabel}",
  "industry": "retail|technology|manufacturing|financial|healthcare|energy",
  "currency": "GBP|USD|EUR|etc",
  "revenue": number,
  "cogs": number,
  "grossProfit": number,
  "ebit": number,
  "netIncome": number,
  "operatingCashFlow": number,
  "depreciation": number,
  "sga": number,
  "interestExpense": number,
  "totalAssets": number,
  "currentAssets": number,
  "ppe": number,
  "receivables": number,
  "inventory": number,
  "currentLiabilities": number,
  "totalDebt": number,
  "equity": number,
  "redFlags": ["list", "of", "textual", "red", "flags", "you", "noticed"],
  "notes": "brief commentary on anything unusual in the accounting policies or notes"
}

Annual report text (first 12000 chars):
${pdfText.slice(0, 12000)}`;

  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      messages: [{ role: "user", content: prompt }]
    })
  });
  const data = await resp.json();
  const text = data.content?.[0]?.text || "{}";
  const clean = text.replace(/```json|```/g, "").trim();
  return JSON.parse(clean);
}

async function generateAuditSummary(financials, beneish, benchmarks, industry) {
  const flagged = benchmarks.filter(b => b.flag !== "ok").map(b =>
    `${b.label}: company=${b.company}${b.unit} vs industry avg ${b.industry}${b.unit}`
  ).join("; ");

  const prompt = `You are a senior auditor at a Big 4 firm writing a concise audit risk summary for a junior colleague.

Company: ${financials.companyName} (${financials.year})
Industry: ${industry}
Beneish M-Score: ${beneish?.score} (${beneish?.isManipulator ? "MANIPULATOR ZONE — above -1.78" : "non-manipulator zone"})
Fraud probability estimate: ${beneish?.fraudProb}%
Key benchmark deviations: ${flagged || "none significant"}
Textual red flags found: ${(financials.redFlags || []).join("; ")}
Analyst notes: ${financials.notes || "none"}

Write a 3-4 sentence plain English summary as a senior auditor would. Be direct and analytical. Mention the most important risk(s) first. Do not use bullet points. Do not start with "This company..." — start with the most important finding.`;

  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      messages: [{ role: "user", content: prompt }]
    })
  });
  const data = await resp.json();
  return data.content?.[0]?.text || "";
}

// ─── STATE ───────────────────────────────────────────────────────────────────
let state = {
  reports: [],       // [{year, financials, beneish, ratios, benchmarks}]
  activeYear: null,
  industry: "retail",
  summary: "",
  charts: {}
};

// ─── UTILS ───────────────────────────────────────────────────────────────────
async function readPDF(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const typedArray = new Uint8Array(e.target.result);
        const pdf = await pdfjsLib.getDocument(typedArray).promise;
        let text = "";
        for (let i = 1; i <= Math.min(pdf.numPages, 40); i++) {
          const page = await pdf.getPage(i);
          const content = await page.getTextContent();
          text += content.items.map(s => s.str).join(" ") + "\n";
        }
        resolve(text);
      } catch (err) { reject(err); }
    };
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

function setProgress(steps, activeIdx) {
  steps.forEach((s, i) => {
    const el = document.querySelector(`[data-step="${i}"]`);
    if (!el) return;
    el.className = "progress-step " + (i < activeIdx ? "done" : i === activeIdx ? "active" : "");
  });
}

// ─── RENDER ──────────────────────────────────────────────────────────────────
function renderMetricCards(beneish, ratios) {
  const scoreColor = !beneish ? "var(--text)" :
    beneish.isManipulator ? "var(--red)" :
    beneish.fraudProb > 30 ? "var(--amber)" : "var(--green)";
  const cardClass = !beneish ? "" :
    beneish.isManipulator ? "danger" : beneish.fraudProb > 30 ? "warn" : "ok";

  return `
  <div class="results-grid">
    <div class="metric-card ${cardClass}">
      <div class="metric-label">Beneish M-Score</div>
      <div class="metric-value" style="color:${scoreColor}">${beneish ? beneish.score : "—"}</div>
      <div class="metric-sub">${beneish ? (beneish.isManipulator ? "⚠ Manipulator zone (> −1.78)" : "✓ Non-manipulator zone") : "Requires 2 years of data"}</div>
    </div>
    <div class="metric-card ${cardClass}">
      <div class="metric-label">Fraud Probability</div>
      <div class="metric-value" style="color:${scoreColor}">${beneish ? beneish.fraudProb + "%" : "—"}</div>
      <div class="metric-sub">${beneish ? "Model-estimated likelihood" : "Upload prior year for score"}</div>
    </div>
    <div class="metric-card ${ratios.grossMargin < 0.2 ? "danger" : ratios.grossMargin < 0.35 ? "warn" : "ok"}">
      <div class="metric-label">Gross Margin</div>
      <div class="metric-value">${ratios.grossMargin != null ? (ratios.grossMargin * 100).toFixed(1) + "%" : "—"}</div>
      <div class="metric-sub">Profitability indicator</div>
    </div>
    <div class="metric-card ${ratios.currentRatio < 1 ? "danger" : ratios.currentRatio < 1.5 ? "warn" : "ok"}">
      <div class="metric-label">Current Ratio</div>
      <div class="metric-value">${ratios.currentRatio != null ? ratios.currentRatio + "x" : "—"}</div>
      <div class="metric-sub">Short-term liquidity</div>
    </div>
    <div class="metric-card ${ratios.receivablesDays > 90 ? "danger" : ratios.receivablesDays > 60 ? "warn" : "ok"}">
      <div class="metric-label">Receivables Days</div>
      <div class="metric-value">${ratios.receivablesDays != null ? ratios.receivablesDays + "d" : "—"}</div>
      <div class="metric-sub">Cash collection speed</div>
    </div>
    <div class="metric-card ${ratios.interestCoverage && ratios.interestCoverage < 2 ? "danger" : ratios.interestCoverage && ratios.interestCoverage < 3 ? "warn" : "ok"}">
      <div class="metric-label">Interest Coverage</div>
      <div class="metric-value">${ratios.interestCoverage != null ? ratios.interestCoverage + "x" : "—"}</div>
      <div class="metric-sub">Debt service ability</div>
    </div>
  </div>`;
}

function renderFindings(financials, beneish, benchmarks) {
  const findings = [];

  if (beneish?.isManipulator) {
    findings.push({ level: "high", icon: "🚨", title: "Earnings manipulation likely", body: `Beneish M-Score of ${beneish.score} exceeds the −1.78 threshold. The model estimates a ${beneish.fraudProb}% probability of earnings manipulation. Key drivers: ${Object.entries(beneish.components).filter(([k,v]) => v > 1.3).map(([k]) => k).join(", ") || "multiple indicators elevated"}.` });
  }

  benchmarks.filter(b => b.flag === "high").forEach(b => {
    findings.push({ level: "high", icon: "⚠️", title: `${b.label} significantly above industry`, body: `Company's ${b.label} is ${b.company}${b.unit} versus an industry average of ${b.industry}${b.unit}. This deviation of ${Math.abs(b.company - b.industry).toFixed(1)}${b.unit} warrants further investigation.` });
  });
  benchmarks.filter(b => b.flag === "medium").forEach(b => {
    findings.push({ level: "medium", icon: "📌", title: `${b.label} above sector average`, body: `${b.label} of ${b.company}${b.unit} is above the industry benchmark of ${b.industry}${b.unit}. Monitor for further deterioration.` });
  });

  (financials.redFlags || []).slice(0, 3).forEach(flag => {
    findings.push({ level: "medium", icon: "📄", title: "Textual red flag in report", body: flag });
  });

  if (findings.length === 0) {
    findings.push({ level: "low", icon: "✅", title: "No major red flags detected", body: "All key ratios are within acceptable ranges and the Beneish M-Score indicates a low probability of earnings manipulation. Routine audit procedures recommended." });
  }

  const labels = { high: "HIGH RISK", medium: "MONITOR", low: "CLEAR" };
  return `<div class="findings">${findings.map(f => `
    <div class="finding ${f.level}">
      <div class="finding-icon">${f.icon}</div>
      <div class="finding-body">
        <h4>${f.title}</h4>
        <p>${f.body}</p>
        <span class="finding-badge">${labels[f.level]}</span>
      </div>
    </div>`).join("")}</div>`;
}

function renderBeneishBreakdown(components) {
  if (!components) return '<p style="color:var(--text-3);font-size:13px">Upload a second year of data to calculate M-Score components.</p>';
  const desc = {
    DSRI: ["Days Sales Receivables", "Receivables growing faster than revenue → revenue inflation risk", 1.1],
    GMI:  ["Gross Margin Index", "Deteriorating margins can push earnings manipulation", 1.1],
    AQI:  ["Asset Quality Index", "Rising intangibles or deferred costs signal risk", 1.0],
    SGI:  ["Sales Growth Index", "High growth firms face more incentive to manipulate", 1.2],
    DEPI: ["Depreciation Index", "Lower depreciation rates may inflate earnings", 1.0],
    SGAI: ["SG&A Expense Index", "Rising admin costs relative to revenue", 1.1],
    TATA: ["Total Accruals / Assets", "High accruals vs cash = earnings quality concern", 0.08],
    LVGI: ["Leverage Index", "Rising leverage increases fraud incentive", 1.0]
  };
  return `<div class="beneish-grid">${Object.entries(components).map(([k, v]) => {
    const [name, tip, thresh] = desc[k] || [k, "", 1];
    const bad = v > thresh;
    return `<div class="beneish-item">
      <div class="beneish-abbr">${k}</div>
      <div class="beneish-detail">
        <span>${name}</span>
        <small>${tip}</small>
      </div>
      <div class="beneish-val" style="color:${bad ? "var(--amber)" : "var(--green)"}">${v}</div>
    </div>`;
  }).join("")}</div>`;
}

function renderBenchmarkTable(benchmarks) {
  if (!benchmarks.length) return "";
  const flagColors = { high: "var(--red)", medium: "var(--amber)", ok: "var(--green)" };
  const flagLabels = { high: "⚠ High", medium: "~ Watch", ok: "✓ OK" };
  return `
  <table class="benchmark-table">
    <thead><tr><th>Metric</th><th>Company</th><th>Industry avg</th><th>vs Benchmark</th><th>Status</th></tr></thead>
    <tbody>${benchmarks.map(b => {
      const compVal = b.company ?? "N/A";
      const pct = b.company && b.industry ? Math.min(100, (b.company / (b.industry * 2)) * 100) : 50;
      return `<tr>
        <td>${b.label}</td>
        <td style="font-family:var(--mono)">${compVal}${compVal !== "N/A" ? b.unit : ""}</td>
        <td style="font-family:var(--mono);color:var(--text-3)">${b.industry}${b.unit}</td>
        <td><div class="vs-industry"><div class="vs-bar"><div class="vs-fill" style="width:${pct}%;background:${flagColors[b.flag]}"></div></div></div></td>
        <td style="color:${flagColors[b.flag]};font-size:12px;font-family:var(--mono)">${flagLabels[b.flag]}</td>
      </tr>`;
    }).join("")}</tbody>
  </table>`;
}

// ─── CHARTS ──────────────────────────────────────────────────────────────────
function drawCharts() {
  const reports = state.reports;
  if (!reports.length) return;

  const labels = reports.map(r => r.year);
  const colors = { accent: "#3b82f6", green: "#10b981", amber: "#f59e0b", red: "#ef4444" };
  const gridColor = "rgba(255,255,255,0.06)";
  const textColor = "#64748b";
  const baseOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: textColor, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: gridColor } },
      y: { ticks: { color: textColor, font: { family: "IBM Plex Mono", size: 11 } }, grid: { color: gridColor } }
    }
  };

  // Revenue chart
  const revCtx = document.getElementById("chartRevenue");
  if (revCtx) {
    if (state.charts.revenue) state.charts.revenue.destroy();
    state.charts.revenue = new Chart(revCtx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "Revenue", data: reports.map(r => r.financials.revenue), backgroundColor: "rgba(59,130,246,0.7)", borderRadius: 4 },
          { label: "Net Income", data: reports.map(r => r.financials.netIncome), backgroundColor: "rgba(16,185,129,0.7)", borderRadius: 4 }
        ]
      },
      options: { ...baseOpts, plugins: { ...baseOpts.plugins } }
    });
  }

  // Beneish score trend
  const bCtx = document.getElementById("chartBeneish");
  if (bCtx) {
    const bScores = reports.map(r => r.beneish?.score ?? null);
    if (state.charts.beneish) state.charts.beneish.destroy();
    state.charts.beneish = new Chart(bCtx, {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "M-Score", data: bScores, borderColor: colors.amber, backgroundColor: "rgba(245,158,11,0.1)", tension: 0.3, pointRadius: 5, pointBackgroundColor: colors.amber },
          { label: "Threshold", data: labels.map(() => -1.78), borderColor: colors.red, borderDash: [6,3], borderWidth: 1.5, pointRadius: 0 }
        ]
      },
      options: { ...baseOpts, plugins: { legend: { display: false } } }
    });
  }

  // Ratios radar / bar
  const ratCtx = document.getElementById("chartRatios");
  if (ratCtx) {
    const active = reports.find(r => r.year === state.activeYear) || reports[reports.length - 1];
    const bench = INDUSTRY_BENCHMARKS[state.industry];
    const rLabels = ["Receivables Days", "Current Ratio", "Debt/Equity", "Interest Cover", "Asset Turnover"];
    const compData = [active.ratios.receivablesDays, active.ratios.currentRatio, active.ratios.debtToEquity, active.ratios.interestCoverage, active.ratios.assetTurnover];
    const industData = [bench.receivablesDays, bench.currentRatio, bench.debtToEquity, bench.interestCoverage, bench.assetTurnover];
    if (state.charts.ratios) state.charts.ratios.destroy();
    state.charts.ratios = new Chart(ratCtx, {
      type: "bar",
      data: {
        labels: rLabels,
        datasets: [
          { label: "Company", data: compData, backgroundColor: "rgba(59,130,246,0.7)", borderRadius: 3 },
          { label: "Industry", data: industData, backgroundColor: "rgba(100,116,139,0.4)", borderRadius: 3 }
        ]
      },
      options: {
        ...baseOpts,
        indexAxis: "y",
        plugins: { legend: { display: true, labels: { color: textColor, font: { size: 11 } } } }
      }
    });
  }
}

// ─── MAIN RENDER ─────────────────────────────────────────────────────────────
function renderResults() {
  if (!state.reports.length) return;
  const active = state.reports.find(r => r.year === state.activeYear) || state.reports[state.reports.length - 1];

  document.getElementById("companyTitle").textContent = active.financials.companyName || "Company";
  document.getElementById("yearTitle").textContent = active.year;

  // year chips
  document.getElementById("yearChips").innerHTML = state.reports.map(r =>
    `<button class="year-chip ${r.year === state.activeYear ? "active" : ""}" onclick="switchYear('${r.year}')">${r.year}</button>`
  ).join("");

  // summary
  if (state.summary) {
    document.getElementById("aiSummary").innerHTML = `
      <div class="ai-summary-label">AI audit summary</div>
      <p>${state.summary}</p>`;
    document.getElementById("aiSummary").style.display = "block";
  }

  // metric cards
  document.getElementById("metricCards").innerHTML = renderMetricCards(active.beneish, active.ratios);
  // findings
  document.getElementById("findings").innerHTML = renderFindings(active.financials, active.beneish, active.benchmarks);
  // beneish breakdown
  document.getElementById("beneishBreakdown").innerHTML = renderBeneishBreakdown(active.beneish?.components);
  // benchmark table
  document.getElementById("benchmarkTable").innerHTML = renderBenchmarkTable(active.benchmarks);

  document.getElementById("uploadSection").style.display = "none";
  document.getElementById("resultsSection").style.display = "block";

  setTimeout(drawCharts, 100);
}

function switchYear(year) {
  state.activeYear = year;
  renderResults();
}

// ─── TAB LOGIC ───────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach(p => p.style.display = p.id === "panel-" + name ? "block" : "none");
  if (name === "charts") setTimeout(drawCharts, 50);
}

// ─── UPLOAD & ANALYSIS ───────────────────────────────────────────────────────
async function analyseFile(file, yearLabel) {
  const steps = ["Reading PDF", "Extracting financials", "Calculating ratios", "Running Beneish model", "Benchmarking", "Generating summary"];
  const loaderEl = document.getElementById("loader");
  loaderEl.innerHTML = `
    <div class="loader">
      <div class="spinner"></div>
      <div class="progress-steps">
        ${steps.map((s, i) => `<div class="progress-step" data-step="${i}">${s}</div>`).join("")}
      </div>
    </div>`;
  document.getElementById("uploadSection").style.display = "none";
  loaderEl.style.display = "block";

  try {
    setProgress(steps, 0);
    const text = await readPDF(file);

    setProgress(steps, 1);
    const financials = await extractFinancialsWithClaude(text, yearLabel);
    state.industry = financials.industry || state.industry;

    setProgress(steps, 2);
    const ratios = calcRatios(financials);

    setProgress(steps, 3);
    // find previous year data for Beneish
    const sorted = [...state.reports].sort((a, b) => a.year - b.year);
    const prev = sorted[sorted.length - 1]?.financials;
    if (prev) {
      prev.prevRevenue = prev.revenue;
      financials.prevRevenue = prev.revenue;
    }
    const beneish = prev ? calcBeneish(financials, prev) : null;

    setProgress(steps, 4);
    const benchmarks = benchmarkRatios(ratios, state.industry);

    // add or replace this year
    state.reports = state.reports.filter(r => r.year !== yearLabel);
    state.reports.push({ year: yearLabel, financials, beneish, ratios, benchmarks });
    state.reports.sort((a, b) => a.year.localeCompare(b.year));
    state.activeYear = yearLabel;

    // add to sidebar list
    updateReportList();

    setProgress(steps, 5);
    state.summary = await generateAuditSummary(financials, beneish, benchmarks, state.industry);

    steps.forEach((_, i) => setProgress(steps, i + 99)); // mark all done
    loaderEl.style.display = "none";
    renderResults();

  } catch (err) {
    loaderEl.innerHTML = `<div class="loader"><p style="color:var(--red)">Error: ${err.message}</p><button onclick="resetUpload()" style="margin-top:1rem">Try again</button></div>`;
  }
}

function updateReportList() {
  const list = document.getElementById("reportList");
  list.innerHTML = state.reports.map(r =>
    `<div class="report-item ${r.year === state.activeYear ? "active" : ""}" onclick="switchYear('${r.year}')">
      <span class="report-item-icon">📄</span> ${r.financials.companyName || "Report"} ${r.year}
    </div>`
  ).join("");
}

function resetUpload() {
  document.getElementById("loader").style.display = "none";
  document.getElementById("uploadSection").style.display = "block";
}

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const zone = document.getElementById("uploadZone");
  const input = document.getElementById("fileInput");
  const yearSel = document.getElementById("yearSelect");

  zone.addEventListener("click", () => input.click());
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("drag"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("drag");
    const file = e.dataTransfer.files[0];
    if (file) analyseFile(file, yearSel.value);
  });
  input.addEventListener("change", () => {
    if (input.files[0]) analyseFile(input.files[0], yearSel.value);
  });

  document.querySelectorAll(".tab").forEach(t =>
    t.addEventListener("click", () => switchTab(t.dataset.tab))
  );

  // industry selector
  document.getElementById("industrySelect").addEventListener("change", e => {
    state.industry = e.target.value;
    state.reports.forEach(r => { r.benchmarks = benchmarkRatios(r.ratios, state.industry); });
    if (state.reports.length) renderResults();
  });
});

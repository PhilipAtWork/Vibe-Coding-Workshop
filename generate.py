#!/usr/bin/env python3
"""Generate index.html from data/wvs-synthetic.csv.

Produces a self-contained HTML page with embedded data and Chart.js
visualisations. Uses only the Python standard library. Set a fixed
random seed so the output is reproducible.
"""

import csv, json, random, os

SEED = 42
random.seed(SEED)

COLORS = {
    "China": "#E69F00",
    "Singapore": "#D55E00",
    "Turkey": "#CC79A7",
    "India": "#0072B2",
    "Kazakhstan": "#009E73",
}
MARKERS = {
    "China": "circle",
    "Singapore": "triangle",
    "Turkey": "star",
    "India": "rectRot",
    "Kazakhstan": "rect",
}
COUNTRY_ORDER = ["China", "India", "Kazakhstan", "Singapore", "Turkey"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "data", "wvs-synthetic.csv")

# ── 1. Read CSV ──────────────────────────────────────────────────────
with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    all_rows = list(reader)

total_rows = len(all_rows)

# ── 2. Summary statistics (before cleaning) ─────────────────────────
DISPLAY_COLS = [c for c in fieldnames if c != "respondent_id"]

NUMERIC_COLS = {
    "age", "life_satisfaction", "freedom_of_choice",
    "emancipative_values", "importance_of_god",
    "financial_satisfaction", "secular_values",
}
INDEX_COLS = {"emancipative_values", "secular_values"}

def col_type_label(c):
    if c in INDEX_COLS:
        return "Numeric (0–1 index)"
    if c in NUMERIC_COLS:
        return "Numeric"
    if c == "income_level":
        return "Ordinal categorical"
    return "Categorical"

non_empty_counts = {}
for c in DISPLAY_COLS:
    non_empty_counts[c] = sum(1 for r in all_rows if r[c].strip() != "")

# Duplicate check on respondent_id
ids = [r["respondent_id"] for r in all_rows]
n_duplicates = total_rows - len(set(ids))

# ── 3. Clean: remove rows with any blank cell ───────────────────────
clean_rows = [r for r in all_rows if all(r[c].strip() != "" for c in fieldnames)]
n_removed = total_rows - len(clean_rows)
n_clean = len(clean_rows)

# ── 4. Compute aggregates ───────────────────────────────────────────
def mean(values):
    return sum(values) / len(values)

def country_rows(country):
    return [r for r in clean_rows if r["country"] == country]

country_stats = {}
for country in COUNTRY_ORDER:
    rows = country_rows(country)
    n = len(rows)
    sec = mean([float(r["secular_values"]) for r in rows])
    eman = mean([float(r["emancipative_values"]) for r in rows])
    life = mean([float(r["life_satisfaction"]) for r in rows]) / 10
    trust = sum(1 for r in rows if r["trust_people"] == "Trusted") / n
    god = mean([float(r["importance_of_god"]) for r in rows]) / 10
    fin = mean([float(r["financial_satisfaction"]) for r in rows]) / 10
    country_stats[country] = {
        "n": n,
        "secular": round(sec, 4),
        "emancipative": round(eman, 4),
        "life": round(life, 4),
        "trust": round(trust, 4),
        "god": round(god, 4),
        "financial": round(fin, 4),
    }

# Cultural map data
cultural_map = {c: {"x": s["secular"], "y": s["emancipative"]} for c, s in country_stats.items()}

# Radar data (order: life, trust, god, emancipative, secular, financial)
radar_data = {}
for c, s in country_stats.items():
    radar_data[c] = [s["life"], s["trust"], s["god"], s["emancipative"], s["secular"], s["financial"]]

# China vs India scatter sample
random.seed(SEED)
china_rows = country_rows("China")
india_rows = country_rows("India")
china_sample = random.sample(china_rows, min(300, len(china_rows)))
india_sample = random.sample(india_rows, min(300, len(india_rows)))

china_pts = [{"x": round(float(r["secular_values"]), 4), "y": round(float(r["emancipative_values"]), 4)} for r in china_sample]
india_pts = [{"x": round(float(r["secular_values"]), 4), "y": round(float(r["emancipative_values"]), 4)} for r in india_sample]
china_avg = cultural_map["China"]
india_avg = cultural_map["India"]

# Singapore heatmap
sg_rows = country_rows("Singapore")
heatmap = [[0] * 10 for _ in range(10)]
for r in sg_rows:
    ls = int(float(r["life_satisfaction"]))
    fs = int(float(r["financial_satisfaction"]))
    heatmap[ls - 1][fs - 1] += 1
heatmap_max = max(max(row) for row in heatmap)

# ── 5. Compute takeaway text ────────────────────────────────────────
highest_sec = max(COUNTRY_ORDER, key=lambda c: country_stats[c]["secular"])
lowest_sec = min(COUNTRY_ORDER, key=lambda c: country_stats[c]["secular"])
highest_eman = max(COUNTRY_ORDER, key=lambda c: country_stats[c]["emancipative"])

takeaway_cultural = (
    f"{highest_sec} scores highest on secular values and {highest_eman} leads on emancipative values, "
    f"while {lowest_sec} shows the lowest secular-values score. "
    f"The five countries span a wide range on the Inglehart–Welzel cultural map."
)

radar_labels_short = ["life satisfaction", "interpersonal trust", "importance of god",
                      "emancipative values", "secular values", "financial satisfaction"]
ranges = []
for i in range(6):
    vals = [radar_data[c][i] for c in COUNTRY_ORDER]
    ranges.append((max(vals) - min(vals), radar_labels_short[i]))
ranges.sort(reverse=True)
takeaway_radar = (
    f"Countries differ most sharply on {ranges[0][1]} and {ranges[1][1]}, "
    f"while {ranges[-1][1]} shows the smallest gap across the five countries."
)

takeaway_scatter = (
    "Despite clearly different averages, individual responses from China and India "
    "overlap substantially — many respondents from both countries share similar value profiles."
)

max_cell = 0
max_ls, max_fs = 0, 0
for ls in range(10):
    for fs in range(10):
        if heatmap[ls][fs] > max_cell:
            max_cell = heatmap[ls][fs]
            max_ls, max_fs = ls + 1, fs + 1
takeaway_heatmap = (
    f"The densest cluster sits at life satisfaction = {max_ls} and financial satisfaction = {max_fs} "
    f"({max_cell} respondents). Higher financial satisfaction generally coincides with higher life satisfaction."
)

# ── 6. Build summary table HTML ─────────────────────────────────────
summary_rows_html = ""
for c in DISPLAY_COLS:
    summary_rows_html += f"<tr><td><code>{c}</code></td><td>{col_type_label(c)}</td><td>{non_empty_counts[c]:,}</td></tr>\n"

# ── 7. Build heatmap HTML ───────────────────────────────────────────
heatmap_html = '<div class="heatmap-wrap">\n'
heatmap_html += '<table class="heatmap-table"><tbody>\n'
# header row
heatmap_html += '<tr><td class="hm-corner"></td>'
for fs in range(1, 11):
    heatmap_html += f'<td class="hm-col-hdr">{fs}</td>'
heatmap_html += '</tr>\n'
# data rows (life_satisfaction 10 at top, 1 at bottom)
for ls in range(10, 0, -1):
    heatmap_html += f'<tr><td class="hm-row-hdr">{ls}</td>'
    for fs in range(1, 11):
        count = heatmap[ls - 1][fs - 1]
        if count == 0:
            heatmap_html += '<td class="hm-cell hm-empty"></td>'
        else:
            intensity = count / heatmap_max
            lightness = 95 - intensity * 55
            color = f"hsl(24, 100%, {lightness:.0f}%)"
            text_color = "#fff" if lightness < 50 else "#333"
            heatmap_html += (
                f'<td class="hm-cell" style="background:{color};color:{text_color}">{count}</td>'
            )
    heatmap_html += '</tr>\n'
heatmap_html += '</tbody></table>\n'
heatmap_html += '<div class="hm-axis-labels"><span class="hm-x-label">Financial Satisfaction &rarr;</span></div>\n'
heatmap_html += '<div class="hm-y-label-wrap"><span class="hm-y-label">Life Satisfaction &rarr;</span></div>\n'
heatmap_html += '</div>\n'

# ── 8. Assemble HTML ────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Values Survey – Synthetic Data Explorer</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:#222;background:#fafafa;margin:0;padding:0;line-height:1.6}}
.container{{max-width:900px;margin:0 auto;padding:1rem 1.25rem 3rem}}
h1{{font-size:1.75rem;margin:1.5rem 0 0.25rem}}
h2{{font-size:1.25rem;margin:2.5rem 0 0.5rem;border-bottom:2px solid #ddd;padding-bottom:0.3rem}}
p{{margin:0.5rem 0}}
a{{color:#0072B2}}
.intro{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:1rem 1.25rem;margin:1rem 0}}
.summary-table{{width:100%;border-collapse:collapse;margin:1rem 0;font-size:0.9rem}}
.summary-table th,.summary-table td{{padding:0.4rem 0.75rem;border:1px solid #ddd;text-align:left}}
.summary-table th{{background:#f5f5f5;font-weight:600}}
.summary-table code{{background:#eef;padding:0.1rem 0.3rem;border-radius:3px;font-size:0.85em}}
.note{{font-size:0.9rem;color:#555;margin:0.5rem 0}}
.chart-wrap{{position:relative;width:100%;max-width:720px;margin:1.5rem auto}}
canvas{{width:100%!important}}
.takeaway{{background:#f0f7ff;border-left:3px solid #0072B2;padding:0.6rem 1rem;margin:1rem 0;font-size:0.95rem;border-radius:0 6px 6px 0}}
/* Heatmap */
.heatmap-wrap{{position:relative;max-width:520px;margin:1.5rem auto;padding-left:2rem;padding-bottom:2rem}}
.hm-y-label-wrap{{position:absolute;left:-0.5rem;top:50%;transform:rotate(-90deg) translateX(-50%);transform-origin:0 0;white-space:nowrap;font-size:0.8rem;color:#555}}
.hm-axis-labels{{text-align:center;margin-top:0.25rem}}
.hm-x-label{{font-size:0.8rem;color:#555}}
.heatmap-table{{width:100%;border-collapse:collapse;table-layout:fixed}}
.hm-cell{{text-align:center;font-size:clamp(0.55rem,2vw,0.8rem);padding:0;aspect-ratio:1;vertical-align:middle;border:1px solid #eee}}
.hm-empty{{background:#f9f9f9}}
.hm-row-hdr,.hm-col-hdr{{font-size:0.75rem;color:#555;text-align:center;padding:0.2rem;font-weight:600;border:none}}
.hm-corner{{border:none}}
.legend-inline{{display:flex;flex-wrap:wrap;gap:0.75rem;margin:0.5rem 0;font-size:0.85rem}}
.legend-inline span{{display:inline-flex;align-items:center;gap:0.3rem}}
.legend-dot{{width:12px;height:12px;border-radius:50%;display:inline-block}}
@media(max-width:600px){{
  h1{{font-size:1.3rem}}
  .container{{padding:0.75rem 1rem 2rem}}
  .heatmap-wrap{{max-width:100%;padding-left:1.5rem}}
}}
</style>
</head>
<body>
<div class="container">

<h1>World Values Survey &ndash; Synthetic Data Explorer</h1>

<div class="intro">
<p>This page presents an exploratory analysis of a <strong>synthetic (simulated) dataset</strong>
modelled on the <a href="https://www.worldvaluessurvey.org/" target="_blank" rel="noopener">World Values Survey, Wave&nbsp;7</a>
(Haerpfer, C., Inglehart, R., Moreno, A., Welzel, C., Kizilova, K., Diez-Medrano, J., Lagos, M., Norris, P., Ponarin, E., &amp; Puranen, B. (eds.), 2022.
<em>World Values Survey: Round Seven &ndash; Country-Pooled Datafile</em>. Madrid &amp; Vienna: JD Systems Institute &amp; WVSA Secretariat).</p>
<p>The rows are entirely <strong>fabricated</strong> to resemble real WVS distributions and relationships &mdash;
<strong>no actual respondent data is used</strong>. Any patterns shown are illustrative only.</p>
<p><strong>Countries included:</strong> China, India, Kazakhstan, Singapore, and Turkey
({n_clean:,} respondents after cleaning; {total_rows:,} original rows).</p>
</div>

<h2>Data Summary</h2>
<table class="summary-table">
<thead><tr><th>Column</th><th>Data Type</th><th>Non-Empty Rows (of {total_rows:,})</th></tr></thead>
<tbody>
{summary_rows_html}
</tbody>
</table>
<p class="note">{"No duplicate respondent IDs found" if n_duplicates == 0 else f"{n_duplicates:,} duplicate respondent IDs found"}
({total_rows:,} unique identifiers). <code>respondent_id</code> is excluded from all charts.</p>
<p class="note">{n_removed:,} rows contained at least one missing value and were removed,
leaving <strong>{n_clean:,} rows</strong> for the analyses below.</p>

<h2>1. Cultural Map &mdash; Emancipative vs Secular Values</h2>
<p style="font-size:0.9rem;color:#555">Each point is a country average (Inglehart&ndash;Welzel style).</p>
<div class="chart-wrap"><canvas id="culturalMap"></canvas></div>
<div class="takeaway">{takeaway_cultural}</div>

<h2>2. Value Fingerprints &mdash; Radar Chart</h2>
<p style="font-size:0.9rem;color:#555">Six measures normalised to 0&ndash;1. One line per country.</p>
<div class="chart-wrap"><canvas id="radarChart"></canvas></div>
<div class="takeaway">{takeaway_radar}</div>

<h2>3. Individual Values &mdash; China vs India</h2>
<p style="font-size:0.9rem;color:#555">~300 randomly sampled respondents per country; larger outlined points mark the country average.</p>
<div class="chart-wrap"><canvas id="chinaIndia"></canvas></div>
<div class="takeaway">{takeaway_scatter}</div>

<h2>4. Life vs Financial Satisfaction &mdash; Singapore</h2>
<p style="font-size:0.9rem;color:#555">Each cell shows the number of Singaporean respondents at that combination.
Darker&nbsp;=&nbsp;more respondents.</p>
{heatmap_html}
<div class="takeaway">{takeaway_heatmap}</div>

</div><!-- .container -->

<script>
// ── Embedded data ──
const COLORS = {json.dumps(COLORS)};
const MARKERS = {json.dumps(MARKERS)};
const culturalMap = {json.dumps(cultural_map)};
const radarLabels = ["Life Satisfaction","Trust (share)","Importance of God","Emancipative Values","Secular Values","Financial Satisfaction"];
const radarData = {json.dumps(radar_data)};
const chinaPts = {json.dumps(china_pts)};
const indiaPts = {json.dumps(india_pts)};
const chinaAvg = {json.dumps(china_avg)};
const indiaAvg = {json.dumps(india_avg)};
const countryOrder = {json.dumps(COUNTRY_ORDER)};

// ── Helpers ──
const fmt = (v) => Number(v).toFixed(2);

// ── 1. Cultural Map ──
new Chart(document.getElementById('culturalMap'), {{
  type: 'scatter',
  data: {{
    datasets: countryOrder.map(c => ({{
      label: c,
      data: [culturalMap[c]],
      backgroundColor: COLORS[c],
      borderColor: COLORS[c],
      pointStyle: MARKERS[c],
      pointRadius: 10,
      borderWidth: 2
    }}))
  }},
  options: {{
    responsive: true,
    aspectRatio: 1.3,
    scales: {{
      x: {{ title: {{ display: true, text: 'Secular Values' }}, min: 0, max: 0.8, ticks: {{ callback: v => v.toFixed(1) }} }},
      y: {{ title: {{ display: true, text: 'Emancipative Values' }}, min: 0, max: 0.8, ticks: {{ callback: v => v.toFixed(1) }} }}
    }},
    plugins: {{
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': (' + fmt(ctx.parsed.x) + ', ' + fmt(ctx.parsed.y) + ')' }} }},
      legend: {{ labels: {{ usePointStyle: true, pointStyle: (ctx) => MARKERS[countryOrder[ctx.datasetIndex]] }} }}
    }}
  }},
  plugins: [{{
    afterDraw(chart) {{
      const ctx2 = chart.ctx;
      chart.data.datasets.forEach((ds, i) => {{
        const meta = chart.getDatasetMeta(i);
        if (!meta.data[0]) return;
        const pt = meta.data[0];
        ctx2.save();
        ctx2.fillStyle = '#333';
        ctx2.font = 'bold 12px sans-serif';
        ctx2.fillText(ds.label, pt.x + 14, pt.y - 10);
        ctx2.restore();
      }});
    }}
  }}]
}});

// ── 2. Radar ──
new Chart(document.getElementById('radarChart'), {{
  type: 'radar',
  data: {{
    labels: radarLabels,
    datasets: countryOrder.map(c => ({{
      label: c,
      data: radarData[c],
      borderColor: COLORS[c],
      backgroundColor: COLORS[c] + '22',
      pointStyle: MARKERS[c],
      pointRadius: 5,
      pointBackgroundColor: COLORS[c],
      borderWidth: 2,
      fill: true
    }}))
  }},
  options: {{
    responsive: true,
    scales: {{
      r: {{ min: 0, max: 1, ticks: {{ stepSize: 0.2, callback: v => v.toFixed(1) }} }}
    }},
    plugins: {{
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': ' + fmt(ctx.parsed.r) }} }},
      legend: {{ labels: {{ usePointStyle: true }} }}
    }}
  }}
}});

// ── 3. China vs India ──
new Chart(document.getElementById('chinaIndia'), {{
  type: 'scatter',
  data: {{
    datasets: [
      {{
        label: 'China (individuals)',
        data: chinaPts,
        backgroundColor: COLORS['China'] + '66',
        borderColor: COLORS['China'] + '66',
        pointStyle: 'circle',
        pointRadius: 3.5,
        borderWidth: 0
      }},
      {{
        label: 'India (individuals)',
        data: indiaPts,
        backgroundColor: COLORS['India'] + '66',
        borderColor: COLORS['India'] + '66',
        pointStyle: 'rectRot',
        pointRadius: 3.5,
        borderWidth: 0
      }},
      {{
        label: 'China (average)',
        data: [chinaAvg],
        backgroundColor: 'rgba(0,0,0,0)',
        borderColor: COLORS['China'],
        pointStyle: 'circle',
        pointRadius: 12,
        borderWidth: 3
      }},
      {{
        label: 'India (average)',
        data: [indiaAvg],
        backgroundColor: 'rgba(0,0,0,0)',
        borderColor: COLORS['India'],
        pointStyle: 'rectRot',
        pointRadius: 12,
        borderWidth: 3
      }}
    ]
  }},
  options: {{
    responsive: true,
    aspectRatio: 1.3,
    scales: {{
      x: {{ title: {{ display: true, text: 'Secular Values' }}, min: 0, max: 1, ticks: {{ callback: v => v.toFixed(1) }} }},
      y: {{ title: {{ display: true, text: 'Emancipative Values' }}, min: 0, max: 1, ticks: {{ callback: v => v.toFixed(1) }} }}
    }},
    plugins: {{
      tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': (' + fmt(ctx.parsed.x) + ', ' + fmt(ctx.parsed.y) + ')' }} }},
      legend: {{ labels: {{ usePointStyle: true }} }}
    }}
  }}
}});
</script>
</body>
</html>
"""

# ── 9. Write output ─────────────────────────────────────────────────
out_path = os.path.join(SCRIPT_DIR, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Wrote {out_path}")
print(f"  {total_rows:,} rows read, {n_removed:,} removed, {n_clean:,} analysed")

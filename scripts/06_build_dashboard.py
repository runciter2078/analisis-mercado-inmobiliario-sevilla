"""
06_build_dashboard.py
Genera el dashboard HTML estático del análisis inmobiliario de Sevilla.
Lee los CSVs de resultados (clustering y forecast) e inyecta los datos
como JSON en el template HTML. El HTML resultante es autocontenido.

Ejecutar desde la raíz del proyecto:
    python scripts/06_build_dashboard.py
"""

import json
import math
from pathlib import Path

import pandas as pd

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parent.parent
CLUSTERS   = ROOT / "resultados" / "distritos_clusters.csv"
FORECAST   = ROOT / "resultados" / "forecast_valores.csv"
HISTORICAL = ROOT / "data" / "processed" / "mivau_sevilla_series.csv"
OUT_HTML   = ROOT / "resultados" / "dashboard_insur.html"


def load_data():
    df_cl = pd.read_csv(CLUSTERS)
    df_fc = pd.read_csv(FORECAST)
    df_hi = pd.read_csv(HISTORICAL)
    return df_cl, df_fc, df_hi


def prepare_clusters(df):
    """Selecciona y serializa las columnas necesarias para el dashboard."""
    cols = ["district_name", "last_price", "avg_yoy_pct", "yoy_accel",
            "avg_cagr_5y", "cluster_id", "cluster_label"]
    return df[cols].sort_values("last_price", ascending=False).to_dict(orient="records")


def prepare_forecast(df):
    cols = ["period", "date", "sarima_forecast", "sarima_lo80", "sarima_hi80",
            "prophet_forecast", "prophet_lo80", "prophet_hi80"]
    return df[cols].to_dict(orient="records")


def prepare_historical(df):
    """Últimos 20 trimestres para contexto visual del forecast."""
    df["date"] = pd.PeriodIndex(df["period"], freq="Q").to_timestamp().strftime("%Y-%m-%d")
    tail = df.tail(20)[["date", "price_nueva_eur_m2"]].dropna()
    return tail.rename(columns={"price_nueva_eur_m2": "price"}).to_dict(orient="records")


def compute_kpis(df_cl, df_fc, df_hi):
    last_price   = round(df_hi["price_nueva_eur_m2"].iloc[-1], 1)
    prev_price   = df_hi["price_nueva_eur_m2"].iloc[-5]   # mismo trimestre año anterior
    yoy          = round((last_price / prev_price - 1) * 100, 1)
    price_min    = int(df_cl["last_price"].min())
    price_max    = int(df_cl["last_price"].max())
    fc_q1        = round(df_fc["sarima_forecast"].iloc[0], 0)
    fc_q1_lo     = round(df_fc["sarima_lo80"].iloc[0], 0)
    fc_q1_hi     = round(df_fc["sarima_hi80"].iloc[0], 0)
    n_clusters   = df_cl["cluster_label"].nunique()
    silhouette   = 0.257
    return {
        "last_price":  last_price,
        "yoy":         yoy,
        "price_min":   price_min,
        "price_max":   price_max,
        "fc_q1":       int(fc_q1),
        "fc_q1_lo":    int(fc_q1_lo),
        "fc_q1_hi":    int(fc_q1_hi),
        "n_clusters":  n_clusters,
        "silhouette":  silhouette,
    }


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Mercado Inmobiliario Sevilla — Análisis 2025</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --ink:     #1a1f2e;
    --ink-mid: #3d4560;
    --ink-low: #7a829e;
    --bg:      #f7f6f2;
    --white:   #ffffff;
    --rule:    #e2e0d9;
    --c0: #e07b54;
    --c1: #5b8db8;
    --c2: #5aaa7e;
    --c3: #c9843a;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--ink); font-family: 'DM Sans', sans-serif; font-size: 15px; line-height: 1.6; }}

  header {{ background: var(--ink); color: #fff; padding: 48px 60px 40px; border-bottom: 3px solid var(--c0); }}
  header .eyebrow {{ font-family: 'DM Mono', monospace; font-size: 11px; letter-spacing: .15em; text-transform: uppercase; color: var(--c0); margin-bottom: 14px; }}
  header h1 {{ font-family: 'DM Serif Display', serif; font-size: 36px; font-weight: 400; letter-spacing: -.5px; line-height: 1.15; margin-bottom: 10px; }}
  header .subtitle {{ color: #9aa3bb; font-size: 14px; font-weight: 300; }}
  header .meta {{ margin-top: 28px; display: flex; gap: 32px; flex-wrap: wrap; }}
  header .meta-item {{ font-family: 'DM Mono', monospace; font-size: 11px; color: #9aa3bb; letter-spacing: .05em; }}
  header .meta-item span {{ color: #fff; }}

  main {{ max-width: 1200px; margin: 0 auto; padding: 48px 60px 80px; }}
  section {{ margin-bottom: 64px; }}
  .section-label {{ font-family: 'DM Mono', monospace; font-size: 11px; letter-spacing: .12em; text-transform: uppercase; color: var(--ink-low); margin-bottom: 6px; }}
  .section-title {{ font-family: 'DM Serif Display', serif; font-size: 24px; font-weight: 400; color: var(--ink); margin-bottom: 24px; padding-bottom: 14px; border-bottom: 1px solid var(--rule); }}

  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{ background: var(--white); border: 1px solid var(--rule); border-radius: 4px; padding: 22px 20px 18px; }}
  .kpi-label {{ font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-low); margin-bottom: 8px; }}
  .kpi-value {{ font-family: 'DM Serif Display', serif; font-size: 28px; color: var(--ink); line-height: 1; margin-bottom: 4px; }}
  .kpi-sub {{ font-size: 12px; color: var(--ink-low); }}
  .kpi-delta {{ display: inline-block; margin-top: 8px; font-family: 'DM Mono', monospace; font-size: 11px; font-weight: 500; padding: 2px 7px; border-radius: 2px; }}
  .kpi-delta.up   {{ background: #eaf6ee; color: #2d7a4f; }}
  .kpi-delta.neu  {{ background: #f0f0ee; color: var(--ink-mid); }}

  .insight-bar {{ background: var(--white); border: 1px solid var(--rule); border-left: 3px solid var(--c0); border-radius: 4px; padding: 16px 20px; font-size: 14px; color: var(--ink-mid); line-height: 1.7; }}
  .insight-bar strong {{ color: var(--ink); }}

  .chart-card {{ background: var(--white); border: 1px solid var(--rule); border-radius: 4px; padding: 24px; }}
  .chart-note {{ margin-top: 12px; font-family: 'DM Mono', monospace; font-size: 11px; color: var(--ink-low); line-height: 1.6; }}

  .cluster-legend {{ display: flex; gap: 20px; flex-wrap: wrap; margin-bottom: 16px; }}
  .cluster-pill {{ display: flex; align-items: center; gap: 7px; font-size: 13px; color: var(--ink-mid); }}
  .cluster-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

  .table-wrap {{ background: var(--white); border: 1px solid var(--rule); border-radius: 4px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ background: var(--ink); color: #fff; }}
  thead th {{ font-family: 'DM Mono', monospace; font-size: 10px; font-weight: 500; letter-spacing: .1em; text-transform: uppercase; padding: 13px 16px; text-align: left; }}
  thead th.num {{ text-align: right; }}
  tbody tr {{ border-bottom: 1px solid var(--rule); transition: background .12s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #faf9f6; }}
  tbody td {{ padding: 12px 16px; font-size: 13.5px; color: var(--ink); }}
  tbody td.num {{ text-align: right; font-family: 'DM Mono', monospace; font-size: 13px; color: var(--ink-mid); }}
  .cluster-badge {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500; }}
  .badge-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}

  .sources {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--rule); font-family: 'DM Mono', monospace; font-size: 10.5px; color: var(--ink-low); line-height: 1.9; letter-spacing: .02em; }}
  .sources strong {{ color: var(--ink-mid); }}

  @media (max-width: 900px) {{
    header, main {{ padding-left: 24px; padding-right: 24px; }}
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<header>
  <div class="eyebrow">Grupo Insur · Análisis de mercado</div>
  <h1>Mercado Inmobiliario de Sevilla<br><em>Segmentación de distritos y previsión de precios</em></h1>
  <div class="subtitle">Análisis basado en datos MIVAU (serie 2005–2025) e informes TINSA IMIE Mercados Locales (2025)</div>
  <div class="meta">
    <div class="meta-item">Fuente precio ciudad: <span>MIVAU · Valor tasado vivienda nueva</span></div>
    <div class="meta-item">Fuente distritos: <span>TINSA IMIE · Mercados Locales</span></div>
    <div class="meta-item">Último dato real: <span>4T 2025</span></div>
    <div class="meta-item">Modelo forecasting: <span>SARIMA(1,1,1)×(1,1,1,4)</span></div>
  </div>
</header>

<main>

<section>
  <div class="section-label">01</div>
  <div class="section-title">Resumen ejecutivo</div>
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-label">Precio actual · ciudad</div>
      <div class="kpi-value">__LAST_PRICE__</div>
      <div class="kpi-sub">€/m² · vivienda nueva · 4T 2025 (MIVAU)</div>
      <div class="kpi-delta up">+__YOY__% interanual</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Rango de precios · distritos</div>
      <div class="kpi-value">__PRICE_MIN__–__PRICE_MAX__</div>
      <div class="kpi-sub">€/m² · diferencia __PRICE_RATIO__× entre extremos</div>
      <div class="kpi-delta neu">11 distritos analizados</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Forecast SARIMA · rango 2026–2027</div>
      <div class="kpi-value">2.724–2.891</div>
      <div class="kpi-sub">€/m² · escenario central</div>
      <div class="kpi-delta neu">Horizonte: 6 trimestres</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Perfiles identificados</div>
      <div class="kpi-value">__N_CLUSTERS__</div>
      <div class="kpi-sub">clusters · K-Means con validación silhouette</div>
      <div class="kpi-delta neu">k=4 · silhouette __SILHOUETTE__</div>
    </div>
  </div>
  <div class="insight-bar">
    <strong>Conclusión principal:</strong> Sevilla muestra un mercado dual en 2025. Los distritos
    <strong>Premium consolidado</strong> (Casco Antiguo, Nervión) lideran en precio absoluto (&gt;3.100 €/m²)
    con crecimiento sólido. <strong>San Pablo-Santa Justa</strong> destaca como el distrito de mayor
    aceleración del conjunto (+14 pp interanual), señal de revalorización emergente. Los modelos
    SARIMA y Prophet convergen en proyectar una normalización gradual hacia <strong>2.720–2.890 €/m²
    en 2026–2027</strong>, frente al fuerte ciclo alcista de 2025.
    El modelo SARIMA proyecta una normalización gradual del mercado hacia ese rango; Prophet se incluye únicamente como referencia comparativa.
  </div>
</section>

<section>
  <div class="section-label">02</div>
  <div class="section-title">Segmentación de distritos · K-Means clustering</div>
  <div class="cluster-legend">
    <div class="cluster-pill"><div class="cluster-dot" style="background:var(--c0)"></div>Premium consolidado</div>
    <div class="cluster-pill"><div class="cluster-dot" style="background:var(--c1)"></div>Mercado estabilizado</div>
    <div class="cluster-pill"><div class="cluster-dot" style="background:var(--c2)"></div>Dinamismo sostenido</div>
    <div class="cluster-pill"><div class="cluster-dot" style="background:var(--c3)"></div>Alta tracción emergente</div>
  </div>
  <div class="chart-card">
    <div id="chart-clusters" style="height:500px"></div>
    <div class="chart-note">
      Visualización interpretativa del clustering. El modelo K-Means se entrenó con 5 variables: precio 4T 2025, variación interanual media 2025,
      aceleración interanual, CAGR 5 años y volatilidad del precio. Para facilitar la lectura, el gráfico muestra solo precio × variación interanual media;
      el tamaño de la burbuja es proporcional al CAGR 5 años. Líneas de referencia: mediana de precio y mediana de variación interanual.
      Fuente: TINSA IMIE Mercados Locales, informes 1T–4T 2025.
      San Pablo-Santa Justa forma un cluster unitario estable: 0% de co-ocurrencia con cualquier otro distrito en 20 ejecuciones de K-Means con random_state distintos.
    </div>
  </div>
</section>

<section>
  <div class="section-label">03</div>
  <div class="section-title">Previsión de precio · Sevilla ciudad · 2026–2027</div>
  <div class="chart-card">
    <div id="chart-forecast" style="height:460px"></div>
    <div class="chart-note">
      Serie histórica: MIVAU, valor tasado vivienda libre nueva, municipios &gt;25.000 hab., últimos 20 trimestres mostrados.
      Modelo principal: SARIMA(1,1,1)×(1,1,1,4) · MAPE en test (2024Q1–2025Q4): 3,04% · supera baselines naive (4,44%) y seasonal (4,97%).
      Prophet: referencia comparativa, configuración estándar sin tuning (MAPE test: 19,54%).
      Banda: IC 80%. La oscilación intraanual Q4→Q1 es compatible con el componente estacional trimestral estimado por el modelo.
    </div>
  </div>
</section>

<section>
  <div class="section-label">04</div>
  <div class="section-title">Distritos de Sevilla · métricas detalladas</div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Distrito</th>
          <th>Perfil</th>
          <th class="num">Precio 4T25 (€/m²)</th>
          <th class="num">Var. interanual media</th>
          <th class="num">Aceleración (pp)</th>
          <th class="num">CAGR 5 años</th>
        </tr>
      </thead>
      <tbody id="table-body"></tbody>
    </table>
  </div>
</section>

<div class="sources">
  <strong>Fuentes:</strong><br>
  [1] Ministerio de Vivienda y Agenda Urbana (MIVAU). <em>Valor tasado de la vivienda libre. Municipios &gt;25.000 habitantes.</em> Serie trimestral 2005Q1–2025Q4. Archivo 35103500.XLS.<br>
  [2] TINSA. <em>IMIE Mercados Locales — Sevilla.</em> Informes trimestrales 1T–4T 2025. Tabla de distritos, p. 24.<br>
  <strong>Nota metodológica:</strong> El forecast se construye con la serie MIVAU (vivienda nueva, valor tasado).
  Los precios de distritos proceden de TINSA. Ambas fuentes no se mezclan para modelar; la comparación es únicamente narrativa.
  La capa GenAI del proyecto se utilizó para extraer y estructurar el contenido narrativo de los informes TINSA mediante Claude API;
  el resultado consolidado está disponible en <em>resultados/resumen_ia_informes.md</em>.
  Generado por <em>scripts/06_build_dashboard.py</em>. Detalles en <em>decisiones_y_limitaciones.md</em>.
</div>

</main>

<script>
const CLUSTER_COLORS = {{
  "Premium consolidado":     "#e07b54",
  "Mercado estabilizado":    "#5b8db8",
  "Dinamismo sostenido":     "#5aaa7e",
  "Alta tracción emergente": "#c9843a",
}};

const distritos  = __DISTRITOS_JSON__;
const forecast   = __FORECAST_JSON__;
const historical = __HIST_JSON__;
const kpis       = __KPIS_JSON__;

// ── CLUSTERS ──────────────────────────────────────────
(function() {{
  const byCluster = {{}};
  distritos.forEach(d => {{
    if (!byCluster[d.cluster_label]) byCluster[d.cluster_label] = [];
    byCluster[d.cluster_label].push(d);
  }});
  const order = ["Premium consolidado","Mercado estabilizado","Dinamismo sostenido","Alta tracción emergente"];
  const traces = order.map(cl => {{
    const pts = byCluster[cl] || [];
    return {{
      type:"scatter", mode:"markers+text", name:cl,
      x: pts.map(d => d.avg_yoy_pct),
      y: pts.map(d => d.last_price),
      text: pts.map(d => d.district_name),
      textposition: "top center",
      textfont: {{ family:"DM Sans", size:12, color:"#1a1f2e" }},
      marker: {{
        color: CLUSTER_COLORS[cl],
        size:  pts.map(d => d.avg_cagr_5y * 5.5),
        opacity: 0.88,
        line: {{ color:"#fff", width:1.5 }},
      }},
      hovertemplate: "<b>%{{text}}</b><br>Precio: %{{y:,.0f}} €/m²<br>YoY medio: %{{x:.1f}}%<extra></extra>",
    }};
  }});

  const prices = distritos.map(d => d.last_price);
  const yoys   = distritos.map(d => d.avg_yoy_pct);
  const medP   = prices.slice().sort((a,b)=>a-b)[Math.floor(prices.length/2)];
  const medY   = yoys.slice().sort((a,b)=>a-b)[Math.floor(yoys.length/2)];

  Plotly.newPlot("chart-clusters", traces, {{
    xaxis: {{ title:{{text:"Variación interanual media 2025 (%)",font:{{family:"DM Sans",size:12,color:"#7a829e"}}}},
              tickfont:{{family:"DM Mono",size:11,color:"#7a829e"}}, gridcolor:"#ede8e0", zeroline:false }},
    yaxis: {{ title:{{text:"Precio 4T 2025 (€/m²)",font:{{family:"DM Sans",size:12,color:"#7a829e"}}}},
              tickfont:{{family:"DM Mono",size:11,color:"#7a829e"}}, gridcolor:"#ede8e0", zeroline:false }},
    shapes: [
      {{ type:"line", x0:Math.min(...yoys)-0.5, x1:Math.max(...yoys)+0.5, y0:medP, y1:medP,
         line:{{ color:"#bbb", width:1, dash:"dot" }} }},
      {{ type:"line", x0:medY, x1:medY, y0:Math.min(...prices)-100, y1:Math.max(...prices)+200,
         line:{{ color:"#bbb", width:1, dash:"dot" }} }},
    ],
    annotations: [
      {{ x:Math.max(...yoys), y:medP, text:"mediana precio", showarrow:false,
         font:{{family:"DM Mono",size:10,color:"#aaa"}}, xanchor:"right", yanchor:"bottom" }},
      {{ x:medY, y:Math.max(...prices)+150, text:"mediana YoY", showarrow:false,
         font:{{family:"DM Mono",size:10,color:"#aaa"}}, xanchor:"left" }},
    ],
    legend: {{ font:{{family:"DM Sans",size:12}}, bgcolor:"rgba(255,255,255,0.9)",
               bordercolor:"#e2e0d9", borderwidth:1 }},
    paper_bgcolor:"#ffffff", plot_bgcolor:"#ffffff",
    margin:{{ t:20, r:20, b:60, l:70 }},
    hovermode:"closest",
  }}, {{ responsive:true, displayModeBar:false }});
}})();

// ── FORECAST ──────────────────────────────────────────
(function() {{
  const histDates  = historical.map(d => d.date);
  const histPrices = historical.map(d => d.price);
  const fcDates    = forecast.map(d => d.date);
  const anchor     = historical[historical.length - 1];

  const traces = [
    {{
      type:"scatter", mode:"lines+markers", name:"Histórico (MIVAU)",
      x:histDates, y:histPrices,
      line:{{color:"#1a1f2e",width:2}}, marker:{{size:5,color:"#1a1f2e"}},
      hovertemplate:"<b>%{{x}}</b><br>%{{y:,.0f}} €/m²<extra>Histórico</extra>",
    }},
    {{
      type:"scatter", mode:"lines", name:"SARIMA IC 80%",
      x:[...fcDates,...fcDates.slice().reverse()],
      y:[...forecast.map(d=>d.sarima_hi80),...forecast.map(d=>d.sarima_lo80).reverse()],
      fill:"toself", fillcolor:"rgba(192,57,43,0.10)", line:{{color:"transparent"}},
      hoverinfo:"skip",
    }},
    {{
      type:"scatter", mode:"lines", name:"Prophet IC 80%",
      x:[...fcDates,...fcDates.slice().reverse()],
      y:[...forecast.map(d=>d.prophet_hi80),...forecast.map(d=>d.prophet_lo80).reverse()],
      fill:"toself", fillcolor:"rgba(41,128,185,0.08)", line:{{color:"transparent"}},
      hoverinfo:"skip",
    }},
    {{
      type:"scatter", mode:"lines",
      x:[anchor.date, fcDates[0]], y:[anchor.price, forecast[0].sarima_forecast],
      line:{{color:"#c0392b",width:1.5,dash:"dot"}}, showlegend:false, hoverinfo:"skip",
    }},
    {{
      type:"scatter", mode:"lines",
      x:[anchor.date, fcDates[0]], y:[anchor.price, forecast[0].prophet_forecast],
      line:{{color:"#2980b9",width:1.5,dash:"dot"}}, showlegend:false, hoverinfo:"skip",
    }},
    {{
      type:"scatter", mode:"lines+markers", name:"SARIMA (modelo principal)",
      x:fcDates, y:forecast.map(d=>d.sarima_forecast),
      line:{{color:"#c0392b",width:2.5,dash:"dash"}}, marker:{{size:7,color:"#c0392b"}},
      hovertemplate:"<b>%{{x}}</b><br>%{{y:,.0f}} €/m²<extra>SARIMA</extra>",
    }},
    {{
      type:"scatter", mode:"lines+markers", name:"Prophet (referencia comparativa)",
      x:fcDates, y:forecast.map(d=>d.prophet_forecast),
      line:{{color:"#2980b9",width:2,dash:"dot"}}, marker:{{size:7,color:"#2980b9"}},
      hovertemplate:"<b>%{{x}}</b><br>%{{y:,.0f}} €/m²<extra>Prophet</extra>",
    }},
  ];

  Plotly.newPlot("chart-forecast", traces, {{
    xaxis: {{ tickfont:{{family:"DM Mono",size:11,color:"#7a829e"}},
              gridcolor:"#ede8e0", zeroline:false }},
    yaxis: {{ title:{{text:"€/m²",font:{{family:"DM Sans",size:12,color:"#7a829e"}}}},
              tickfont:{{family:"DM Mono",size:11,color:"#7a829e"}},
              gridcolor:"#ede8e0", zeroline:false }},
    shapes: [
      {{ type:"rect", x0:fcDates[0], x1:fcDates[fcDates.length-1], y0:0, y1:1, yref:"paper",
         fillcolor:"rgba(200,195,185,0.07)", line:{{width:0}} }},
      {{ type:"line", x0:fcDates[0], x1:fcDates[0], y0:0, y1:1, yref:"paper",
         line:{{color:"#bbb",width:1,dash:"dot"}} }},
    ],
    annotations: [
      {{ x:fcDates[0], y:0.97, yref:"paper", text:"Inicio forecast", showarrow:false,
         font:{{family:"DM Mono",size:10,color:"#aaa"}}, xanchor:"left" }}
    ],
    legend: {{ font:{{family:"DM Sans",size:12}}, bgcolor:"rgba(255,255,255,0.9)",
               bordercolor:"#e2e0d9", borderwidth:1,
               orientation:"h", yanchor:"bottom", y:1.02, xanchor:"right", x:1 }},
    paper_bgcolor:"#ffffff", plot_bgcolor:"#ffffff",
    margin:{{ t:40, r:20, b:50, l:70 }},
    hovermode:"x unified",
  }}, {{ responsive:true, displayModeBar:false }});
}})();

// ── TABLE ─────────────────────────────────────────────
(function() {{
  const tbody = document.getElementById("table-body");
  distritos.forEach(d => {{
    const color = CLUSTER_COLORS[d.cluster_label];
    const sign  = d.yoy_accel > 0 ? "+" : "";
    const accelColor = d.yoy_accel > 5 ? "#2d7a4f" : d.yoy_accel < 0 ? "#b5291a" : "#555";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${{d.district_name}}</strong></td>
      <td><span class="cluster-badge">
        <span class="badge-dot" style="background:${{color}}"></span>
        ${{d.cluster_label}}
      </span></td>
      <td class="num">${{d.last_price.toLocaleString('es-ES')}}</td>
      <td class="num">${{d.avg_yoy_pct.toFixed(1)}}%</td>
      <td class="num" style="color:${{accelColor}};font-weight:500">${{sign}}${{d.yoy_accel.toFixed(1)}} pp</td>
      <td class="num">${{d.avg_cagr_5y.toFixed(2)}}%</td>
    `;
    tbody.appendChild(tr);
  }});
}})();
</script>
</body>
</html>
"""


def build_html(kpis, clusters, forecast, historical):
    """Inyecta datos usando placeholders __KEY__ para evitar conflictos
    entre str.format() y las llaves del JS en el template."""
    price_ratio = round(kpis["price_max"] / kpis["price_min"], 1)
    fmt = lambda v: f"{int(round(v)):,}".replace(",", ".")  # separador miles español
    replacements = {
        "__LAST_PRICE__":     fmt(kpis["last_price"]),
        "__YOY__":            str(kpis["yoy"]),
        "__PRICE_MIN__":      fmt(kpis["price_min"]),
        "__PRICE_MAX__":      fmt(kpis["price_max"]),
        "__PRICE_RATIO__":    str(price_ratio),
        "__FC_Q1__":          str(kpis["fc_q1"]),
        "__FC_Q1_LO__":       str(kpis["fc_q1_lo"]),
        "__FC_Q1_HI__":       str(kpis["fc_q1_hi"]),
        "__N_CLUSTERS__":     str(kpis["n_clusters"]),
        "__SILHOUETTE__":     str(kpis["silhouette"]),
        "__DISTRITOS_JSON__": json.dumps(clusters,  ensure_ascii=False),
        "__FORECAST_JSON__":  json.dumps(forecast,   ensure_ascii=False),
        "__HIST_JSON__":      json.dumps(historical, ensure_ascii=False),
        "__KPIS_JSON__":      json.dumps(kpis,       ensure_ascii=False),
    }
    html = HTML_TEMPLATE
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)
    # Desescapar llaves dobles que quedaron del antiguo str.format()
    html = html.replace("{{", "{").replace("}}", "}")
    return html


def main():
    print("Cargando datos...")
    df_cl, df_fc, df_hi = load_data()

    kpis       = compute_kpis(df_cl, df_fc, df_hi)
    clusters   = prepare_clusters(df_cl)
    forecast   = prepare_forecast(df_fc)
    historical = prepare_historical(df_hi)

    print(f"  Distritos:    {len(clusters)}")
    print(f"  Trimestres históricos (últimos 20): {len(historical)}")
    print(f"  Periodos forecast: {len(forecast)}")
    print(f"  KPIs: precio ciudad={kpis['last_price']} €/m², yoy={kpis['yoy']}%")

    html = build_html(kpis, clusters, forecast, historical)

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nDashboard generado: {OUT_HTML}")
    print("✓ Listo.")


if __name__ == "__main__":
    main()

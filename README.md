# Análisis del Mercado Inmobiliario de Sevilla
### Prueba técnica · Grupo Insur · Marzo 2026

Análisis end-to-end del mercado residencial de Sevilla que combina **extracción GenAI de informes sectoriales** con **ML clásico** (clustering de distritos y forecasting de precios). El proyecto demuestra cómo ambas capas se complementan para un problema real de negocio inmobiliario: la GenAI extrae y estructura información cualitativa que el ML no puede procesar directamente; el ML produce segmentaciones y previsiones cuantitativas que los informes narrativos no ofrecen.

Todos los datos son **públicos y verificables** (MIVAU, TINSA). La capa GenAI es **auditable**: los prompts están versionados y las respuestas raw de la API están guardadas en `data/interim/pdf_json/`.

---

## Qué contiene el entregable

| Artefacto | Ruta | Descripción |
|---|---|---|
| **Dashboard HTML** | `resultados/dashboard_insur.html` | Vista ejecutiva interactiva. Autocontenido, no requiere servidor. |
| **Clustering de distritos** | `resultados/distritos_clusters.csv` | 11 distritos segmentados en 4 perfiles con métricas detalladas. Basado en TINSA IMIE. |
| **Forecast de precio** | `resultados/forecast_valores.csv` | Previsión SARIMA + Prophet a nivel ciudad, basada en MIVAU. 2026Q1–2027Q2 con IC 80%. |
| **Resumen GenAI informes** | `resultados/resumen_ia_informes.md` | Síntesis ejecutiva de los 4 informes TINSA procesados con Claude API. |
| **Scripts reproducibles** | `scripts/` | Pipeline completo en 6 pasos, ejecutable desde cero. |
| **Decisiones técnicas** | `docs/decisiones_y_limitaciones.md` | Justificación detallada de cada elección metodológica relevante. |

---

## Cómo revisar el proyecto en 2 minutos

1. **Abrir** `resultados/dashboard_insur.html` en el navegador — visión completa del análisis: KPIs, clusters, forecast y tabla de distritos.
2. **Leer** `resultados/resumen_ia_informes.md` — qué extrajo la IA de los informes TINSA y qué señales identificó.
3. **Ojear** este README y `docs/decisiones_y_limitaciones.md` para entender las decisiones clave (fuentes, clustering, forecasting).
4. **Si se quiere reproducir**: ejecutar los 6 scripts en orden (ver sección _Pipeline_). Requiere Python 3.10+, dependencias en `requirements.txt` y variable de entorno `ANTHROPIC_API_KEY`.

---

## Estructura del repositorio

```
.
├── data/
│   ├── raw/                        # Datos originales sin modificar
│   │   ├── 35103500.XLS            # MIVAU — valor tasado vivienda libre, municipios
│   │   └── pdf_tinsa/              # Informes TINSA IMIE 1T–4T 2025 (PDF)
│   ├── interim/
│   │   ├── pdf_text/               # Texto extraído de los PDFs (pdfplumber)
│   │   └── pdf_json/               # JSONs estructurados por Claude API + respuestas raw
│   └── processed/
│       ├── mivau_sevilla_series.csv        # Serie trimestral 2005Q1–2025Q4
│       ├── tinsa_distritos_panel.csv       # Panel 11 distritos × 4 trimestres
│       └── dataset_distritos_features.csv  # Features para clustering
├── scripts/
│   ├── 01_ingest_mivau_xls.py
│   ├── 02_extract_tinsa_pdfs.py
│   ├── 03_extract_tinsa_genai.py
│   ├── 03_build_district_features.py
│   ├── 04_clustering.py
│   ├── 05_forecasting.py
│   └── 06_build_dashboard.py
├── prompts/
│   └── pdf_extraction_prompt_v1.txt   # Prompt Claude API, versionado
├── resultados/
│   ├── dashboard_insur.html
│   ├── distritos_clusters.csv
│   ├── forecast_valores.csv
│   ├── resumen_ia_informes.md
│   └── figuras/
│       ├── clusters_pca.html
│       └── clusters_precio_yoy.html
├── docs/
│   ├── decisiones_y_limitaciones.md
│   ├── fuentes_y_citas.md
│   └── claude_code_log.md
├── requirements.txt
└── README.md
```

---

## Pipeline de ejecución

Los scripts se ejecutan en orden desde la raíz del proyecto:

```bash
# 1. Extraer serie histórica de precio (MIVAU XLS → CSV)
python scripts/01_ingest_mivau_xls.py

# 2. Extraer texto de los PDFs TINSA (pdfplumber → TXT)
python scripts/02_extract_tinsa_pdfs.py

# 3a. Estructurar texto con Claude API (TXT → JSON)
python scripts/03_extract_tinsa_genai.py

# 3b. Construir features de distritos para clustering
python scripts/03_build_district_features.py

# 4. K-Means clustering de distritos (k=4, con stability check)
python scripts/04_clustering.py

# 5. Forecasting SARIMA + Prophet (evaluación + proyección 6T)
python scripts/05_forecasting.py

# 6. Generar dashboard HTML estático
python scripts/06_build_dashboard.py
```

---

## Requisitos y ejecución

**Python 3.10+**

```bash
pip install -r requirements.txt
```

**Variable de entorno necesaria** para el script GenAI (paso 3a):

```bash
# Windows
set ANTHROPIC_API_KEY=sk-ant-...

# Linux / macOS
export ANTHROPIC_API_KEY=sk-ant-...
```

Los demás scripts no requieren API key ni conexión a internet.

> **Nota sobre Claude Code:** Claude Code se utilizó como herramienta de apoyo al desarrollo durante la construcción del pipeline. El log de sesiones y decisiones tomadas con su asistencia está en `docs/claude_code_log.md`.

---

## Fuentes de datos

| Fuente | Descripción | Acceso |
|---|---|---|
| **MIVAU** | Valor tasado vivienda libre nueva, municipios >25.000 hab. Serie trimestral 2005Q1–2025Q4. | [transportes.gob.es](https://www.transportes.gob.es/el-ministerio/informacion-estadistica/vivienda-y-actuaciones-urbanas/estadisticas/valor-tasado-de-la-vivienda) · Archivo `35103500.XLS` · Descargado marzo 2026 |
| **TINSA IMIE** | Mercados Locales — Sevilla. Precio €/m² y variación interanual por distrito. | Informes trimestrales 1T–4T 2025, descargados desde [TINSA IMIE Mercados Locales](https://www.tinsa.es/mercados-locales/); PDFs incluidos en `data/raw/pdf_tinsa/` · Tabla de distritos, p. 24 |

**Nota:** ambas fuentes miden conceptos distintos (valor tasado vs. precio de mercado TINSA) y **no se mezclan para modelar**. MIVAU se usa para forecasting a nivel ciudad; TINSA para clustering de distritos. La comparación entre ambas es únicamente narrativa.

---

## Resultados principales

- **MIVAU sitúa Sevilla en 2.805 €/m² en 4T 2025** (vivienda nueva), serie utilizada como base del forecasting a nivel ciudad. TINSA IMIE registra una aceleración interanual intensa durante 2025, con +12,4% en el conjunto de la ciudad en 4T.
- **4 perfiles de distrito identificados**: Premium consolidado (Casco Antiguo, Nervión, >3.100 €/m²), Mercado estabilizado (Los Remedios enfriándose pese a precio alto), Dinamismo sostenido (5 distritos de clase media en crecimiento estable) y Alta tracción emergente (San Pablo-Santa Justa, aceleración +14 pp, singleton estadísticamente estable en 20 runs).
- **Forecast SARIMA (MAPE 3,04% en test)**: precios convergen hacia 2.720–2.890 €/m² en 2026–2027, señalando normalización gradual tras el ciclo alcista. SARIMA supera los baselines naive (4,44%) y seasonal (4,97%).
- **La capa GenAI extrae y estructura cualitativamente** tendencias, señales cualitativas y contexto macro de 4 informes TINSA, integrándose con el análisis cuantitativo sin mezclar fuentes para modelar.

---

## Limitaciones y decisiones técnicas

Las decisiones metodológicas relevantes (selección de features, k=4, uso de `price_nueva_eur_m2` para forecasting, tratamiento del cluster unitario, rol de Prophet, separación de fuentes MIVAU/TINSA) están documentadas en detalle en:

📄 [`docs/decisiones_y_limitaciones.md`](docs/decisiones_y_limitaciones.md)

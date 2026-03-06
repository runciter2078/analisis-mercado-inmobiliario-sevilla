# Log de uso de Claude Code

## Contexto

Claude Code se utilizó como herramienta de apoyo al desarrollo durante la construcción del pipeline. Este documento describe el rol que tuvo, qué partes del proyecto asistió y cuáles fueron desarrolladas de forma autónoma.

---

## Sesiones representativas

Registro de usos concretos durante el desarrollo del proyecto:

```
2026-03-02 10:15 — Scaffold inicial
  Petición: generar estructura de carpetas del proyecto y esqueleto de scripts numerados.
  Resultado: borradores de 01_ingest_mivau_xls.py y 02_extract_tinsa_pdfs.py.

2026-03-02 16:30 — Diseño pipeline GenAI
  Petición: separar extracción de texto (pdfplumber) y estructuración (Claude API) en scripts distintos.
  Resultado: arquitectura de 2 fases; borrador de 03_extract_tinsa_genai.py con manejo de errores.

2026-03-03 09:20 — Depuración JSONDecodeError
  Petición: script falla cuando Claude API devuelve JSON envuelto en bloques markdown.
  Resultado: strip defensivo de bloques ```json ... ``` añadido permanentemente antes del parse.

2026-03-03 14:45 — Stability check clustering
  Petición: primera versión del stability check daba resultados bajos (~50%) por label switching de K-Means.
  Resultado: reescritura usando co-ocurrencia de pares, independiente del ID numérico asignado.

2026-03-04 11:00 — Conflicto llaves JS en dashboard
  Petición: ValueError al generar HTML por conflicto entre str.format() y llaves CSS/JS del template.
  Resultado: sistema de placeholders __KEY__ + desescapado explícito de {{ y }} tras las sustituciones.

2026-03-04 17:30 — Revisión decisiones técnicas
  Petición: auditoría del framing de Prophet y de la explicación de la oscilación Q4→Q1 en SARIMA.
  Resultado: textos ajustados en dashboard y decisiones_y_limitaciones.md para no sobreprometer.
```

---



Claude Code actuó como asistente de desarrollo iterativo: generación de borradores de scripts, depuración de errores, sugerencias de arquitectura y revisión de decisiones metodológicas. En ningún caso ejecutó código de forma autónoma ni tomó decisiones de negocio o de modelado sin supervisión.

Todas las decisiones técnicas relevantes (selección de features, elección de k, modelos de forecasting, diseño del prompt GenAI, separación de fuentes) fueron tomadas, revisadas y validadas por el autor del proyecto. Las decisiones están documentadas en `docs/decisiones_y_limitaciones.md`.

---

## Asistencia por script

| Script | Asistencia Claude Code | Decisiones del autor |
|---|---|---|
| `01_ingest_mivau_xls.py` | Estructura de extracción con `xlrd`, regex para localizar fila Sevilla | Selección de variable `price_nueva_eur_m2`, tratamiento de NaNs |
| `02_extract_tinsa_pdfs.py` | Borrador inicial con `pdfplumber` | Detección de limitación (tablas como imagen), decisión de pipeline en 2 fases |
| `03_extract_tinsa_genai.py` | Estructura de llamada a API, manejo de errores JSON | Diseño del prompt, instrucciones anti-alucinación, esquema de campos |
| `03_build_district_features.py` | Generación de features derivadas | Selección de las 5 features finales para clustering, exclusión de redundantes |
| `04_clustering.py` | Implementación K-Means, silhouette sweep, PCA para visualización | Selección k=4, diseño del stability check por co-ocurrencia, interpretación de perfiles |
| `05_forecasting.py` | Estructura SARIMA + Prophet, evaluación train/test | Separación temporal estricta, elección IC 80%, decisión de no hacer tuning de Prophet |
| `06_build_dashboard.py` | Template HTML, integración Plotly, sistema de placeholders | Arquitectura de 4 bloques, selección de KPIs, separación visual MIVAU/TINSA |

---

## Depuración asistida

Los principales problemas técnicos resueltos con asistencia de Claude Code:

- **`JSONDecodeError` en extracción GenAI:** Claude API devolvía ocasionalmente respuestas envueltas en bloques markdown (` ```json ... ``` `). Solución: strip defensivo aplicado permanentemente antes del parse.
- **Conflicto `str.format()` con llaves JS en template HTML:** El template contenía `{{` y `}}` para escapar CSS/JS. Al cambiar a sistema de placeholders `__KEY__`, las llaves dobles quedaron literales. Solución: desescapado explícito tras las sustituciones.
- **Stability check por label switching:** Primera versión del stability check medía coincidencia de etiquetas numéricas, dando resultados bajos (~50%) por el label switching de K-Means entre ejecuciones. Solución: reescritura usando co-ocurrencia de pares, independiente del ID numérico asignado.

---

## Partes desarrolladas sin asistencia de Claude Code

- Transcripción manual de tablas de distritos desde PDFs TINSA
- Diseño del prompt de extracción GenAI y sus instrucciones anti-alucinación
- Interpretación de negocio de los 4 perfiles de clustering
- Redacción de documentación (README, este documento, `decisiones_y_limitaciones.md`)

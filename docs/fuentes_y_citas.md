# Fuentes y citas

## Fuente 1 — MIVAU (Ministerio de Vivienda y Agenda Urbana)

**Nombre oficial:** Valor tasado de la vivienda libre. Municipios con más de 25.000 habitantes.
**Organismo:** Ministerio de Transportes, Movilidad y Agenda Urbana (MITMA) / Ministerio de Vivienda y Agenda Urbana (MIVAU).
**URL de acceso:** https://www.transportes.gob.es/el-ministerio/informacion-estadistica/vivienda-y-actuaciones-urbanas/estadisticas/valor-tasado-de-la-vivienda
**Archivo descargado:** `35103500.XLS` (municipios >25.000 habitantes, todas las provincias)
**Fecha de descarga:** Marzo 2026
**Cobertura temporal:** 2005Q1–2025Q4 (84 trimestres)
**Variable utilizada:** `price_nueva_eur_m2` — valor tasado vivienda libre nueva, €/m²
**Municipio:** Sevilla (código INE 41091)
**Uso en el proyecto:** Serie base para forecasting a nivel ciudad (scripts 01 y 05)

---

## Fuente 2 — TINSA IMIE Mercados Locales

**Nombre oficial:** TINSA IMIE Mercados Locales
**Organismo:** TINSA (Tasaciones Inmobiliarias S.A.)
**URL de referencia:** https://www.tinsa.es/mercados-locales/
**Archivos incluidos en el repositorio:**

| Archivo | Trimestre | Página utilizada |
|---|---|---|
| `data/raw/pdf_tinsa/tinsa_imie_mercados_locales_1t2025.pdf` | 1T 2025 | p. 24 |
| `data/raw/pdf_tinsa/tinsa_imie_mercados_locales_2t2025.pdf` | 2T 2025 | p. 24 |
| `data/raw/pdf_tinsa/tinsa_imie_mercados_locales_3t2025.pdf` | 3T 2025 | p. 24 |
| `data/raw/pdf_tinsa/tinsa_imie_mercados_locales_4t2025.pdf` | 4T 2025 | p. 24 |

**Datos extraídos:** Precio €/m² y variación interanual (%) por distrito de Sevilla.
**Método de extracción:** Transcripción manual de tablas (renderizadas como imagen en el PDF). Claude API se utilizó para estructurar el contenido narrativo de los informes; los valores tabulares por distrito se verificaron manualmente contra la tabla original del PDF.
**Uso en el proyecto:** Features de clustering de distritos (scripts 03 y 04)

---

## Nota sobre separación de fuentes

Ambas fuentes miden conceptos distintos:
- MIVAU: **valor tasado** de vivienda libre nueva (estimación pericial)
- TINSA: **precio de mercado** según informes propios TINSA

No se cruzan ni mezclan para modelar. Cualquier comparación entre valores de ambas fuentes en el análisis es únicamente narrativa e ilustrativa.

---

## Herramientas y librerías

Las librerías de Python utilizadas y sus versiones están especificadas en `requirements.txt`.

La extracción GenAI utiliza la API de Anthropic (modelo `claude-sonnet-4-20250514`). El prompt empleado está versionado en `prompts/pdf_extraction_prompt_v1.txt`.

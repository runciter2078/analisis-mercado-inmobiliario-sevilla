# Resumen ejecutivo — Mercado inmobiliario Sevilla 2025
_Generado automáticamente a partir de informes TINSA IMIE Mercados Locales (1T–4T 2025)_
_Extracción realizada con Claude API (claude-sonnet-4-20250514). Prompt: prompts/pdf_extraction_prompt_v1.txt_

---

## 1. Evolución del precio medio en Sevilla ciudad

| Trimestre | €/m² | Var. interanual |
|-----------|------|-----------------|
| 1T 2025 | 2221 | 5.6% |
| 2T 2025 | 2354 | 11.4% |
| 3T 2025 | 2414 | 12.4% |
| 4T 2025 | 2466 | 12.4% |

---

## 2. Factores clave identificados por trimestre

### 1T 2025

### 2T 2025

### 3T 2025

### 4T 2025

---

## 3. Contexto macro nacional

- **1T 2025**: España 1902 €/m², variación 7.5%
- **2T 2025**: España 1955 €/m², variación 9.8%
- **3T 2025**: España 2018 €/m², variación 11.7%

---

## 4. Nota metodológica

- Fuente: TINSA IMIE Mercados Locales, trimestres 1T–4T 2025.
- Extracción automática de texto mediante pdfplumber.
- Estructuración de datos mediante Claude API con prompt fijo (ver `prompts/pdf_extraction_prompt_v1.txt`).
- Las tablas numéricas de distritos no fueron capturadas por extracción automática (renderizadas como imagen en los PDFs); los datos de distritos proceden de transcripción manual validada visualmente.
- Los campos marcados como `null` en los JSONs intermedios indican ausencia explícita en el texto, no error de extracción.
- Los JSONs intermedios por informe están en `data/interim/pdf_json/`.
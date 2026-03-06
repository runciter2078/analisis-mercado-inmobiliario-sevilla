# Decisiones técnicas y limitaciones del proyecto

## 1. Fuentes de datos y separación metodológica

**Decisión:** Se utilizan dos fuentes independientes con propósitos distintos y sin mezclarlas para modelar.

- **MIVAU** (Ministerio de Transportes): valor tasado vivienda libre nueva, serie trimestral 2005Q1–2025Q4. Utilizada exclusivamente para el forecasting a nivel ciudad, por su extensión temporal (84 trimestres) y continuidad.
- **TINSA IMIE Mercados Locales**: precio por distrito, 2025 (4 trimestres). Utilizada exclusivamente para el clustering de distritos, por ser la única fuente con desagregación geográfica disponible.

Ambas fuentes miden conceptos distintos (valor tasado vs. precio de mercado TINSA). La comparación entre ellas es únicamente narrativa y no alimenta ningún modelo.

**Limitación:** La serie TINSA de distritos cubre solo 4 trimestres (2025), lo que limita la riqueza de las features temporales del clustering. Con más historia por distrito sería posible construir features de tendencia más robustas y explorar modelos de forecasting a nivel de distrito.

---

## 2. Extracción GenAI de informes TINSA

**Decisión:** Se diseñó un pipeline en dos fases separadas: primero extracción de texto con `pdfplumber` y después estructuración con Claude API (`claude-sonnet-4-20250514`).

La separación permite auditar cada fase de forma independiente: los textos intermedios están en `data/interim/pdf_text/` y las respuestas raw de la API en `data/interim/pdf_json/*_raw.txt`.

El prompt está versionado en `prompts/pdf_extraction_prompt_v1.txt` e incluye instrucciones explícitas anti-alucinación: "extrae SOLO lo que aparezca en el documento; si un campo no existe, devuelve null". Esta decisión de diseño es deliberada para garantizar trazabilidad y evitar que el modelo infiera datos no presentes en los PDFs.

**Limitación:** Las tablas de distritos no eran extraíbles en formato tabular limpio por `pdfplumber`, pero los valores numéricos sí estaban presentes en el texto plano del PDF. Claude API los identificó y estructuró correctamente. La extracción se validó manualmente contra la tabla original del informe (11/11 coincidencias en `IMIE4T2025.pdf`, p. 24). La transcripción manual actuó como validación independiente, no como fuente alternativa.

Los campos de "drivers" del mercado aparecen vacíos o nulos en la mayoría de informes porque los PDFs TINSA Sevilla no los detallan de forma estructurada; el pipeline los captura correctamente como null en lugar de inferirlos.

---

## 3. Construcción de features para clustering

**Decisión:** Se construyeron 13 features a partir del panel de 44 registros (11 distritos × 4 trimestres) y se seleccionaron 5 para el modelo:

```
last_price      — nivel de precio actual (4T 2025)
avg_yoy_pct     — dinamismo medio durante 2025
yoy_accel       — aceleración interanual (último trimestre - primero)
avg_cagr_5y     — rendimiento estructural a 5 años
price_vol       — volatilidad intra-2025 del precio
```

Se excluyeron features redundantes (p. ej. `avg_price` es altamente correlacionada con `last_price`) y features con escasa variabilidad entre distritos. La selección busca capturar nivel de precio, dinamismo reciente, tendencia estructural y estabilidad, que son las dimensiones relevantes para decisiones de inversión inmobiliaria.

---

## 4. Selección de k en K-Means

**Decisión:** k=4 seleccionado por máximo silhouette score (0.257) en el rango k=2..5.

| k | Silhouette |
|---|---|
| 2 | 0.249 |
| 3 | 0.231 |
| **4** | **0.257** |
| 5 | 0.254 |

k=5 tiene silhouette similar (0.254) pero genera segmentos de 1–2 distritos en varios clusters, perdiendo valor interpretativo con n=11. k=2 pierde granularidad narrativa útil para negocio. k=4 ofrece el mejor equilibrio entre separabilidad estadística e interpretabilidad.

**Limitación:** Con n=11 distritos, cualquier solución de clustering debe interpretarse con cautela. Los perfiles identificados tienen valor descriptivo y orientativo, no predictivo en sentido estricto.

---

## 5. Cluster unitario San Pablo-Santa Justa

**Decisión:** San Pablo-Santa Justa forma un cluster de un solo elemento. Se validó su estabilidad mediante un stability check por co-ocurrencia: en 20 ejecuciones de K-Means con `random_state` distintos, este distrito obtuvo **0% de co-ocurrencia** con cualquier otro, es decir, nunca compartió cluster con ningún vecino. Esto indica que su perfil es suficientemente diferenciado como para que el algoritmo lo aísle consistentemente, independientemente de la inicialización.

**Limitación:** Un cluster de un solo distrito tiene limitaciones prácticas evidentes. Su interpretación como "perfil emergente de alta tracción" es válida como señal de comportamiento diferenciado en 2025, pero debe tratarse con prudencia por estar basado en 4 observaciones de un único distrito.

---

## 6. Forecasting: elección de modelos y evaluación

**Decisión:** Se implementaron SARIMA y Prophet con una separación temporal estricta: train hasta 2023Q4, test en 2024Q1–2025Q4 (8 trimestres), forecast en 2026Q1–2027Q2.

SARIMA(1,1,1)×(1,1,1,4) se seleccionó con `auto_arima` (criterio AIC). Prophet se configuró con estacionalidad multiplicativa. Ambos modelos se evaluaron sobre el mismo conjunto de test antes de producir el forecast final.

| Modelo | MAPE test | MAE test |
|---|---|---|
| Naive (último valor) | 4,44% | 113,8 €/m² |
| Seasonal naive | 4,97% | 130,9 €/m² |
| **SARIMA** | **3,04%** | **76,5 €/m²** |
| Prophet | 19,54% | 511,2 €/m² |

SARIMA es el modelo de decisión por rendimiento out-of-sample demostrado. Prophet se mantiene como referencia comparativa; con configuración estándar y sin tuning específico, no captura la aceleración brusca observada en 2024–2025. Dado el alcance de esta prueba, no se realizó tuning exhaustivo de Prophet.

**Sobre la oscilación intraanual de SARIMA:** El forecast muestra una caída entre 2026Q4 (2.891 €/m²) y 2027Q1 (2.805 €/m²), seguida de recuperación en 2027Q2 (2.837 €/m²). Este patrón es compatible con el componente estacional trimestral (s=4) estimado por el modelo sobre la serie 2005–2025. La tendencia anual del forecast sigue siendo moderadamente alcista (~2–3% anual), frente al +12% registrado en 2025, lo que señala normalización del mercado tras el ciclo alcista reciente.

**Intervalo de confianza al 80%:** Se eligió IC 80% en lugar de 95% para una lectura ejecutiva más informativa. El IC 95% en series de precio con componente de tendencia tiende a ser muy amplio y reduce la utilidad práctica del forecast.

**Limitación:** El forecast se basa en una única serie de precio agregado a nivel ciudad (MIVAU). No incorpora variables exógenas (tipos de interés, oferta de obra nueva, migración, etc.) que podrían mejorar la precisión pero requerirían datos adicionales y un modelo de mayor complejidad.

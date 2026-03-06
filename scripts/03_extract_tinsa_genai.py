"""
03_extract_tinsa_genai.py  —  FASE 2: texto -> JSON estructurado con Claude API
Lee los ficheros _sevilla.txt generados en la fase 1 y extrae información
estructurada usando Claude. Guarda un JSON por informe y un resumen consolidado.

Ejecutar desde la raíz del proyecto:
    python scripts/03_extract_tinsa_genai.py
"""

import json
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# ── Configuración ─────────────────────────────────────────────────────────────
load_dotenv()

ROOT        = Path(__file__).resolve().parent.parent
TEXT_DIR    = ROOT / "data" / "interim" / "pdf_text"
JSON_DIR    = ROOT / "data" / "interim" / "pdf_json"
PROMPT_FILE = ROOT / "prompts" / "pdf_extraction_prompt_v1.txt"
RESULTS_DIR = ROOT / "resultados"

JSON_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL    = "claude-sonnet-4-20250514"
MAX_TOKENS = 2000

# Mapeo nombre de fichero -> periodo legible
PERIOD_MAP = {
    "IMIE-TINSA-1T-2025": "1T 2025",
    "IMIE2T2025":         "2T 2025",
    "IMIE32T25":          "3T 2025",
    "IMIE4T2025":         "4T 2025",
}


def load_prompt_template() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def extract_json_from_text(text: str, report_id: str, client: anthropic.Anthropic, prompt_template: str) -> dict:
    """Llama a Claude con el texto del informe y devuelve el JSON extraído."""
    prompt = prompt_template.replace("{texto}", text)

    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}]
    )

    #raw = message.content[0].text.strip()
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # Guardar respuesta raw para auditoría
    raw_path = JSON_DIR / f"{report_id}_raw.txt"
    raw_path.write_text(raw, encoding="utf-8")

    # Parsear JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ERROR parseando JSON de {report_id}: {e}")
        print(f"  Respuesta raw guardada en {raw_path}")
        data = {"error": str(e), "raw": raw}

    return data


def build_summary(all_results: list[dict]) -> str:
    """Genera resumen ejecutivo en markdown a partir de los JSONs extraídos."""
    lines = [
        "# Resumen ejecutivo — Mercado inmobiliario Sevilla 2025",
        "_Generado automáticamente a partir de informes TINSA IMIE Mercados Locales (1T–4T 2025)_",
        "_Extracción realizada con Claude API (claude-sonnet-4-20250514). Prompt: prompts/pdf_extraction_prompt_v1.txt_",
        "",
        "---",
        "",
        "## 1. Evolución del precio medio en Sevilla ciudad",
        "",
    ]

    # Tabla de evolución trimestral
    lines.append("| Trimestre | €/m² | Var. interanual |")
    lines.append("|-----------|------|-----------------|")
    for r in all_results:
        if "error" in r:
            continue
        period = r.get("report_period", "n.d.")
        city   = r.get("seville_city", {})
        price  = city.get("price_eur_m2", "n.d.")
        yoy    = city.get("yoy_change_pct", "n.d.")
        yoy_str = f"{yoy}%" if yoy is not None else "n.d."
        lines.append(f"| {period} | {price} | {yoy_str} |")

    lines += ["", "---", "", "## 2. Factores clave identificados por trimestre", ""]

    for r in all_results:
        if "error" in r:
            continue
        period  = r.get("report_period", "n.d.")
        city    = r.get("seville_city", {})
        drivers = city.get("key_drivers", [])
        risks   = city.get("risks", [])
        outlook = city.get("outlook")

        lines.append(f"### {period}")
        if drivers:
            lines.append("**Impulsores:**")
            for d in drivers:
                lines.append(f"- {d}")
        if risks:
            lines.append("**Riesgos:**")
            for rk in risks:
                lines.append(f"- {rk}")
        if outlook:
            lines.append(f"**Perspectiva:** {outlook}")
        lines.append("")

    lines += ["---", "", "## 3. Contexto macro nacional", ""]
    for r in all_results:
        if "error" in r:
            continue
        period = r.get("report_period", "n.d.")
        macro  = r.get("macro_context", {})
        nat_price = macro.get("national_price_eur_m2")
        nat_yoy   = macro.get("national_yoy_change_pct")
        if nat_price or nat_yoy:
            lines.append(f"- **{period}**: España {nat_price} €/m², variación {nat_yoy}%")

    lines += [
        "",
        "---",
        "",
        "## 4. Nota metodológica",
        "",
        "- Fuente: TINSA IMIE Mercados Locales, trimestres 1T–4T 2025.",
        "- Extracción automática de texto mediante pdfplumber.",
        "- Estructuración de datos mediante Claude API con prompt fijo (ver `prompts/pdf_extraction_prompt_v1.txt`).",
        "- Las tablas numéricas de distritos no fueron capturadas por extracción automática (renderizadas como imagen en los PDFs); los datos de distritos proceden de transcripción manual validada visualmente.",
        "- Los campos marcados como `null` en los JSONs intermedios indican ausencia explícita en el texto, no error de extracción.",
        "- Los JSONs intermedios por informe están en `data/interim/pdf_json/`.",
    ]

    return "\n".join(lines)


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY no encontrada. Comprueba el fichero .env")

    client = anthropic.Anthropic(api_key=api_key)
    prompt_template = load_prompt_template()

    print(f"Prompt cargado: {PROMPT_FILE.name}")
    print(f"Modelo: {MODEL}\n")

    all_results = []

    for stem, period in PERIOD_MAP.items():
        txt_path = TEXT_DIR / f"{stem}_sevilla.txt"
        if not txt_path.exists():
            print(f"AVISO: no encontrado {txt_path.name}, saltando.")
            continue

        print(f"Procesando: {stem} ({period})")
        text = txt_path.read_text(encoding="utf-8")
        print(f"  Caracteres de texto: {len(text):,}")

        result = extract_json_from_text(text, stem, client, prompt_template)

        # Inyectar metadatos si no vienen del modelo
        if "report_id" not in result or not result["report_id"]:
            result["report_id"] = stem
        if "report_period" not in result or not result["report_period"]:
            result["report_period"] = period

        # Guardar JSON
        json_path = JSON_DIR / f"{stem}.json"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSON guardado: {json_path.name}")

        # Preview rápido
        city = result.get("seville_city", {})
        print(f"  Sevilla: {city.get('price_eur_m2')} €/m², "
              f"var. {city.get('yoy_change_pct')}%, "
              f"tendencia: {city.get('trend')}")
        print()

        all_results.append(result)

    # Resumen consolidado
    summary_path = RESULTS_DIR / "resumen_ia_informes.md"
    summary = build_summary(all_results)
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Resumen ejecutivo guardado: {summary_path}")
    print(f"\nFase 2 completada. JSONs en data/interim/pdf_json/")


if __name__ == "__main__":
    main()

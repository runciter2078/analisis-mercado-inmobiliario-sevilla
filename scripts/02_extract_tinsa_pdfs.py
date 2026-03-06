"""
02_extract_tinsa_pdfs.py  —  FASE 1: PDF -> texto
Extrae el texto de cada informe TINSA IMIE y lo guarda en
data/interim/pdf_text/<nombre>.txt para su posterior procesado con Claude API.

Ejecutar desde la raíz del proyecto:
    python scripts/02_extract_tinsa_pdfs.py
"""

import pdfplumber
from pathlib import Path

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
PDF_DIR   = ROOT / "data" / "raw" / "pdf_tinsa"
OUT_DIR   = ROOT / "data" / "interim" / "pdf_text"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Palabras clave para localizar páginas relevantes de Sevilla
SEVILLA_KEYWORDS = ["sevilla", "seville"]


def extract_text_from_pdf(pdf_path: Path) -> dict:
    """
    Extrae el texto completo y el texto de páginas que mencionan Sevilla.
    Devuelve un dict con:
        - full_text: texto completo del PDF
        - sevilla_pages: lista de (num_pagina, texto) donde aparece Sevilla
        - n_pages: total de páginas
    """
    full_pages = []
    sevilla_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            full_pages.append(text)
            if any(kw in text.lower() for kw in SEVILLA_KEYWORDS):
                sevilla_pages.append((i, text))

    return {
        "full_text":    "\n\n--- PÁGINA {} ---\n\n".join([""] + full_pages).strip(),
        "sevilla_pages": sevilla_pages,
        "n_pages":      n_pages,
    }


def save_texts(pdf_path: Path, result: dict):
    """Guarda texto completo y texto filtrado de Sevilla."""
    stem = pdf_path.stem

    # Texto completo
    full_out = OUT_DIR / f"{stem}_full.txt"
    full_out.write_text(result["full_text"], encoding="utf-8")

    # Solo páginas con Sevilla (más manejable para el prompt de Claude)
    sevilla_text = ""
    for page_num, text in result["sevilla_pages"]:
        sevilla_text += f"\n\n=== PÁGINA {page_num} ===\n\n{text}"

    sevilla_out = OUT_DIR / f"{stem}_sevilla.txt"
    sevilla_out.write_text(sevilla_text.strip(), encoding="utf-8")

    return full_out, sevilla_out


def main():
    pdfs = sorted(PDF_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No se encontraron PDFs en {PDF_DIR}")
        return

    print(f"PDFs encontrados: {len(pdfs)}\n")

    for pdf_path in pdfs:
        print(f"Procesando: {pdf_path.name}")
        result = extract_text_from_pdf(pdf_path)

        print(f"  Total páginas : {result['n_pages']}")
        print(f"  Páginas Sevilla: {len(result['sevilla_pages'])} "
              f"(págs. {[p for p, _ in result['sevilla_pages']]})")

        full_out, sevilla_out = save_texts(pdf_path, result)
        print(f"  Guardado texto completo : {full_out.name}")
        print(f"  Guardado texto Sevilla  : {sevilla_out.name}")

        # Preview rápido de lo que hay en páginas Sevilla
        if result["sevilla_pages"]:
            preview = result["sevilla_pages"][0][1][:300].replace("\n", " ")
            print(f"  Preview pág {result['sevilla_pages'][0][0]}: {preview}...")
        print()

    print("Fase 1 completada. Revisa data/interim/pdf_text/ antes de pasar a Claude.")


if __name__ == "__main__":
    main()

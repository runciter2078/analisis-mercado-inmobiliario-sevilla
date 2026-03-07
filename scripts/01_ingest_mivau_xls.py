"""
01_ingest_mivau_xls.py
Extrae la serie histórica trimestral de precio €/m² para Sevilla
desde el XLS del Ministerio de Transportes (35103500.XLS).

Salida: data/processed/mivau_sevilla_series.csv
"""

import re
import pandas as pd
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
XLS_PATH = ROOT / "data" / "raw" / "35103500.XLS"
OUT_PATH = ROOT / "data" / "processed" / "mivau_sevilla_series.csv"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Constantes ────────────────────────────────────────────────────────────────
MUNICIPIO_COL = 2       # columna índice donde aparece el nombre del municipio
NUEVA_COL     = 3       # precio vivienda nueva (hasta 5 años)
USADA_COL     = 4       # precio vivienda usada (más de 5 años)
MUNICIPIO_STR = "Sevilla"
SHEET_PATTERN = re.compile(r"T(\d)A(\d{4})", re.IGNORECASE)


def parse_sheet_name(name: str):
    """Devuelve (quarter, year) desde 'T1A2005', 'T2A2006 ', etc."""
    m = SHEET_PATTERN.match(name.strip())
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def extract_sevilla(xls: pd.ExcelFile, sheet_name: str):
    """Lee una hoja y devuelve el precio de Sevilla o None si no se encuentra."""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    mask = df[MUNICIPIO_COL].astype(str).str.strip().str.lower() == MUNICIPIO_STR.lower()
    rows = df[mask]
    if rows.empty:
        return None, None
    row = rows.iloc[0]
    nueva = row[NUEVA_COL]
    usada = row[USADA_COL]
    # Convertir a float; 'n.r' u otros strings -> NaN
    def to_float(v):
        try:
            return float(v)
        except (ValueError, TypeError):
            return float("nan")
    return to_float(nueva), to_float(usada)


def main():
    print(f"Leyendo: {XLS_PATH}")
    xls = pd.ExcelFile(XLS_PATH)

    records = []
    skipped = []

    for raw_name in xls.sheet_names:
        quarter, year = parse_sheet_name(raw_name)
        if quarter is None:
            skipped.append(raw_name)
            continue

        price_nueva, price_usada = extract_sevilla(xls, raw_name)

        if price_nueva is None and price_usada is None:
            print(f"  AVISO: Sevilla no encontrada en hoja '{raw_name}'")
            continue

        period = f"{year}Q{quarter}"
        records.append({
            "period":       period,
            "year":         year,
            "quarter":      quarter,
            "municipio":    MUNICIPIO_STR,
            "price_nueva_eur_m2": price_nueva,
            "price_usada_eur_m2": price_usada,
        })

    if skipped:
        print(f"Hojas ignoradas (no coinciden con patrón TxAxxxx): {skipped}")

    # ── Construcción del DataFrame ────────────────────────────────────────────
    df = pd.DataFrame(records)
    df = df.sort_values(["year", "quarter"]).reset_index(drop=True)

    # ── Validaciones ──────────────────────────────────────────────────────────
    print(f"\nTotal trimestres extraídos: {len(df)}")

    # 1. Trimestres esperados entre el primero y el último
    expected = (df["year"].max() - df["year"].min()) * 4 + df.loc[df["year"] == df["year"].max(), "quarter"].max()
    if len(df) < expected:
        print(f"  AVISO: se esperaban ~{expected} trimestres, se obtuvieron {len(df)}")

    # 2. Duplicados
    dupes = df[df.duplicated("period")]
    if not dupes.empty:
        print(f"  AVISO: periods duplicados:\n{dupes}")

    # 3. Rango de valores razonable (100–10000 €/m²)
    for col in ["price_nueva_eur_m2", "price_usada_eur_m2"]:
        out_of_range = df[(df[col] < 100) | (df[col] > 10000)]
        if not out_of_range.empty:
            print(f"  AVISO: valores fuera de rango en {col}:\n{out_of_range[['period', col]]}")

    # 4. NaNs
    nan_counts = df[["price_nueva_eur_m2", "price_usada_eur_m2"]].isna().sum()
    if nan_counts.any():
        print(f"  NaNs por columna:\n{nan_counts}")

    # ── Exportar ──────────────────────────────────────────────────────────────
    df.to_csv(OUT_PATH, index=False)
    print(f"\nCSV exportado: {OUT_PATH}")
    print(df.tail(8).to_string(index=False))


if __name__ == "__main__":
    main()

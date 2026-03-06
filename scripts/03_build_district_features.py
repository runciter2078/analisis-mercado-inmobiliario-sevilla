"""
03_build_district_features.py
A partir de tinsa_distritos_panel.csv construye dataset_distritos_features.csv:
una fila por distrito con features derivadas para clustering K-Means.

Ejecutar desde la raíz del proyecto:
    python scripts/03_build_district_features.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
PANEL    = ROOT / "data" / "processed" / "tinsa_distritos_panel.csv"
OUT_PATH = ROOT / "data" / "processed" / "dataset_distritos_features.csv"

# Orden cronológico de periodos
PERIOD_ORDER = ["1T2025", "2T2025", "3T2025", "4T2025"]


def compute_trend_slope(values: pd.Series) -> float:
    """Pendiente de regresión lineal simple (normalizada por nº observaciones)."""
    y = values.dropna().values
    if len(y) < 2:
        return np.nan
    x = np.arange(len(y))
    slope, _, _, _, _ = stats.linregress(x, y)
    return round(slope, 2)


def main():
    df = pd.read_csv(PANEL)
    print(f"Panel cargado: {df.shape[0]} filas, {df['district_name'].nunique()} distritos")

    # Orden cronológico
    df["period"] = pd.Categorical(df["period"], categories=PERIOD_ORDER, ordered=True)
    df = df.sort_values(["district_name", "period"]).reset_index(drop=True)

    features = []

    for district, grp in df.groupby("district_name"):
        grp = grp.sort_values("period")
        prices = grp["price_eur_m2"]
        yoys   = grp["yoy_change_pct"]
        cagrs  = grp["cagr_5y_pct"]

        # ── Features de precio ────────────────────────────────────────────────
        last_price   = prices.iloc[-1]
        first_price  = prices.iloc[0]
        avg_price    = prices.mean()
        price_growth = round((last_price - first_price) / first_price * 100, 2)  # % en 4 trimestres
        price_vol    = round(prices.std(), 1)           # volatilidad (std)
        price_slope  = compute_trend_slope(prices)      # tendencia lineal

        # ── Features de variación interanual ─────────────────────────────────
        last_yoy  = yoys.iloc[-1]
        avg_yoy   = round(yoys.mean(), 2)
        min_yoy   = yoys.min()                          # peor trimestre
        yoy_accel = round(yoys.iloc[-1] - yoys.iloc[0], 2)  # aceleración (último - primero)

        # ── Features de CAGR ─────────────────────────────────────────────────
        avg_cagr  = round(cagrs.mean(), 2)
        last_cagr = cagrs.iloc[-1]

        # ── Datos de completitud ──────────────────────────────────────────────
        missing_rate = round(grp[["price_eur_m2", "yoy_change_pct"]].isna().mean().mean(), 2)

        features.append({
            "district_name":  district,
            "last_price":     last_price,
            "avg_price":      round(avg_price, 1),
            "price_growth_4q_pct": price_growth,
            "price_vol":      price_vol,
            "price_slope":    price_slope,
            "last_yoy_pct":   last_yoy,
            "avg_yoy_pct":    avg_yoy,
            "min_yoy_pct":    min_yoy,
            "yoy_accel":      yoy_accel,
            "avg_cagr_5y":    avg_cagr,
            "last_cagr_5y":   last_cagr,
            "missing_rate":   missing_rate,
        })

    feat_df = pd.DataFrame(features).sort_values("last_price", ascending=False).reset_index(drop=True)

    # ── Validaciones ──────────────────────────────────────────────────────────
    print(f"\nDataset features: {feat_df.shape[0]} distritos × {feat_df.shape[1]} columnas")

    nans = feat_df.isna().sum()
    if nans.any():
        print(f"  NaNs detectados:\n{nans[nans > 0]}")
    else:
        print("  Sin NaNs ✓")

    print(f"\n  Rango de precios: {feat_df['last_price'].min()} – {feat_df['last_price'].max()} €/m²")
    print(f"  Rango yoy último: {feat_df['last_yoy_pct'].min()} – {feat_df['last_yoy_pct'].max()} %")
    print(f"  Rango CAGR medio: {feat_df['avg_cagr_5y'].min()} – {feat_df['avg_cagr_5y'].max()} %")

    # ── Tabla resumen ─────────────────────────────────────────────────────────
    print("\nResumen por distrito (ordenado por precio último trimestre):")
    print(feat_df[["district_name", "last_price", "last_yoy_pct", "avg_cagr_5y", "yoy_accel"]].to_string(index=False))

    # ── Exportar ──────────────────────────────────────────────────────────────
    feat_df.to_csv(OUT_PATH, index=False)
    print(f"\nExportado: {OUT_PATH}")


if __name__ == "__main__":
    main()

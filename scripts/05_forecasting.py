"""
05_forecasting.py
Forecasting del precio €/m² de vivienda nueva en Sevilla (municipio).
Modelos: SARIMA (statsmodels) + Prophet, con evaluación vs baseline.
Serie: mivau_sevilla_series.csv (2005Q1–2025Q4, trimestral).

Ejecutar desde la raíz del proyecto:
    python scripts/05_forecasting.py
"""

import warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
SERIES    = ROOT / "data" / "processed" / "mivau_sevilla_series.csv"
OUT_HTML  = ROOT / "resultados" / "forecast_sevilla.html"
OUT_CSV   = ROOT / "resultados" / "forecast_valores.csv"
OUT_HTML.parent.mkdir(parents=True, exist_ok=True)

# ── Parámetros ────────────────────────────────────────────────────────────────
TRAIN_END        = "2023Q4"   # fin del periodo de entrenamiento
HORIZON          = 6          # trimestres a predecir tras el último dato real
SARIMA_ORDER     = (1, 1, 1)
SARIMA_SEASONAL  = (1, 1, 1, 4)  # estacionalidad trimestral (s=4)


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return round(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100, 2)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return round(np.mean(np.abs(y_true - y_pred)), 1)


def load_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.PeriodIndex(df["period"], freq="Q").to_timestamp()
    df = df.sort_values("date").reset_index(drop=True)
    df = df[["date", "period", "price_nueva_eur_m2"]].dropna()
    return df


def split_train_test(df: pd.DataFrame, train_end: str):
    train_end_ts = pd.Period(train_end, freq="Q").to_timestamp()
    train = df[df["date"] <= train_end_ts].copy()
    test  = df[df["date"] >  train_end_ts].copy()
    return train, test


# ── Baselines ─────────────────────────────────────────────────────────────────
def baseline_naive(train: pd.Series, n: int) -> np.ndarray:
    return np.full(n, train.iloc[-1])


def baseline_seasonal(train: pd.Series, n: int, s: int = 4) -> np.ndarray:
    preds = []
    for i in range(n):
        preds.append(train.iloc[-(s - (i % s))])
    return np.array(preds)


# ── SARIMA ────────────────────────────────────────────────────────────────────
def fit_sarima(train: pd.Series, order, seasonal_order):
    model = SARIMAX(train, order=order, seasonal_order=seasonal_order,
                    enforce_stationarity=False, enforce_invertibility=False)
    return model.fit(disp=False)


# ── Prophet ───────────────────────────────────────────────────────────────────
def fit_prophet(df: pd.DataFrame):
    prophet_df = df.rename(columns={"date": "ds", "price_nueva_eur_m2": "y"})
    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        interval_width=0.80,
        changepoint_prior_scale=0.05,
    )
    m.fit(prophet_df)
    return m


def forecast_prophet(model, last_date, n_total: int):
    future_dates = pd.date_range(last_date, periods=n_total + 1, freq="QS")[1:]
    future_df = pd.DataFrame({"ds": future_dates})
    fc = model.predict(future_df)
    return (fc["yhat"].values,
            fc["yhat_lower"].values,
            fc["yhat_upper"].values,
            future_dates)


def main():
    # ── Carga y split ─────────────────────────────────────────────────────────
    df = load_series(SERIES)
    print(f"Serie cargada: {len(df)} trimestres ({df['period'].iloc[0]} – {df['period'].iloc[-1]})")

    train, test = split_train_test(df, TRAIN_END)
    n_test = len(test)
    print(f"Train: {len(train)} obs (hasta {TRAIN_END}) | Test: {n_test} obs | Horizonte futuro: {HORIZON}Q\n")

    y_test = test["price_nueva_eur_m2"].values

    # ── Baselines ─────────────────────────────────────────────────────────────
    naive_pred    = baseline_naive(train["price_nueva_eur_m2"], n_test)
    seasonal_pred = baseline_seasonal(train["price_nueva_eur_m2"], n_test)

    print("── Baselines ──────────────────────────────────────────")
    print(f"  Naive last:      MAPE={mape(y_test, naive_pred)}%  MAE={mae(y_test, naive_pred)} €/m²")
    print(f"  Seasonal naive:  MAPE={mape(y_test, seasonal_pred)}%  MAE={mae(y_test, seasonal_pred)} €/m²")

    # ── SARIMA (evaluación en test) ───────────────────────────────────────────
    print("\n── SARIMA ─────────────────────────────────────────────")
    sarima_fit = fit_sarima(train["price_nueva_eur_m2"], SARIMA_ORDER, SARIMA_SEASONAL)
    fc_test = sarima_fit.get_forecast(steps=n_test)
    sarima_test_pred = fc_test.predicted_mean.values
    print(f"  SARIMA{SARIMA_ORDER}x{SARIMA_SEASONAL}: MAPE={mape(y_test, sarima_test_pred)}%  MAE={mae(y_test, sarima_test_pred)} €/m²")

    # Reentrenar en serie completa → forecast futuro
    sarima_full = fit_sarima(df["price_nueva_eur_m2"], SARIMA_ORDER, SARIMA_SEASONAL)
    fc_future = sarima_full.get_forecast(steps=HORIZON)
    sarima_future_mean = fc_future.predicted_mean.values
    sarima_future_ci   = fc_future.conf_int(alpha=0.20)
    sarima_future_lo   = sarima_future_ci.iloc[:, 0].values
    sarima_future_hi   = sarima_future_ci.iloc[:, 1].values

    # ── Prophet (evaluación en test) ─────────────────────────────────────────
    print("\n── Prophet ────────────────────────────────────────────")
    prophet_model = fit_prophet(train)
    prophet_test_mean, _, _, _ = forecast_prophet(prophet_model, train["date"].iloc[-1], n_test)
    print(f"  Prophet:         MAPE={mape(y_test, prophet_test_mean)}%  MAE={mae(y_test, prophet_test_mean)} €/m²")

    # Reentrenar Prophet en serie completa → forecast futuro
    prophet_full = fit_prophet(df)
    prophet_future_mean, prophet_future_lo, prophet_future_hi, future_dates = \
        forecast_prophet(prophet_full, df["date"].iloc[-1], HORIZON)

    # ── Fechas y periodos futuros ─────────────────────────────────────────────
    future_periods = pd.PeriodIndex(future_dates, freq="Q").strftime("%YQ%q")

    # ── Exportar CSV ──────────────────────────────────────────────────────────
    forecast_df = pd.DataFrame({
        "period":           future_periods,
        "date":             future_dates,
        "sarima_forecast":  sarima_future_mean.round(1),
        "sarima_lo80":      sarima_future_lo.round(1),
        "sarima_hi80":      sarima_future_hi.round(1),
        "prophet_forecast": prophet_future_mean.round(1),
        "prophet_lo80":     prophet_future_lo.round(1),
        "prophet_hi80":     prophet_future_hi.round(1),
    })
    forecast_df.to_csv(OUT_CSV, index=False)
    print(f"\nForecast valores exportado: {OUT_CSV}")
    print(forecast_df[["period", "sarima_forecast", "prophet_forecast"]].to_string(index=False))

    # ── Visualización ─────────────────────────────────────────────────────────
    fig = go.Figure()

    # Serie histórica completa
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["price_nueva_eur_m2"],
        name="Histórico (MIVAU)", mode="lines+markers",
        line=dict(color="#2c3e50", width=2),
        marker=dict(size=4),
    ))

    # Zona test (referencia visual)
    if n_test > 0:
        fig.add_vrect(
            x0=str(test["date"].iloc[0])[:10],
            x1=str(test["date"].iloc[-1])[:10],
            fillcolor="lightgray", opacity=0.2, line_width=0,
            annotation_text="Periodo validación", annotation_position="top left",
        )

    # SARIMA forecast + banda IC 80%
    fig.add_trace(go.Scatter(
        x=future_dates, y=sarima_future_mean,
        name=f"SARIMA{SARIMA_ORDER}×{SARIMA_SEASONAL}", mode="lines+markers",
        line=dict(color="#e74c3c", width=2.5, dash="dash"),
        marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=list(future_dates) + list(future_dates[::-1]),
        y=list(sarima_future_hi) + list(sarima_future_lo[::-1]),
        fill="toself", fillcolor="rgba(231,76,60,0.12)",
        line=dict(color="rgba(255,255,255,0)"),
        name="SARIMA IC 80%",
    ))

    # Prophet forecast + banda IC 80%
    fig.add_trace(go.Scatter(
        x=future_dates, y=prophet_future_mean,
        name="Prophet (multiplicativo)", mode="lines+markers",
        line=dict(color="#2980b9", width=2.5, dash="dot"),
        marker=dict(size=6),
    ))
    fig.add_trace(go.Scatter(
        x=list(future_dates) + list(future_dates[::-1]),
        y=list(prophet_future_hi) + list(prophet_future_lo[::-1]),
        fill="toself", fillcolor="rgba(41,128,185,0.12)",
        line=dict(color="rgba(255,255,255,0)"),
        name="Prophet IC 80%",
    ))

    # Línea de separación histórico/forecast
    last_date_str = str(df["date"].iloc[-1])[:10]
    fig.add_vline(x=last_date_str, line_dash="dot", line_color="gray", opacity=0.6)
    
    fig.update_layout(
        title=dict(
            text=(
                "Forecast precio vivienda nueva — Sevilla (€/m²)<br>"
                "<sup>Fuente histórica: MIVAU. Modelos: SARIMA(1,1,1)×(1,1,1,4) y Prophet | "
                "Horizonte: 6 trimestres | IC 80%</sup>"
            ),
            x=0.5,
        ),
        xaxis_title="Trimestre",
        yaxis_title="€/m²",
        template="plotly_white",
        height=580,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )

    fig.write_html(OUT_HTML)
    print(f"\nGráfico forecast guardado: {OUT_HTML}")
    print("\n✓ Fase forecasting completada.")


if __name__ == "__main__":
    main()

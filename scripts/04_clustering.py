"""
04_clustering.py
Clustering K-Means de los distritos de Sevilla por perfil inmobiliario.
Selección de k por silhouette + interpretabilidad de centroides.
Incluye stability check por co-ocurrencia de pares (robusto a label switching).

Ejecutar desde la raíz del proyecto:
    python scripts/04_clustering.py
"""

import numpy as np
import pandas as pd
import plotly.express as px
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
FEAT_PATH = ROOT / "data" / "processed" / "dataset_distritos_features.csv"
OUT_CSV   = ROOT / "resultados" / "distritos_clusters.csv"
OUT_PCA   = ROOT / "resultados" / "figuras" / "clusters_pca.html"
OUT_BAR   = ROOT / "resultados" / "figuras" / "clusters_precio_yoy.html"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
OUT_PCA.parent.mkdir(parents=True, exist_ok=True)

CLUSTER_FEATURES = [
    "last_price",
    "avg_yoy_pct",
    "yoy_accel",
    "avg_cagr_5y",
    "price_vol",
]

RANDOM_STATE     = 42
N_STABILITY_RUNS = 20


def select_k(X_scaled: np.ndarray, k_range: range) -> dict:
    results = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=20)
        labels = km.fit_predict(X_scaled)
        sil = silhouette_score(X_scaled, labels) if k > 1 else np.nan
        results[k] = {"inertia": round(km.inertia_, 2), "silhouette": round(sil, 3)}
    return results


def stability_check_cooccurrence(X_scaled: np.ndarray, k: int,
                                  district_names: list,
                                  n_runs: int = N_STABILITY_RUNS) -> pd.DataFrame:
    """
    Stability check por co-ocurrencia de pares.
    Para cada distrito, calcula con qué % de runs sus compañeros de cluster
    son los mismos. Robusto al label switching (KMeans no fija etiquetas numéricas).
    Un distrito con co-ocurrencia media ≥ 80% se considera estable.
    """
    n = len(district_names)
    cooccurrence = np.zeros((n, n), dtype=int)

    for seed in range(n_runs):
        km = KMeans(n_clusters=k, random_state=seed, n_init=20)
        labels = km.fit_predict(X_scaled)
        for i in range(n):
            for j in range(n):
                if labels[i] == labels[j]:
                    cooccurrence[i, j] += 1

    cooccurrence_pct = cooccurrence / n_runs * 100

    # Para cada distrito: estabilidad media con sus compañeros de cluster
    # (excluyendo la diagonal, que siempre es 100%)
    results = []
    for i, name in enumerate(district_names):
        partners = [j for j in range(n) if j != i]
        # Compañeros "frecuentes": aquellos con co-ocurrencia ≥ 80%
        stable_partners = [district_names[j] for j in partners
                           if cooccurrence_pct[i, j] >= 80]
        mean_cooc = np.mean([cooccurrence_pct[i, j] for j in partners])
        results.append({
            "district_name": name,
            "mean_cooccurrence_pct": round(mean_cooc, 1),
            "stable_partners": ", ".join(stable_partners) if stable_partners else "ninguno (singleton estable)",
        })

    return pd.DataFrame(results)


def label_clusters(centroids_df: pd.DataFrame) -> dict:
    labels = {}
    for idx, row in centroids_df.iterrows():
        price = row["last_price"]
        yoy   = row["avg_yoy_pct"]
        accel = row["yoy_accel"]
        if price >= 3000:
            labels[idx] = "Premium consolidado"
        elif accel >= 10:
            labels[idx] = "Alta tracción emergente"
        elif yoy <= 6:
            labels[idx] = "Mercado estabilizado"
        else:
            labels[idx] = "Dinamismo sostenido"
    return labels


def main():
    df = pd.read_csv(FEAT_PATH)
    print(f"Dataset cargado: {df.shape[0]} distritos × {df.shape[1]} columnas")
    print(f"Features para clustering: {CLUSTER_FEATURES}\n")

    X = df[CLUSTER_FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Selección de k ────────────────────────────────────────────────────────
    print("Evaluación de k (2–5):")
    print(f"{'k':>4} {'Inertia':>10} {'Silhouette':>12}")
    print("-" * 30)
    k_results = select_k(X_scaled, range(2, 6))
    for k, res in k_results.items():
        marker = " ← seleccionado" if k == 4 else ""
        print(f"{k:>4} {res['inertia']:>10} {res['silhouette']:>12}{marker}")

    print(f"\nk seleccionado: 4")
    print("  Justificación: máximo silhouette (0.257); k=5 similar (0.254) pero")
    print("  genera segmentos demasiado pequeños para negocio con n=11;")
    print("  k=2 pierde valor narrativo (0.249).")

    # ── Clustering final ──────────────────────────────────────────────────────
    best_k = 4
    km_final = KMeans(n_clusters=best_k, random_state=RANDOM_STATE, n_init=20)
    df["cluster_id"] = km_final.fit_predict(X_scaled)

    centroids = scaler.inverse_transform(km_final.cluster_centers_)
    centroids_df = pd.DataFrame(centroids, columns=CLUSTER_FEATURES)
    centroids_df.index.name = "cluster_id"

    print("\nCentroides (escala original, inverse_transform aplicado):")
    print(centroids_df.round(1).to_string())

    # ── Etiquetas ─────────────────────────────────────────────────────────────
    cluster_labels = label_clusters(centroids_df)
    df["cluster_label"] = df["cluster_id"].map(cluster_labels)

    print("\nAsignación de clusters:")
    print(df[["district_name", "last_price", "avg_yoy_pct", "yoy_accel",
              "cluster_id", "cluster_label"]].to_string(index=False))

    # ── Stability check por co-ocurrencia ────────────────────────────────────
    print(f"\n── Stability check por co-ocurrencia ({N_STABILITY_RUNS} runs) ──")
    print("  Nota: mide co-ocurrencia de pares, no etiqueta numérica")
    print("  (robusto al label switching inherente de KMeans)\n")
    stab = stability_check_cooccurrence(X_scaled, best_k,
                                        df["district_name"].tolist(),
                                        N_STABILITY_RUNS)
    print(stab[["district_name", "mean_cooccurrence_pct", "stable_partners"]].to_string(index=False))

    # Veredicto singleton
    singleton = stab[stab["district_name"].str.contains("San Pablo", na=False)]
    if not singleton.empty:
        cooc = singleton["mean_cooccurrence_pct"].values[0]
        partners = singleton["stable_partners"].values[0]
        print(f"\nSan Pablo-Santa Justa — co-ocurrencia media con otros: {cooc}%")
        print(f"  Compañeros estables (≥80%): {partners}")
        verdict = "Singleton estable — perfil suficientemente diferenciado" if cooc < 20 \
                  else "Revisar: comparte cluster con otros distritos en muchos runs"
        print(f"  Veredicto: {verdict}")

    # ── Exportar CSV ──────────────────────────────────────────────────────────
    df.to_csv(OUT_CSV, index=False)
    print(f"\nCSV exportado: {OUT_CSV}")

    # ── PCA 2D ────────────────────────────────────────────────────────────────
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    coords = pca.fit_transform(X_scaled)
    df["pca1"] = coords[:, 0]
    df["pca2"] = coords[:, 1]
    var_exp = pca.explained_variance_ratio_
    print(f"\nVarianza explicada PCA: PC1={var_exp[0]:.1%}, PC2={var_exp[1]:.1%}, "
          f"Total={sum(var_exp):.1%}")

    fig_pca = px.scatter(
        df, x="pca1", y="pca2",
        color="cluster_label", text="district_name",
        title="Segmentación de distritos de Sevilla — PCA (2D)",
        labels={
            "pca1": f"PC1 ({var_exp[0]:.1%} varianza)",
            "pca2": f"PC2 ({var_exp[1]:.1%} varianza)",
            "cluster_label": "Perfil",
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
        template="plotly_white", height=550,
    )
    fig_pca.update_traces(textposition="top center", marker=dict(size=12))
    fig_pca.write_html(OUT_PCA)
    print(f"Gráfico PCA guardado: {OUT_PCA}")

    # ── Precio vs YoY ─────────────────────────────────────────────────────────
    fig_bar = px.scatter(
        df, x="avg_yoy_pct", y="last_price",
        color="cluster_label", text="district_name", size="avg_cagr_5y",
        title="Distritos de Sevilla: precio actual vs crecimiento medio 2025",
        labels={
            "avg_yoy_pct": "Variación interanual media 2025 (%)",
            "last_price":  "Precio último trimestre (€/m²)",
            "cluster_label": "Perfil",
            "avg_cagr_5y": "CAGR 5 años (%)",
        },
        color_discrete_sequence=px.colors.qualitative.Set2,
        template="plotly_white", height=580,
    )
    fig_bar.update_traces(textposition="top center")
    fig_bar.add_hline(y=df["last_price"].median(), line_dash="dot",
                      line_color="gray", annotation_text="Precio mediano")
    fig_bar.add_vline(x=df["avg_yoy_pct"].median(), line_dash="dot",
                      line_color="gray", annotation_text="YoY mediano")
    fig_bar.write_html(OUT_BAR)
    print(f"Gráfico precio/YoY guardado: {OUT_BAR}")

    # ── Resumen por cluster ───────────────────────────────────────────────────
    print("\nResumen por cluster:")
    summary = df.groupby("cluster_label").agg(
        distritos=("district_name", lambda x: ", ".join(x)),
        precio_medio=("last_price", "mean"),
        yoy_medio=("avg_yoy_pct", "mean"),
        cagr_medio=("avg_cagr_5y", "mean"),
    ).round(1)
    print(summary.to_string())


if __name__ == "__main__":
    main()

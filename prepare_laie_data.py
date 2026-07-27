#!/usr/bin/env python3
"""
prepare_laie_data.py
Convierte el export SAP de ventas de Laie en la estructura que espera RD-Agent
(data_science, modo local) para la previsión SEMANAL por tienda.

Formato de entrada (export real): separador '#', encoding latin-1, columnas
  centro, nombre, fecha, target, budget, semana_en_anyo, ..., es_semana_santa
Venta = 'target'. Se filtran WEB/almacenes/paradas/eventos y tiendas sin ventas.

Genera (bajo --out, por defecto git_ignore_folder/ds_data):
  laie-sales-forecast/train/train.csv                (histórico con sales)
  laie-sales-forecast/test/test.csv                  (holdout ago-dic 2025, sin sales)
  laie-sales-forecast/sample_submission.csv
  laie-sales-forecast/forecast/test_2026.csv         (ago-dic 2026, previsión real)
  eval/laie-sales-forecast/submission_test.csv       (verdad del holdout)
  sample/laie-sales-forecast/...                     (subconjunto para debug)

Uso:
  python prepare_laie_data.py --sales export.csv
  python prepare_laie_data.py --sales export.csv --include-web
"""
import argparse
import re
from pathlib import Path

import pandas as pd

COMPETITION = "laie-sales-forecast"


def slug(s: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", str(s).upper()).strip("_")


def monday_of(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s, errors="coerce")
    return d - pd.to_timedelta(d.dt.weekday, unit="D")


def is_excluded(centro: str, nombre: str) -> bool:
    """True si el punto de venta NO es una tienda física permanente."""
    n = str(nombre).upper()
    c = str(centro).upper().strip()
    if n.startswith("WEB"):
        return True  # canal online
    if "ALMACEN" in n or "ALMAC" in n:
        return True  # almacén
    if "PARADA" in n or c.startswith("P"):
        return True  # parada
    if c.startswith("E"):
        return True  # evento/exposición (E001..)
    return False


def load_laie(path: Path, sep: str, enc: str, include_web: bool, include_all: bool,
              min_total: float) -> pd.DataFrame:
    df = pd.read_csv(path, sep=sep, encoding=enc, quotechar='"')
    df.columns = [c.strip().strip('"') for c in df.columns]

    df["centro"] = df["centro"].astype(str).str.strip().replace({"nan": "", "None": ""})
    df["nombre"] = df["nombre"].astype(str).str.strip()
    df["date"] = monday_of(df["fecha"].astype(str).str.strip('"'))
    df["sales_day"] = pd.to_numeric(df["target"], errors="coerce").fillna(0.0)
    # store_id: centro si existe, si no un slug del nombre (p.ej. Café sin centro)
    df["store_id"] = df.apply(lambda r: r["centro"] if r["centro"] else slug(r["nombre"]), axis=1)

    # Semana Santa (flag semanal) si viene la columna
    if "es_semana_santa" in df.columns:
        df["ss_day"] = df["es_semana_santa"].astype(str).str.strip().str.lower().isin(["si", "sí", "1", "true"]).astype(int)
    else:
        df["ss_day"] = 0

    # Filtro de tiendas
    if not include_all:
        keep = ~df.apply(lambda r: is_excluded(r["centro"], r["nombre"]), axis=1)
        if not include_web:
            pass  # is_excluded ya quita WEB
        df = df[keep]

    # Agregación semanal
    weekly = df.groupby(["store_id", "date"], as_index=False).agg(
        sales=("sales_day", "sum"),
        semana_santa=("ss_day", "max"),
    )

    # Rellenar semanas ausentes con 0, pero empezando cada tienda en su PRIMERA
    # semana con venta real (evita ceros iniciales de antes de la apertura, que
    # confunden al agente haciéndole creer que es una tienda "nueva sin histórico").
    global_max = weekly["date"].max()
    filled = []
    for sid, g in weekly.groupby("store_id"):
        g = g.sort_values("date")
        nz = g[g["sales"] > 0]
        if nz.empty:
            continue  # sin ventas reales; se descartará por min_total igualmente
        start = nz["date"].min()
        g = g[g["date"] >= start]
        idx = pd.date_range(start, global_max, freq="W-MON")
        gg = g.set_index("date").reindex(idx)
        gg["store_id"] = sid
        gg["sales"] = gg["sales"].fillna(0.0)
        gg["semana_santa"] = gg["semana_santa"].fillna(0).astype(int)
        gg.index.name = "date"
        filled.append(gg.reset_index())
    weekly = pd.concat(filled, ignore_index=True)

    weekly["covid"] = weekly["date"].dt.year.isin([2020, 2021]).astype(int)

    # Excluir tiendas con ventas totales casi nulas (aperturas 2026 a 0, etc.)
    totals = weekly.groupby("store_id")["sales"].sum()
    keep_ids = totals[totals > min_total].index
    weekly = weekly[weekly["store_id"].isin(keep_ids)]

    return weekly.sort_values(["store_id", "date"]).reset_index(drop=True)


def make_id(df: pd.DataFrame) -> pd.Series:
    return df["store_id"].astype(str) + "__" + df["date"].dt.strftime("%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sales", required=True)
    ap.add_argument("--out", default="git_ignore_folder/ds_data")
    ap.add_argument("--sep", default="#")
    ap.add_argument("--encoding", default="latin-1")
    ap.add_argument("--holdout-start", default="2025-08-01")
    ap.add_argument("--holdout-end", default="2025-12-31")
    ap.add_argument("--forecast-end", default="2026-12-31")
    ap.add_argument("--min-total-sales", type=float, default=1000.0)
    ap.add_argument("--include-web", action="store_true")
    ap.add_argument("--include-all", action="store_true")
    ap.add_argument("--exclude-covid", action="store_true")
    args = ap.parse_args()

    out = Path(args.out)
    comp = out / COMPETITION
    ev = out / "eval" / COMPETITION
    sp = out / "sample" / COMPETITION
    for d in (comp / "train", comp / "test", comp / "forecast", ev, sp / "train", sp / "test"):
        d.mkdir(parents=True, exist_ok=True)

    weekly = load_laie(Path(args.sales), args.sep, args.encoding,
                       args.include_web, args.include_all, args.min_total_sales)

    hs, he = pd.Timestamp(args.holdout_start), pd.Timestamp(args.holdout_end)
    extra = ["covid", "semana_santa"]

    # TRAIN
    train = weekly[weekly["date"] < hs].copy()
    if args.exclude_covid:
        train = train[train["covid"] == 0]
    train_out = train[["store_id", "date", "sales"] + extra].copy()
    train_out["date"] = train_out["date"].dt.strftime("%Y-%m-%d")

    # TEST holdout
    hold = weekly[(weekly["date"] >= hs) & (weekly["date"] <= he)].copy()
    hold["id"] = make_id(hold)
    test_out = hold[["id", "store_id", "date"] + extra].copy()
    test_out["date"] = test_out["date"].dt.strftime("%Y-%m-%d")
    submission_test = hold[["id", "sales"]].copy()
    sample_submission = hold[["id"]].copy()
    sample_submission["sales"] = 0.0

    # FORECAST real ago-dic 2026 (tiendas activas últimas 8 semanas)
    recent_cut = weekly["date"].max() - pd.Timedelta(weeks=8)
    active = sorted(weekly[weekly["date"] >= recent_cut]["store_id"].unique())
    fc_start = max(weekly["date"].max() + pd.Timedelta(weeks=1), pd.Timestamp("2026-08-01"))
    fweeks = pd.date_range(fc_start, pd.Timestamp(args.forecast_end), freq="W-MON")
    fc = pd.MultiIndex.from_product([active, fweeks], names=["store_id", "date"]).to_frame(index=False)
    fc["covid"] = 0
    fc["semana_santa"] = 0
    fc["id"] = make_id(fc)
    forecast_out = fc[["id", "store_id", "date"] + extra].copy()
    forecast_out["date"] = forecast_out["date"].dt.strftime("%Y-%m-%d")

    # Escribir
    train_out.to_csv(comp / "train" / "train.csv", index=False)
    test_out.to_csv(comp / "test" / "test.csv", index=False)
    sample_submission.to_csv(comp / "sample_submission.csv", index=False)
    submission_test.to_csv(ev / "submission_test.csv", index=False)
    forecast_out.to_csv(comp / "forecast" / "test_2026.csv", index=False)

    # Sample debug (3 tiendas)
    some = sorted(weekly["store_id"].unique())[:3]
    train_out[train_out["store_id"].isin(some)].to_csv(sp / "train" / "train.csv", index=False)
    test_out[test_out["store_id"].isin(some)].to_csv(sp / "test" / "test.csv", index=False)
    sample_submission[sample_submission["id"].str.startswith(tuple(f"{s}__" for s in some))].to_csv(
        sp / "sample_submission.csv", index=False)
    desc = comp / "description.md"
    if desc.exists():
        (sp / "description.md").write_text(desc.read_text(encoding="utf-8"), encoding="utf-8")

    # Resumen
    print("=" * 62)
    print("Preparación Laie completada.")
    print(f"  Tiendas incluidas : {weekly['store_id'].nunique()}")
    print(f"  Rango semanal     : {weekly['date'].min().date()} → {weekly['date'].max().date()}")
    print(f"  TRAIN    : {len(train_out):>6} filas ({'sin COVID' if args.exclude_covid else 'COVID incluido, covid=1'})")
    print(f"  TEST     : {len(test_out):>6} filas  holdout {hs.date()} → {he.date()}")
    print(f"  SUBM_GT  : {len(submission_test):>6} filas")
    print(f"  FORECAST : {len(forecast_out):>6} filas  {fc_start.date()} → {args.forecast_end} ({len(active)} tiendas)")
    if len(test_out) != len(submission_test):
        print("  ⚠️  test y submission_test NO cuadran.")
    if len(test_out) == 0:
        print("  ⚠️  Holdout vacío: ¿hay datos en ago-dic 2025?")
    print("=" * 62)
    print("Tiendas:", ", ".join(sorted(weekly['store_id'].unique())))


if __name__ == "__main__":
    main()

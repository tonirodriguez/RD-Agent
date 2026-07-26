#!/usr/bin/env python3
"""
analyze_fin_quant_results.py
Escanea los workspaces generados por RD-Agent (fin_quant/fin_factor/fin_model),
extrae las métricas de backtest de cada experimento (qlib_res.csv) y las presenta
en una tabla comparativa ordenada por fecha (≈ orden de los loops). Señala el
experimento ganador y la ruta a su código (factor.py / model.py).

Uso:
    python analyze_fin_quant_results.py
    python analyze_fin_quant_results.py --base git_ignore_folder/RD-Agent_workspace
    python analyze_fin_quant_results.py --sort "information_ratio_with_cost"
    python analyze_fin_quant_results.py --csv resumen.csv   # además exporta a CSV
"""
import argparse
from pathlib import Path

import pandas as pd


def find_metric(series: pd.Series, *substrings: str):
    """Devuelve el primer valor cuyo índice contenga TODOS los substrings (case-insensitive)."""
    subs = [s.lower() for s in substrings]
    for idx, val in series.items():
        name = str(idx).lower()
        if all(s in name for s in subs):
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
    return None


def annual_breakdown(ret_pkl_path: Path) -> pd.DataFrame:
    """
    Desglose por año del rendimiento de la cartera a partir de ret.pkl
    (portfolio_analysis/report_normal_1day.pkl de qlib).

    Sirve para detectar dependencia de régimen: si (casi) todo el exceso de
    retorno viene de 2020-2021 (COVID), el factor probablemente no generaliza.
    NOTA: es un desglose basado en RETORNOS (no en IC crudo, que requiere las
    predicciones/labels diarias que el workspace no persiste).
    """
    rep = pd.read_pickle(ret_pkl_path)
    if not isinstance(rep, pd.DataFrame):
        rep = pd.DataFrame(rep)
    rep.index = pd.to_datetime(rep.index)

    ret = rep["return"] if "return" in rep.columns else rep.iloc[:, 0]
    bench = rep["bench"] if "bench" in rep.columns else 0.0
    cost = rep["cost"] if "cost" in rep.columns else 0.0
    excess = ret - cost - bench  # exceso diario sobre benchmark, con coste

    rows = []
    for year, grp in excess.groupby(excess.index.year):
        cum = (1 + grp).cumprod()
        mdd = float((cum / cum.cummax() - 1).min())
        ir = float(grp.mean() / grp.std() * (252 ** 0.5)) if grp.std() > 0 else float("nan")
        rows.append({
            "year": int(year),
            "excess_return": float((1 + grp).prod() - 1),
            "IR": ir,
            "max_dd": mdd,
            "COVID": "◀ COVID" if year in (2020, 2021) else "",
        })
    return pd.DataFrame(rows)


def load_workspace_metrics(res_path: Path) -> dict:
    """Lee un qlib_res.csv y extrae las métricas clave de forma tolerante."""
    try:
        s = pd.read_csv(res_path, index_col=0).iloc[:, 0]
    except Exception as e:  # noqa: BLE001
        return {"workspace": res_path.parent.name, "error": str(e)}

    ws = res_path.parent
    code = "factor.py" if (ws / "factor.py").exists() else (
        "model.py" if (ws / "model.py").exists() else "-"
    )
    return {
        "workspace": ws.name,
        "mtime": pd.Timestamp(res_path.stat().st_mtime, unit="s"),
        "IC": find_metric(s, "ic") if find_metric(s, "rank", "ic") is None else find_metric(s, "\nic"),
        "Rank IC": find_metric(s, "rank ic") or find_metric(s, "rank_ic"),
        "ICIR": find_metric(s, "icir") if find_metric(s, "rank", "icir") is None else None,
        "Rank ICIR": find_metric(s, "rank icir") or find_metric(s, "rank_icir"),
        "AnnRet_cost": find_metric(s, "with_cost", "annualized_return"),
        "IR_cost": find_metric(s, "with_cost", "information_ratio"),
        "MaxDD_cost": find_metric(s, "with_cost", "max_drawdown"),
        "AnnRet_nocost": find_metric(s, "without_cost", "annualized_return"),
        "IR_nocost": find_metric(s, "without_cost", "information_ratio"),
        "code": code,
        "path": str(ws),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="git_ignore_folder/RD-Agent_workspace",
                    help="Carpeta con los workspaces de RD-Agent")
    ap.add_argument("--sort", default="IR_cost",
                    help="Columna por la que ordenar el ganador (por defecto IR_cost)")
    ap.add_argument("--csv", default=None, help="Ruta opcional para exportar la tabla a CSV")
    args = ap.parse_args()

    base = Path(args.base)
    if not base.exists():
        raise SystemExit(f"No existe {base}. Ejecuta desde la raíz del repo o usa --base.")

    res_files = sorted(base.rglob("qlib_res.csv"), key=lambda p: p.stat().st_mtime)
    if not res_files:
        raise SystemExit(f"No se encontró ningún qlib_res.csv bajo {base}.")

    rows = [load_workspace_metrics(p) for p in res_files]
    df = pd.DataFrame(rows)

    # Si no encontró las métricas estándar, muestra los índices crudos del primero para depurar
    metric_cols = ["Rank IC", "IR_cost", "MaxDD_cost"]
    if df[metric_cols].isna().all().all():
        print("⚠️  No se reconocieron los nombres de métricas estándar.")
        print("    Índices disponibles en el primer qlib_res.csv:")
        sample = pd.read_csv(res_files[0], index_col=0)
        print(sample.to_string())
        print("\n    Ajusta las cadenas de find_metric() a esos nombres.\n")

    cols = ["workspace", "mtime", "IC", "Rank IC", "Rank ICIR",
            "AnnRet_cost", "IR_cost", "MaxDD_cost", "code"]
    cols = [c for c in cols if c in df.columns]
    print("\n=== Comparativa de experimentos (orden cronológico ≈ loops) ===\n")
    with pd.option_context("display.max_columns", None, "display.width", 200,
                           "display.float_format", lambda x: f"{x:,.4f}"):
        print(df[cols].to_string(index=False))

    # Ganador
    sort_col = args.sort if args.sort in df.columns else "IR_cost"
    valid = df.dropna(subset=[sort_col]) if sort_col in df.columns else df
    if not valid.empty and sort_col in valid.columns:
        winner = valid.sort_values(sort_col, ascending=False).iloc[0]
        print("\n=== 🏆 Experimento ganador (por %s) ===" % sort_col)
        print(f"  workspace : {winner['workspace']}")
        print(f"  {sort_col}: {winner.get(sort_col)}")
        print(f"  Rank IC   : {winner.get('Rank IC')}")
        print(f"  código    : {winner.get('code')}")
        print(f"  ruta      : {winner.get('path')}")
        print(f"\n  Ver el código:  cat '{winner.get('path')}/{winner.get('code')}'")

        # Desglose por año del ganador (detección de dependencia COVID)
        ret_pkl = Path(winner.get("path")) / "ret.pkl"
        if ret_pkl.exists():
            try:
                yb = annual_breakdown(ret_pkl)
                print("\n=== 📅 Rendimiento por año del ganador (exceso s/ benchmark, con coste) ===")
                with pd.option_context("display.float_format", lambda x: f"{x:,.4f}"):
                    print(yb.to_string(index=False))
                covid = yb[yb["year"].isin([2020, 2021])]["excess_return"].sum()
                total = yb["excess_return"].sum()
                if total != 0:
                    print(f"\n  Exceso acumulado en 2020-2021 (COVID): {covid:,.4f} "
                          f"de {total:,.4f} total ({100*covid/total:,.1f}%).")
                    print("  Si ese % es muy alto, el edge depende del COVID → valida con un run excluyendo 2020.")
            except Exception as e:  # noqa: BLE001
                print(f"\n  (No se pudo calcular el desglose anual: {e})")
        else:
            print("\n  (Sin ret.pkl en el workspace ganador; no hay desglose anual.)")

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nTabla exportada a {args.csv}")


if __name__ == "__main__":
    main()

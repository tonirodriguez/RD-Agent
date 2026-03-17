import numpy as np
import pandas as pd
import qlib
from qlib.constant import REG_US, REG_CN
from qlib.data import D

# =========================
# CONFIGURACIÓN
# =========================
REGION = "US"  # cambia a "CN" si quieres probar cn_data
PROVIDER_URI = "~/.qlib/qlib_data/us_data" if REGION == "US" else "~/.qlib/qlib_data/cn_data"

MARKET = "nasdaq100" if REGION == "US" else "csi300"  # para CN suele funcionar 'csi300'
START = "2026-01-01"
END   = "2026-03-14"

TOP_K = 10               # número de acciones en cartera
LOOKBACK = 20            # momentum 20 días
REBAL_FREQ = "ME"        # mensual

# =========================
# INIT QLIB
# =========================
qlib.init(provider_uri=PROVIDER_URI, region=REG_US if REGION == "US" else REG_CN)

# =========================
# UNIVERSO
# =========================
pool_cfg = D.instruments(MARKET)
tickers = D.list_instruments(pool_cfg, start_time=START, end_time=END, as_list=True)

if len(tickers) == 0:
    raise RuntimeError(f"No hay instrumentos para MARKET='{MARKET}'. Revisa instruments/ o usa otro market.")

# para hacerlo rápido, limita universo (opcional)
tickers = tickers[:200]

# =========================
# DATOS (Close)
# =========================
close = D.features(tickers, fields=["$close"], freq="day", start_time=START, end_time=END)
print("close shape:", close.shape)
print("close date min/max:", close.index.min(), close.index.max() if not close.empty else None)

close = close["$close"].unstack(level=0).sort_index()   # filas=fecha, cols=ticker

print("close shape:", close.shape)
print("close date min/max:", close.index.min(), close.index.max() if not close.empty else None)

# elimina columnas con demasiados NaN
close = close.dropna(axis=1, thresh=int(0.9 * len(close)))

# =========================
# SEÑAL: momentum 20d
# =========================
mom = close.pct_change(LOOKBACK)

# =========================
# REBALANCEO mensual: elegimos top-K por momentum
# =========================
rebalance_dates = mom.resample(REBAL_FREQ).last().index
rebalance_dates = rebalance_dates.intersection(mom.index)

positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)

for dt in rebalance_dates:
    scores = mom.loc[dt].dropna()
    if len(scores) < TOP_K:
        continue
    top = scores.nlargest(TOP_K).index
    w = 1.0 / TOP_K
    positions.loc[dt:, top] = w
    # ponemos 0 a los no-top desde esa fecha en adelante (re-asignación)
    positions.loc[dt:, positions.columns.difference(top)] = 0.0

# =========================
# PERFORMANCE (retornos diarios)
# =========================
rets = close.pct_change().fillna(0.0)
port_ret = (positions.shift(1) * rets).sum(axis=1)

# equity curve
equity = (1 + port_ret).cumprod()


print("close shape:", close.shape)
print("close date min/max:", close.index.min(), close.index.max() if not close.empty else None)
print("positions shape:", positions.shape)
print("port_ret len:", len(port_ret), "NaNs:", port_ret.isna().sum())
print("equity len:", len(equity))

if equity.empty:
    raise RuntimeError(
        "equity está vacío. Revisa: "
        "1) provider_uri/region/market, 2) START/END, 3) universe/tickers, 4) filtros dropna."
    )

# métricas básicas
def max_drawdown(eq):
    peak = eq.cummax()
    dd = eq / peak - 1.0
    return dd.min()

ann_factor = 252
ann_ret = equity.iloc[-1] ** (ann_factor / len(equity)) - 1
ann_vol = port_ret.std() * np.sqrt(ann_factor)
sharpe = (port_ret.mean() * ann_factor) / (port_ret.std() * np.sqrt(ann_factor) + 1e-12)
mdd = max_drawdown(equity)

print("==== Qlib Simple Momentum Experiment ====")
print(f"REGION: {REGION} | PROVIDER_URI: {PROVIDER_URI}")
print(f"MARKET: {MARKET} | Universe size: {close.shape[1]}")
print(f"Period: {START} to {END}")
print(f"TOP_K: {TOP_K} | LOOKBACK: {LOOKBACK}d | Rebalance: {REBAL_FREQ}")
print("----------------------------------------")
print(f"Annualized Return (approx): {ann_ret:.2%}")
print(f"Annualized Vol (approx):    {ann_vol:.2%}")
print(f"Sharpe (approx):            {sharpe:.2f}")
print(f"Max Drawdown:               {mdd:.2%}")
print("----------------------------------------")
print("Equity last value:", equity.iloc[-1])

# guarda salida
out = pd.DataFrame({"port_ret": port_ret, "equity": equity})
out.to_csv("qlib_momentum_results.csv", index=True)
print("Saved: qlib_momentum_results.csv")
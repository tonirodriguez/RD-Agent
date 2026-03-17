import qlib
from qlib.constant import REG_US, REG_CN
from qlib.data import D
import pandas as pd

REGION = "US"                      # "US" o "CN"
PROVIDER_URI = "~/.qlib/qlib_data/us_data" if REGION == "US" else "~/.qlib/qlib_data/cn_data"
MARKET = "sp500" if REGION == "US" else "csi300"   # ajusta si no existe
START = "2020-01-01"
END   = "2026-12-31"

print("=== CONFIG ===")
print("REGION:", REGION)
print("PROVIDER_URI:", PROVIDER_URI)
print("MARKET:", MARKET)
print("START-END:", START, END)

qlib.init(provider_uri=PROVIDER_URI, region=REG_US if REGION == "US" else REG_CN)

# 1) Resolver universo
pool_cfg = D.instruments(MARKET)   # market puede ser nombre o lista; Qlib lo soporta así
print("\nD.instruments(MARKET) =>", pool_cfg)

tickers = D.list_instruments(pool_cfg, start_time=START, end_time=END, as_list=True)
print("tickers count:", len(tickers))
print("tickers sample:", tickers[:10])

if len(tickers) == 0:
    raise RuntimeError(
        f"No hay instrumentos para MARKET='{MARKET}' en {START}..{END}. "
        "Solución: usa otro MARKET o revisa la carpeta instruments/ del dataset."
    )

# 2) Cargar features
df = D.features(tickers[:5], fields=["$close", "$open", "$volume"], freq="day", start_time=START, end_time=END)
print("\nfeatures df shape:", df.shape)
print(df.head())

if df.empty:
    raise RuntimeError(
        "D.features devolvió vacío. Revisa START/END (rango), provider_uri, y que el dataset tenga esas series."
    )

# 3) Transformar a matriz de precios (close)
close = df["$close"].unstack(level=0).sort_index()
print("\nclose matrix shape:", close.shape)
print("close min/max date:", close.index.min(), close.index.max())
print(close.head())
import numpy as np
import pandas as pd
import qlib
from qlib.constant import REG_US, REG_CN
from qlib.data import D

# =======================================================
# ANÁLISIS QLIB: ESTRATEGIA MOMENTUM + VOLUMEN
# =======================================================

REGION = "US" 
PROVIDER_URI = "~/.qlib/qlib_data/us_data"
MARKET = "nasdaq100" 

# El rango de evaluación. Ponemos una fecha final alta para tomar siempre "hoy" (el último registro real)
START = "2026-01-01"
END   = "2026-03-19" 

TOP_K = 5
MOM_LOOKBACK = 20    # Días para mirar el retorno
VOL_SHORT = 5        # Media móvil del volumen a 5 días
VOL_LONG = 20        # Media móvil del volumen a 20 días
REBAL_FREQ = "W-FRI" # Rebalanceo todos los viernes (Weekly)

# 1) INICIALIZACIÓN
try:
    qlib.init(provider_uri=PROVIDER_URI, region=REG_US if REGION == "US" else REG_CN)
except Exception as e:
    print(f"Error inicializando: {e}")

# 2) UNIVERSO Y DATOS
pool_cfg = D.instruments(MARKET)
tickers = D.list_instruments(pool_cfg, start_time=START, end_time=END, as_list=True)

if len(tickers) == 0:
    raise RuntimeError(f"¡Ojo! El dataset local en {PROVIDER_URI} está vacío para {MARKET} en las fechas puestas.")

# Sacamos precios de Cierre y Volumen
df = D.features(tickers, fields=["$close", "$volume"], freq="day", start_time=START, end_time=END)
close = df["$close"].unstack(level=0).sort_index()
volume = df["$volume"].unstack(level=0).sort_index()

# Limpiamos acciones con muchos días nulos (IPO reciente, sin datos, etc)
close = close.dropna(axis=1, thresh=int(0.5 * len(close)))
volume = volume[close.columns]

# =======================================================
# 3) LÓGICA DE LAS SEÑALES
# =======================================================
# Señal 1: Momentum (Rendimiento (%) en los últimos 20 días)
mom = close.pct_change(MOM_LOOKBACK)

# Señal 2: Tendencia de Volumen (Average(Volume 5d) / Average(Volume 20d))
# Nos dice si se está negociando más acción que su promedio mensual.
vol_ma_short = volume.rolling(VOL_SHORT).mean()
vol_ma_long = volume.rolling(VOL_LONG).mean()
vol_trend = vol_ma_short / (vol_ma_long + 1e-8)  # El epsilon +1e-8 evita división por 0

# Fechas de Rebalanceo (Cada viernes que exista en los datos)
rebalance_dates = mom.resample(REBAL_FREQ).last().index
rebalance_dates = rebalance_dates.intersection(mom.index)

positions = pd.DataFrame(0.0, index=close.index, columns=close.columns)
historical_picks = {}

# =======================================================
# 4) SIMULACIÓN DEL COMPORTAMIENTO
# =======================================================
for dt in rebalance_dates:
    m = mom.loc[dt]
    v = vol_trend.loc[dt]
    
    # REGLAS DE DECISIÓN CLAVES:
    # 1. El momentum debe ser estrictamente positivo (m > 0)
    # 2. El volumen a corto plazo debe ser mayor al de largo plazo (v > 1.0)
    valid_mask = (m > 0) & (v > 1.0)
    valid_tickers = valid_mask[valid_mask].index
    
    if len(valid_tickers) == 0:
        # Nada cumple los requisitos, nos quedamos 100% en Cash (pesos = 0)
        historical_picks[dt] = []
        continue
        
    # De los válidos, ordenamos por la Fuerza del Momentum de mayor a menor
    scores = m.loc[valid_tickers]
    top = scores.nlargest(TOP_K).index
    
    # Invertimos equitativamente en el Top-K
    w = 1.0 / len(top)
    positions.loc[dt:, top] = w
    
    # Vendemos lo que no esté en el TOP-K desde hoy en adelante
    positions.loc[dt:, positions.columns.difference(top)] = 0.0
    
    # Guardamos registro para saber en qué invertíamos
    historical_picks[dt] = list(top)

# Cálculo de retornos histórico para mostrar la rentabilidad simulada
rets = close.pct_change().fillna(0.0)
port_ret = (positions.shift(1) * rets).sum(axis=1) # Usamos posiciones del día anterior
equity = (1 + port_ret).cumprod()

# =======================================================
# 5) IMPRESIÓN DEL ANÁLISIS
# =======================================================
print("===================================================================")
print("     ANÁLISIS QLIB: ESTRATEGIA COMBINADA (MOMENTUM + VOLUMEN)")
print("===================================================================")
print(f"Mercado: {MARKET.upper()} | Período Simulado: {START} a {END}")
print(f"Activos analizados: {len(tickers)} | Frecuencia de Decisión: Semanal")
print("-" * 67)

ann_factor = 252
ann_ret = equity.iloc[-1] ** (ann_factor / max(1, len(equity))) - 1
ann_vol = port_ret.std() * np.sqrt(ann_factor)
sharpe = (port_ret.mean() * ann_factor) / (port_ret.std() * np.sqrt(ann_factor) + 1e-12)

print(f"Retorno Anualizado (CAGR) : {ann_ret:.2%}")
print(f"Volatilidad Anualizada    : {ann_vol:.2%}")
print(f"Ratio de Sharpe           : {sharpe:.2f}")
print("-" * 67)

# =======================================================
# 6) HOJA DE RUTA ACTUAL (EL PRESENTE)
# =======================================================
if equity.empty:
    print("No hay datos suficientes para tomar la decisión actual.")
else:
    last_available_data_date = equity.index[-1]
    last_decision_date = rebalance_dates[-1]
    current_portfolio = historical_picks.get(last_decision_date, [])

    print(f"\n>>>> DECISIÓN DE INVERSIÓN VIGENTE <<<<")
    print(f"Dato más moderno disponible en tu base de datos: {last_available_data_date.date()}")
    print(f"Última fecha donde la estrategia escaneó:        {last_decision_date.date()}\n")

    if len(current_portfolio) == 0:
        print("ESTADO DEL PORTAFOLIO : 🔴 ¡MANTENERSE EN EFECTIVO (CASH)!")
        print("Motivo                : Ninguna acción cumple simultáneamente los requisitos:")
        print("                        - Retorno Positivo en los últimos 20 días.")
        print("                        - Volumen de la última semana superior al promedio mensual.")
    else:
        print(f"ESTADO DEL PORTAFOLIO : 🟢 COMPRAR / INVERTIR EQUITATIVAMENTE ({(100.0/len(current_portfolio)):.1f}% cada una)")
        print("\nTOP ACCIONES SELECCIONADAS:")
        for ticker in current_portfolio:
            t_mom = mom.loc[last_decision_date, ticker]
            t_vol_trend = vol_trend.loc[last_decision_date, ticker]
            print(f" ✔ {ticker:7s} | Momentum (20d): {t_mom:>6.2%} | Tendencia de Compra (Volumen): {t_vol_trend:>4.2f}x ({(t_vol_trend-1):.0%} más que la media)")

print("===================================================================")

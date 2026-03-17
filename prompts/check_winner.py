import qlib
from qlib.constant import REG_US
from qlib.workflow import R

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region=REG_US)

# Obtenemos automáticamente las predicciones del último experimento corrido por qrun
# qrun guarda sus ejecuciones bajo el experimento "workflow" por defecto.
recorder = R.get_recorder(experiment_name="workflow")

pred_df = recorder.load_object("pred.pkl")
tech_giants = ["AAPL", "MSFT", "META", "GOOGL", "TSLA"]

# Quedarnos con el final de la tabla para las 3 y ordenarlo
tech_preds = pred_df.loc[(slice(None), tech_giants), :]
latest_date = tech_preds.index.get_level_values('datetime').max()

print(f"\n--- SCORE DE INVERSIÓN PARA {latest_date.date()} ---")
print(tech_preds.loc[latest_date].sort_values(by="score", ascending=False))

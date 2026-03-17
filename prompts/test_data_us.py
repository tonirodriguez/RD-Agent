import qlib
from qlib.constant import REG_US
from qlib.data import D

qlib.init(provider_uri="~/.qlib/qlib_data/us_data", region=REG_US)
pool = D.instruments("sp500")    # prueba con sp500 o nasdaq100; evitas “all” si falla

tickers = D.list_instruments(pool, as_list=True)
t = tickers[0]
df = D.features([t], ["$close"], freq="day")
dates = df.index.get_level_values(1)
print("range:", dates.min(), "->", dates.max(), "rows:", len(df))
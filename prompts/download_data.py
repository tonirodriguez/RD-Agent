import yfinance as yf
import pandas as pd
from pathlib import Path

tickers = ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NVDA", "TSLA"]

out_dir = Path("data/ohlcv")
out_dir.mkdir(parents=True, exist_ok=True)

for t in tickers:
    df = yf.download(t, start="2016-01-01", auto_adjust=False)
    df = df.reset_index()
    df = df.rename(columns={
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df.to_csv(out_dir / f"{t}.csv", index=False)

print("✅ Datos descargados")
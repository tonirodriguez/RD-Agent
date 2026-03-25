from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def read_calendar(data_dir: Path) -> list[pd.Timestamp]:
    calendar_path = data_dir / "calendars" / "day.txt"
    return sorted(pd.to_datetime(pd.read_csv(calendar_path, header=None).iloc[:, 0]).tolist())


def read_instruments(data_dir: Path) -> pd.DataFrame:
    instruments_path = data_dir / "instruments" / "all.txt"
    df = pd.read_csv(instruments_path, sep="\t", names=["symbol", "start_datetime", "end_datetime"])
    df["end_datetime"] = pd.to_datetime(df["end_datetime"], errors="coerce")
    return df


def load_last_bin_date(data_dir: Path, symbol: str, calendars: list[pd.Timestamp]) -> pd.Timestamp | None:
    feature_dir = data_dir / "features" / symbol.lower()
    for field in ("close", "factor", "open", "high", "low", "volume"):
        bin_path = feature_dir / f"{field}.day.bin"
        if not bin_path.exists():
            continue
        arr = np.fromfile(bin_path, dtype="<f")
        if len(arr) <= 1:
            continue
        start_idx = int(arr[0])
        values = arr[1:]
        valid_idx = np.flatnonzero(~np.isnan(values))
        if len(valid_idx) == 0:
            continue
        pos = start_idx + int(valid_idx[-1])
        if 0 <= pos < len(calendars):
            return calendars[pos]
    return None


def load_last_csv_date(csv_path: Path) -> pd.Timestamp | None:
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path, usecols=["date"])
    if df.empty:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    return dates.max() if not dates.empty else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=str(Path.home() / ".qlib" / "qlib_data" / "us_data"))
    parser.add_argument("--qlib-repo", default="/mnt/c/Users/trodriguez/src/qlib")
    parser.add_argument("--symbols", nargs="+", default=["A", "AA", "AAPL", "MSFT", "SPY"])
    args = parser.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    qlib_repo = Path(args.qlib_repo).expanduser().resolve()
    source_dir = qlib_repo / "scripts" / "data_collector" / "yahoo" / "source"
    normalize_dir = qlib_repo / "scripts" / "data_collector" / "yahoo" / "normalize"

    calendars = read_calendar(data_dir)
    instruments = read_instruments(data_dir).set_index("symbol")

    print("=== DATASET ===")
    print(f"data_dir: {data_dir}")
    print(f"calendar_last: {calendars[-1].date() if calendars else 'N/A'}")
    print(f"instruments_rows: {len(instruments)}")
    print()
    print("=== SYMBOLS ===")

    stale = False
    for symbol in args.symbols:
        source_last = load_last_csv_date(source_dir / f"{symbol}.csv")
        normalize_last = load_last_csv_date(normalize_dir / f"{symbol}.csv")
        instrument_last = instruments.loc[symbol, "end_datetime"] if symbol in instruments.index else None
        bin_last = load_last_bin_date(data_dir, symbol, calendars)
        status = "OK"
        expected_last = max([d for d in [source_last, normalize_last, instrument_last, bin_last] if d is not None], default=None)
        values = [source_last, normalize_last, instrument_last, bin_last]
        if expected_last is not None and any(v is None or v < expected_last for v in values):
            status = "STALE"
            stale = True
        print(
            f"{symbol:6} status={status:5} "
            f"source={source_last.date() if source_last is not None else 'N/A'} "
            f"normalize={normalize_last.date() if normalize_last is not None else 'N/A'} "
            f"instrument={instrument_last.date() if instrument_last is not None else 'N/A'} "
            f"bin={bin_last.date() if bin_last is not None else 'N/A'}"
        )

    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

import sys
import os
import types
import pandas as pd
from pathlib import Path
import fire

# Añadir el repositorio de Qlib al path para importar el recolector
QLIB_REPO = os.environ.get("QLIB_REPO", "/mnt/c/Users/trodriguez/src/qlib")
sys.path.append(os.path.join(QLIB_REPO, "scripts", "data_collector", "yahoo"))

import collector
from collector import Run, YahooCollectorUS1d


def _install_fake_useragent_fallback():
    if "fake_useragent" in sys.modules:
        return

    fake_useragent = types.ModuleType("fake_useragent")

    class UserAgent:  # pragma: no cover - compatibility shim
        @property
        def random(self):
            return (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )

    fake_useragent.UserAgent = UserAgent
    sys.modules["fake_useragent"] = fake_useragent


def _parse_mixed_dates(values):
    parsed = pd.to_datetime(values, format="mixed", utc=True, errors="coerce")
    if isinstance(parsed, pd.Series):
        return parsed.dt.tz_convert(None)
    return parsed.tz_convert(None)


def _patch_yahoo_normalize():
    original_normalize_yahoo = collector.YahooNormalize.normalize_yahoo

    def normalize_yahoo(
        df: pd.DataFrame,
        calendar_list: list = None,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
        last_close: float = None,
    ):
        df = df.copy()
        if not df.empty and date_field_name in df.columns:
            df[date_field_name] = _parse_mixed_dates(df[date_field_name])
        return original_normalize_yahoo(df, calendar_list, date_field_name, symbol_field_name, last_close)

    collector.YahooNormalize.normalize_yahoo = staticmethod(normalize_yahoo)


def _patch_mixed_date_parsing():
    original_executor = collector.Normalize._executor

    def _executor(self, file_path):
        try:
            return original_executor(self, file_path)
        except ValueError as exc:
            if "unconverted data remains when parsing with format" not in str(exc):
                raise

        file_path = Path(file_path)

        # Preserve qlib's CSV parsing behavior while allowing mixed Yahoo date formats.
        default_na = pd._libs.parsers.STR_NA_VALUES.copy()  # pylint: disable=I1101
        symbol_na = default_na.copy()
        symbol_na.remove("NA")
        columns = pd.read_csv(file_path, nrows=0).columns
        df = pd.read_csv(
            file_path,
            dtype={self._symbol_field_name: str},
            keep_default_na=False,
            na_values={col: symbol_na if col == self._symbol_field_name else default_na for col in columns},
        )

        df = self._normalize_obj.normalize(df)
        if df is not None and not df.empty:
            if self._end_date is not None:
                parsed_dates = _parse_mixed_dates(df[self._date_field_name]).dt.normalize()
                end_date = pd.Timestamp(self._end_date).normalize()
                df = df[parsed_dates.notna() & (parsed_dates <= end_date)]
            df.to_csv(self._target_dir.joinpath(file_path.name), index=False)

    collector.Normalize._executor = _executor


_install_fake_useragent_fallback()
_patch_yahoo_normalize()
_patch_mixed_date_parsing()


# Extendemos el recolector de Yahoo para que solo use la lista de Nasdaq 100
class Nasdaq100Collector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de símbolos de Nasdaq 100 exclusivamente...")
        data_dir = os.environ.get("NASDAQ100_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        effective_date = pd.Timestamp(
            os.environ.get("NASDAQ100_EFFECTIVE_DATE", pd.Timestamp.today().strftime("%Y-%m-%d"))
        )
        ins_path = Path(data_dir) / "instruments" / "nasdaq100.txt"
        
        if not ins_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de instrumentos {ins_path}. Necesitas tener el dataset inicial US con Nasdaq 100.")
        
        df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"])
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
        active_mask = df["start_date"].le(effective_date) & df["end_date"].ge(effective_date)
        symbols = df.loc[active_mask, "symbol"].dropna().unique().tolist()
        
        # Opcional: añadir ticker del índice
        symbols.append("^NDX")
        
        # Formato de Qlib
        def _format(s_):
            s_ = s_.replace(".", "-")
            s_ = s_.strip("$")
            s_ = s_.strip("*")
            return s_
            
        res = sorted(set(map(_format, filter(lambda x: len(x) < 8 and not x.endswith("WS"), symbols))))
        print(f"Total de símbolos a descargar: {len(res)}")
        return res

# Inyectamos la clase en el módulo para que 'Run' la encuentre al usar getattr()
collector.Nasdaq100Collector = Nasdaq100Collector

class Nasdaq100Run(Run):
    @property
    def collector_class_name(self):
        return "Nasdaq100Collector"

    def update_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        trading_date: str = None,
        end_date: str = None,
        check_data_length: int = None,
        delay: float = 1,
        exists_skip: bool = False,
    ):
        if self.interval.lower() != "1d":
            collector.logger.warning(f"currently supports 1d data updates: --interval 1d")

        qlib_data_1d_dir = str(Path(qlib_data_1d_dir).expanduser().resolve())
        os.environ["NASDAQ100_INSTRUMENTS_DATA_DIR"] = qlib_data_1d_dir
        if not collector.exists_qlib_data(qlib_data_1d_dir):
            collector.GetData().qlib_data(
                target_dir=qlib_data_1d_dir, interval=self.interval, region=self.region, exists_skip=exists_skip
            )

        if trading_date is None:
            calendar_df = pd.read_csv(Path(qlib_data_1d_dir).joinpath("calendars/day.txt"))
            trading_date = (pd.Timestamp(calendar_df.iloc[-1, 0]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            trading_date = pd.Timestamp(trading_date).strftime("%Y-%m-%d")

        if end_date is None:
            end_date = (pd.Timestamp(trading_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            end_date = pd.Timestamp(end_date).strftime("%Y-%m-%d")
        effective_date = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        os.environ["NASDAQ100_EFFECTIVE_DATE"] = effective_date

        self.download_data(delay=delay, start=trading_date, end=end_date, check_data_length=check_data_length)
        self.max_workers = (
            max(collector.multiprocessing.cpu_count() - 2, 1)
            if self.max_workers is None or self.max_workers <= 1
            else self.max_workers
        )
        self.normalize_data_1d_extend(qlib_data_1d_dir)

        collector.DumpDataUpdate(
            data_path=self.normalize_dir,
            qlib_dir=qlib_data_1d_dir,
            exclude_fields="symbol,date",
            max_workers=self.max_workers,
        ).dump()

        get_instruments = getattr(
            collector.importlib.import_module("data_collector.us_index.collector"), "get_instruments"
        )
        get_instruments(str(qlib_data_1d_dir), "NASDAQ100", market_index="us_index")

if __name__ == "__main__":
    fire.Fire(Nasdaq100Run)

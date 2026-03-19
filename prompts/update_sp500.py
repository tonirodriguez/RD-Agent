import sys
import os
import types
import multiprocessing
import pandas as pd
from pathlib import Path
import fire

# Añadir el repositorio de Qlib al path para importar el recolector
DEFAULT_QLIB_REPO = "/mnt/c/Users/trodriguez/src/qlib"
QLIB_REPO = os.environ.get("QLIB_REPO", DEFAULT_QLIB_REPO)
COLLECTOR_DIR = Path(QLIB_REPO) / "scripts" / "data_collector" / "yahoo"
if not COLLECTOR_DIR.exists():
    alt_repo = Path(__file__).resolve().parents[2] / "qlib"
    alt_collector_dir = alt_repo / "scripts" / "data_collector" / "yahoo"
    if alt_collector_dir.exists():
        COLLECTOR_DIR = alt_collector_dir
sys.path.append(str(COLLECTOR_DIR))

import collector
from collector import Run, YahooCollectorUS1d, YahooNormalize


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


_install_fake_useragent_fallback()


# Extendemos el recolector de Yahoo para que solo use la lista de SP500
class SP500Collector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de símbolos de SP500 exclusivamente...")
        data_dir = os.environ.get("SP500_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        ins_path = Path(data_dir) / "instruments" / "sp500.txt"
        
        if not ins_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de instrumentos {ins_path}. Necesitas tener el dataset inicial US con S&P 500.")
        
        df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"])
        symbols = df["symbol"].unique().tolist()
        
        # Opcional: añadir ticker del índice
        symbols.append("^GSPC")
        
        # Formato de Qlib
        def _format(s_):
            s_ = s_.replace(".", "-")
            s_ = s_.strip("$")
            s_ = s_.strip("*")
            return s_
            
        res = sorted(set(map(_format, filter(lambda x: len(x) < 8 and not x.endswith("WS"), symbols))))
        print(f"Total de símbolos a descargar: {len(res)}")
        return res


class _DailyDateSanitizer:
    @staticmethod
    def _sanitize_daily_dates(df: pd.DataFrame, date_field_name: str) -> pd.DataFrame:
        cleaned = df.copy()
        date_series = cleaned[date_field_name].astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})", expand=False)
        cleaned[date_field_name] = date_series.fillna(cleaned[date_field_name])
        return cleaned

    @staticmethod
    def normalize_yahoo(
        df: pd.DataFrame,
        calendar_list: list = None,
        date_field_name: str = "date",
        symbol_field_name: str = "symbol",
        last_close: float = None,
    ):
        cleaned = _DailyDateSanitizer._sanitize_daily_dates(df, date_field_name)
        return YahooNormalize.normalize_yahoo(
            cleaned,
            calendar_list=calendar_list,
            date_field_name=date_field_name,
            symbol_field_name=symbol_field_name,
            last_close=last_close,
        )


class SP500NormalizeUS1d(_DailyDateSanitizer, collector.YahooNormalizeUS1d):
    pass


class SP500NormalizeUS1dExtend(_DailyDateSanitizer, collector.YahooNormalizeUS1dExtend):
    pass

# Inyectamos la clase en el módulo para que 'Run' la encuentre al usar getattr()
collector.SP500Collector = SP500Collector
collector.SP500NormalizeUS1d = SP500NormalizeUS1d
collector.SP500NormalizeUS1dExtend = SP500NormalizeUS1dExtend

class SP500Run(Run):
    @property
    def collector_class_name(self):
        return "SP500Collector"

    @property
    def normalize_class_name(self):
        return "SP500NormalizeUS1d"

    def update_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        end_date: str = None,
        check_data_length: int = None,
        delay: float = 1,
        exists_skip: bool = False,
    ):
        if exists_skip:
            raise ValueError("exists_skip=True no esta soportado en este wrapper")

        qlib_data_1d_dir = str(Path(qlib_data_1d_dir).expanduser().resolve())
        os.environ["SP500_INSTRUMENTS_DATA_DIR"] = qlib_data_1d_dir
        if not collector.exists_qlib_data(qlib_data_1d_dir):
            collector.GetData().qlib_data(
                target_dir=qlib_data_1d_dir, interval=self.interval, region=self.region, exists_skip=exists_skip
            )

        calendar_path = Path(qlib_data_1d_dir).joinpath("calendars/day.txt")
        if not calendar_path.exists():
            raise ValueError(f"No se encontro el calendario base en {calendar_path}")

        calendar_df = pd.read_csv(calendar_path)
        trading_date = (pd.Timestamp(calendar_df.iloc[-1, 0]) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        if end_date is None:
            end_date = (pd.Timestamp(trading_date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        self.download_data(delay=delay, start=trading_date, end=end_date, check_data_length=check_data_length)
        self.max_workers = (
            max(multiprocessing.cpu_count() - 2, 1)
            if self.max_workers is None or self.max_workers <= 1
            else self.max_workers
        )
        self.normalize_data_1d_extend(qlib_data_1d_dir)

        dump = collector.DumpDataUpdate(
            data_path=self.normalize_dir,
            qlib_dir=qlib_data_1d_dir,
            exclude_fields="symbol,date",
            max_workers=self.max_workers,
        )
        dump.dump()

        get_instruments = getattr(
            collector.importlib.import_module("data_collector.us_index.collector"), "get_instruments"
        )
        get_instruments(str(qlib_data_1d_dir), "SP500", market_index="us_index")

if __name__ == "__main__":
    fire.Fire(SP500Run)

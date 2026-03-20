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


def _patch_sp500_changes_parser():
    us_index_collector = collector.importlib.import_module("data_collector.us_index.collector")

    def _flatten_column_name(column) -> str:
        if isinstance(column, tuple):
            parts = [
                str(part).strip()
                for part in column
                if str(part).strip() and not str(part).startswith("Unnamed")
            ]
            return " ".join(parts)
        return str(column).strip()

    def _get_changes(self) -> pd.DataFrame:
        us_index_collector.logger.info("get sp500 history changes......")
        headers = {"User-Agent": self._ua.random}
        response = us_index_collector.requests.get(self.WIKISP500_CHANGES_URL, headers=headers, timeout=None)
        response.raise_for_status()

        selected_df = None
        for table in reversed(us_index_collector.pd.read_html(us_index_collector.StringIO(response.text))):
            flat_columns = [_flatten_column_name(col) for col in table.columns]
            normalized = [col.lower() for col in flat_columns]

            try:
                date_idx = next(i for i, col in enumerate(normalized) if "effective date" in col or col == "date")
                add_idx = next(i for i, col in enumerate(normalized) if col.startswith("added") and "ticker" in col)
                remove_idx = next(i for i, col in enumerate(normalized) if col.startswith("removed") and "ticker" in col)
            except StopIteration:
                continue

            selected_df = table.iloc[:, [date_idx, add_idx, remove_idx]].copy()
            selected_df.columns = [self.DATE_FIELD_NAME, self.ADD, self.REMOVE]
            break

        if selected_df is None:
            raise ValueError("Could not find the SP500 changes table in the current Wikipedia page structure")

        selected_df[self.DATE_FIELD_NAME] = us_index_collector.pd.to_datetime(
            selected_df[self.DATE_FIELD_NAME], errors="coerce"
        )
        selected_df.dropna(subset=[self.DATE_FIELD_NAME], inplace=True)

        result = []
        for change_type in [self.ADD, self.REMOVE]:
            change_df = selected_df.copy()
            change_df[self.CHANGE_TYPE_FIELD] = change_type
            change_df[self.SYMBOL_FIELD_NAME] = change_df[change_type]
            change_df.dropna(subset=[self.SYMBOL_FIELD_NAME], inplace=True)
            if change_type == self.ADD:
                change_df[self.DATE_FIELD_NAME] = change_df[self.DATE_FIELD_NAME].apply(
                    lambda x: us_index_collector.get_trading_date_by_shift(self.calendar_list, x, 0)
                )
            else:
                change_df[self.DATE_FIELD_NAME] = change_df[self.DATE_FIELD_NAME].apply(
                    lambda x: us_index_collector.get_trading_date_by_shift(self.calendar_list, x, -1)
                )
            result.append(change_df[[self.DATE_FIELD_NAME, self.CHANGE_TYPE_FIELD, self.SYMBOL_FIELD_NAME]])

        us_index_collector.logger.info("end of get sp500 history changes.")
        return us_index_collector.pd.concat(result, sort=False)

    us_index_collector.SP500Index.get_changes = _get_changes


_patch_sp500_changes_parser()


# Extendemos el recolector de Yahoo para que solo use la lista de SP500
class SP500Collector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de símbolos de SP500 exclusivamente...")
        data_dir = os.environ.get("SP500_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        effective_date = pd.Timestamp(os.environ.get("SP500_EFFECTIVE_DATE", pd.Timestamp.today().strftime("%Y-%m-%d")))
        ins_path = Path(data_dir) / "instruments" / "sp500.txt"
        
        if not ins_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de instrumentos {ins_path}. Necesitas tener el dataset inicial US con S&P 500.")
        
        df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"])
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
        active_mask = df["start_date"].le(effective_date) & df["end_date"].ge(effective_date)
        symbols = df.loc[active_mask, "symbol"].dropna().unique().tolist()
        
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
        effective_date = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        os.environ["SP500_EFFECTIVE_DATE"] = effective_date

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

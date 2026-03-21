import sys
import os
import types
import shutil
import multiprocessing
import pandas as pd
from pathlib import Path
import fire

# Resolver el repo de Qlib de forma robusta
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


_install_fake_useragent_fallback()
_patch_yahoo_normalize()
_patch_mixed_date_parsing()
_patch_sp500_changes_parser()


class USAllCollector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de simbolos US_ALL exclusivamente...")
        data_dir = os.environ.get("US_ALL_INSTRUMENTS_SOURCE_DIR") or os.environ.get("US_ALL_INSTRUMENTS_DATA_DIR") or os.environ.get(
            "DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data")
        )
        effective_date = pd.Timestamp(os.environ.get("US_ALL_EFFECTIVE_DATE", pd.Timestamp.today().strftime("%Y-%m-%d")))
        use_all_symbols = os.environ.get("US_ALL_USE_ALL_SYMBOLS", "0") == "1"
        ins_path = Path(data_dir) / "instruments" / "all.txt"

        if not ins_path.exists():
            raise FileNotFoundError(
                f"No se encontro el archivo de instrumentos {ins_path}. Necesitas tener el dataset inicial US."
            )

        df = pd.read_csv(ins_path, sep="\t", names=["symbol", "start_date", "end_date"])
        df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
        df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
        if use_all_symbols:
            return df.loc[:, "symbol"].dropna().unique().tolist()
        active_mask = df["start_date"].le(effective_date) & df["end_date"].ge(effective_date)
        return df.loc[active_mask, "symbol"].dropna().unique().tolist()


collector.USAllCollector = USAllCollector


class USAllRun(Run):
    @staticmethod
    def _find_valid_universe_dir(base_dir: Path, target_name: str):
        candidates = []
        direct_candidate = base_dir / target_name
        candidates.append(direct_candidate)
        candidates.extend(sorted(base_dir.glob(f"{target_name}_backup_*"), reverse=True))

        for candidate in candidates:
            all_path = candidate / "instruments" / "all.txt"
            day_path = candidate / "calendars" / "day.txt"
            if (
                candidate.exists()
                and all_path.exists()
                and day_path.exists()
                and all_path.stat().st_size > 0
                and day_path.stat().st_size > 0
            ):
                return candidate
        return None

    def _refresh_us_indexes(self, qlib_data_1d_dir: str):
        get_instruments = getattr(
            collector.importlib.import_module("data_collector.us_index.collector"), "get_instruments"
        )
        for index_name in ["SP500", "NASDAQ100", "DJIA", "SP400"]:
            get_instruments(str(qlib_data_1d_dir), index_name, market_index="us_index")

    @property
    def collector_class_name(self):
        return "USAllCollector"

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
            collector.logger.warning("currently supports 1d data updates: --interval 1d")

        qlib_data_1d_dir = str(Path(qlib_data_1d_dir).expanduser().resolve())
        os.environ["US_ALL_INSTRUMENTS_DATA_DIR"] = qlib_data_1d_dir
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
        os.environ["US_ALL_EFFECTIVE_DATE"] = effective_date

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

        self._refresh_us_indexes(qlib_data_1d_dir)

    def rebuild_data_to_bin(
        self,
        qlib_data_1d_dir: str,
        start_date: str = "1999-12-31",
        end_date: str = None,
        universe_data_dir: str = None,
        backup_existing: bool = True,
        backup_suffix: str = None,
        delay: float = 1,
    ):
        if self.interval.lower() != "1d":
            collector.logger.warning("currently supports 1d data rebuilds: --interval 1d")

        qlib_data_1d_dir = Path(qlib_data_1d_dir).expanduser().resolve()
        universe_dir = Path(universe_data_dir).expanduser().resolve() if universe_data_dir else None
        backup_dir = None

        if backup_existing and qlib_data_1d_dir.exists():
            suffix = backup_suffix or pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = qlib_data_1d_dir.parent / f"{qlib_data_1d_dir.name}_backup_{suffix}"
            if backup_dir.exists():
                raise FileExistsError(f"Backup dir already exists: {backup_dir}")
            shutil.move(str(qlib_data_1d_dir), str(backup_dir))
            collector.logger.warning(f"Existing dataset moved to backup: {backup_dir}")

        if universe_dir is None:
            if backup_dir is not None:
                universe_dir = backup_dir
            elif qlib_data_1d_dir.exists() and (qlib_data_1d_dir / "instruments" / "all.txt").exists():
                universe_dir = qlib_data_1d_dir
            else:
                universe_dir = self._find_valid_universe_dir(qlib_data_1d_dir.parent, qlib_data_1d_dir.name)

        if universe_dir is None or not (universe_dir / "instruments" / "all.txt").exists():
            raise FileNotFoundError(
                "A clean rebuild needs a valid universe source. Pass --universe_data_dir "
                "or run it over an existing dataset so its backup can be used as the universe source."
            )

        qlib_data_1d_dir.mkdir(parents=True, exist_ok=True)
        os.environ["US_ALL_INSTRUMENTS_DATA_DIR"] = str(qlib_data_1d_dir)
        os.environ["US_ALL_INSTRUMENTS_SOURCE_DIR"] = str(universe_dir)
        os.environ["US_ALL_USE_ALL_SYMBOLS"] = "1"

        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        if self.normalize_dir.exists():
            shutil.rmtree(self.normalize_dir)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.normalize_dir.mkdir(parents=True, exist_ok=True)

        start_date = pd.Timestamp(start_date).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = pd.Timestamp.today().strftime("%Y-%m-%d")
        else:
            end_date = pd.Timestamp(end_date).strftime("%Y-%m-%d")

        effective_date = (pd.Timestamp(end_date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        os.environ["US_ALL_EFFECTIVE_DATE"] = effective_date

        self.download_data(delay=delay, start=start_date, end=end_date)
        source_files = list(self.source_dir.glob("*.csv"))
        if not source_files:
            raise RuntimeError(
                "Clean rebuild aborted: no source CSV files were downloaded. "
                "The dataset will not be overwritten with empty calendars or instruments."
            )
        self.max_workers = (
            max(collector.multiprocessing.cpu_count() - 2, 1)
            if self.max_workers is None or self.max_workers <= 1
            else self.max_workers
        )
        self.normalize_data(end_date=end_date)
        normalized_files = list(self.normalize_dir.glob("*.csv"))
        if not normalized_files:
            raise RuntimeError(
                "Clean rebuild aborted: no normalized CSV files were produced. "
                "The dataset will not be overwritten with empty calendars or instruments."
            )

        dump_bin_module = collector.importlib.import_module("dump_bin")
        dump_bin_module.DumpDataAll(
            data_path=self.normalize_dir,
            qlib_dir=str(qlib_data_1d_dir),
            exclude_fields="symbol,date",
            max_workers=self.max_workers,
        ).dump()

        calendar_path = qlib_data_1d_dir / "calendars" / "day.txt"
        instruments_path = qlib_data_1d_dir / "instruments" / "all.txt"
        if not calendar_path.exists() or calendar_path.stat().st_size == 0:
            raise RuntimeError("Clean rebuild failed: calendars/day.txt was generated empty.")
        if not instruments_path.exists() or instruments_path.stat().st_size == 0:
            raise RuntimeError("Clean rebuild failed: instruments/all.txt was generated empty.")

        self._refresh_us_indexes(str(qlib_data_1d_dir))


if __name__ == "__main__":
    fire.Fire(USAllRun)

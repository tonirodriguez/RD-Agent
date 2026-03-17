import sys
import os
import pandas as pd
from pathlib import Path
import fire

# Añadir el repositorio de Qlib al path para importar el recolector
QLIB_REPO = os.environ.get("QLIB_REPO", "/mnt/d/src/qlib")
sys.path.append(os.path.join(QLIB_REPO, "scripts", "data_collector", "yahoo"))

import collector
from collector import Run, YahooCollectorUS1d

# Extendemos el recolector de Yahoo para que solo use la lista de SP500
class SP500Collector(YahooCollectorUS1d):
    def get_instrument_list(self):
        print("Obteniendo lista de símbolos de SP500 exclusivamente...")
        data_dir = os.environ.get("DATA_DIR", os.path.expanduser("~/.qlib/qlib_data/us_data"))
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

# Inyectamos la clase en el módulo para que 'Run' la encuentre al usar getattr()
collector.SP500Collector = SP500Collector

class SP500Run(Run):
    @property
    def collector_class_name(self):
        return "SP500Collector"

if __name__ == "__main__":
    fire.Fire(SP500Run)

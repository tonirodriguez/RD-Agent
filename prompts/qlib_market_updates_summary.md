# Resumen de Actualización de Mercado Qlib (Sesión 2026-03-14 / 2026-03-15)

Este documento recopila todos los scripts generados, errores resueltos y procedimientos de actualización exitosos para gestionar datos del mercado de Estados Unidos (US Market) con Microsoft Qlib.

## 1. Scripts Generados

### A) `update_us_qlib_daily.sh`
**Ubicación:** `d:\src\RD-Agent\prompts\update_us_qlib_daily.sh`
**Propósito:** Actualizar todo el mercado estadounidense desde una fecha específica (e.g., `2025-12-31`) hasta el día actual.
**Detalles Clave:**
*   Añade `export PYTHONPATH="$(pwd):${PYTHONPATH:-}"` para evitar errores de módulos no encontrados ejecutando Qlib desde el código fuente local.
*   Incluye el parámetro explícito `--region US` al script `collector.py update_data_to_bin`. Esto soluciona un error de desconexión (`RemoteDisconnected`), ya que Qlib por defecto intenta conectarse a los servidores chinos de EastMoney en lugar de Yahoo Finance si no se le especifica la región.

### B) `update_nasdaq100.py`
**Ubicación:** Inicialmente en `d:\src\RD-Agent\prompts\update_nasdaq100.py`, luego movido por el usuario a `scripts/update_nasdaq100.py` dentro del repositorio de Qlib.
**Propósito:** Evitar la descarga masiva de todos los miles de símbolos activos en Yahoo Finance (NYSE, NASDAQ, etc) y limitarlo exclusivamente a los ~100 tickers del índice Nasdaq 100.
**Detalles Clave:**
*   Hereda de `YahooCollectorUS1d` y sobrescribe el método `get_instrument_list()`.
*   Lee el archivo `instruments/nasdaq100.txt` del dataset existente y retorna solo esa pequeña lista, ahorrando tiempo y peticiones.

### C) `update_sp500.py`
**Ubicación:** `d:\src\RD-Agent\prompts\update_sp500.py`
**Propósito:** Similar al script del Nasdaq 100, este archivo restringe la descarga de datos de Yahoo Finance de modo que procese únicamente los tickers formantes del S&P 500, leyendo la lista desde `instruments/sp500.txt`.

### D) `update_nasdaq_qlib_daily.sh` y `update_sp500_qlib_daily.sh`
**Ubicación:** `d:\src\RD-Agent\prompts\update_nasdaq_qlib_daily.sh` y `d:\src\RD-Agent\prompts\update_sp500_qlib_daily.sh`
**Propósito:** Son los archivos envoltorio en bash que sirven de lanzadores (wrappers) para invocar a los scripts `.py` personalizados, filtrando de forma segura las fechas desde finales del año pasado y configurando el `PYTHONPATH`.

### E) `fix_all_txt.py`
**Ubicación:** `d:/src/RD-Agent/prompts/fix_all_txt.py`
**Propósito:** Reconstruir el archivo de instrumentos global de Qlib (`~/.qlib/qlib_data/us_data/instruments/all.txt`) de forma robusta e infalible, leyendo directamente el tamaño de los binarios (`close.day.bin` o `factor.day.bin`) generados en la carpeta `features`.
**Por qué se creó:** Para sortear el error `ValueError: Unsupported file format:` levantado por `pandas` cuando intentaba actualizar los instrumentos leyendo de la carpeta temporal `normalize` que contenía archivos defectuosos o no-CSV.

---

## 2. Errores Resueltos Exitosamente

### ❌ `ModuleNotFoundError: No module named 'qlib.data._libs.rolling'`
**Causa:** Ejecutar Qlib directamente desde el código fuente (`/mnt/d/src/qlib`) sin compilar sus extensiones escritas en Cython (`.pyx`).
**Solución Exitosa:** Se compilaron las extensiones "in-place" ejecutando en terminal dentro del directorio qlib:
```bash
pip install setuptools numpy cython pybind11
python setup.py build_ext --inplace
```
---

## 3. Procedimientos de Actualización Validados

### Actualizar el archivo maestro de símbolos del índice desde Internet (Index Collector)
Si la conformación de las empresas del SP500 o NASDAQ100 han cambiado, se actualizaron localmente ejecutando los siguientes comandos en la raíz (ej: `/mnt/d/src/qlib`):

**Para el NASDAQ-100:**
```bash
python scripts/data_collector/us_index/collector.py \
  --index_name NASDAQ100 \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --method parse_instruments
```

**Para el S&P 500:**
```bash
python scripts/data_collector/us_index/collector.py \
  --index_name SP500 \
  --qlib_dir ~/.qlib/qlib_data/us_data \
  --method parse_instruments
```

*(Ambos scripts analizan la URL de Wikipedia correspondiente al índice histórico, parsean las tablas con BeautifulSoup, identifican acciones entrantes y salientes [add / remove] y guardan los .txt en el dataset.)*

---

## 4. Scripts Generados Hoy (Sesión 2026-03-15)

### A) `graph_stock.py` y `graph_stock.ipynb`
**Ubicación:** `d:\src\RD-Agent\prompts\graph_stock.py` y `d:\src\RD-Agent\prompts\graph_stock.ipynb`
**Propósito:** Graficar la evolución histórica del precio de cierre de un símbolo específico usando los datos de Qlib.
**Detalles Clave:**
*   Recibe un parámetro por línea de comandos (en el script de Python, p. ej. `python graph_stock.py AAPL`) correspondiente al *ticker* a consultar.
*   Inicializa los datos de `us_data` desde `~/.qlib/qlib_data/us_data`.
*   Extrae con Qlib (`D.features()`) los datos históricos (`$close`) limitados hacia atrás al `1-1-2020` y los grafica usando la librería **matplotlib**.
*   El *notebook* equivalente hace lo mismo y está preparado para ser ejecutado cómodamente celda por celda a modo de análisis interactivo.

### B) `backup_qlib_us_data.sh`
**Ubicación:** `d:\src\RD-Agent\prompts\backup_qlib_us_data.sh`
**Propósito:** Generar un backup integral de la base de datos binaria de Qlib.
**Detalles Clave:**
*   Apunta a la carpeta objetivo `$HOME/.qlib/qlib_data/us_data`.
*   Crea dinámicamente el directorio `$HOME/.qlib/backups` si no existe.
*   Comprime todo en un único archivo `.zip` cuyo nombre finaliza con un sello de tiempo (*timestamp*) para versionar el backup y evitar reemplazos indeseados (ej. `us_data_backup_20260315_230230.zip`).

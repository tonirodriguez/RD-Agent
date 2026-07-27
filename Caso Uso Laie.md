# Caso de uso — Previsión de ventas semanales de Laie con RD-Agent

Documento único del experimento: previsión de **ventas semanales por tienda** hasta el
**31/12/2026**, con RD-Agent (escenario **`data_science`**, modo dataset local). Recoge el
plan, la preparación real de los datos, la configuración y los pasos de ejecución.

---

## 1. Idea clave (condiciona todo el diseño)

RD-Agent **optimiza contra un test con etiquetas conocidas**: necesita la "verdad" para
puntuar cada iteración. No puede optimizar sobre el futuro real (ago-dic 2026, sin ventas
aún). Por eso el proyecto es un **backtest con holdout**:

1. Se reserva un periodo pasado conocido y **con la misma estacionalidad** (ago-dic 2025) como
   test → RD-Agent optimiza el pipeline sobre él.
2. Se reentrena el pipeline ganador con **todo** el histórico y se predice ago-dic 2026.

---

## 2. Datos de partida (export SAP real)

Fichero recibido: export SAP de ventas de Laie.

- **Formato**: separador `#`, encoding `latin-1`, campos entrecomillados.
- **Columnas**: `centro, nombre, fecha, target, budget, semana_en_anyo, mes_nombre,
  es_findesemana, ..., es_semana_santa`.
- **Granularidad**: diaria, **2014-01-01 → 2026-07-27** (hasta hoy).
- **Venta a predecir** = columna **`target`** (venta neta real; incluye devoluciones
  negativas). `budget` es el presupuesto/plan y se descarta.

### Decisiones tomadas sobre los datos

- **Solo tiendas físicas permanentes** (36 en total: 35 `T0xx` + `LAIE_CAF`).
- **Excluidos**: canales WEB (online), almacenes (GRAN, SANT), paradas (P0xx), eventos /
  exposiciones (E0xx: Feria del Libro, ARCO, Setmana del Llibre, Imagine Picasso) y aperturas
  de 2026 sin histórico / con ventas ~0.
- **COVID (2020-2021)**: se mantiene en el histórico marcado con `covid=1` (para que el modelo
  pueda condicionar), pero **queda fuera del test**. No se elimina.

---

## 3. Diseño del experimento (block forecast)

- **train**: histórico hasta **2025-07-31**.
- **test (holdout)**: **2025-08-01 → 2025-12-31**, todas las tiendas (mismo tramo estacional
  que se va a prever: vuelta al cole + Navidad, sin Sant Jordi).
- **Previsión en bloque**: se predice todo el periodo de golpe. Para predecir una semana **no**
  se pueden usar ventas de otras semanas del propio test.
- **Métrica**: **WAPE** (`sum(|pred-real|)/sum(|real|)`, menor es mejor).
- **Restricción anti-fuga**: solo features conocidas en el momento de prever — calendario y
  eventos (Sant Jordi, Navidad, vuelta al cole, Semana Santa), atributos de tienda, y **lags
  interanuales** (misma semana del año anterior, ≥52). Prohibidos los lags cortos (1-4 sem).

---

## 4. Estructura del dataset (generada)

Bajo `git_ignore_folder/ds_data/`:

```
laie-sales-forecast/
├── description.md                 # tarea, columnas, WAPE, restricción anti-fuga
├── sample_submission.csv          # formato de entrega: id, sales
├── train/train.csv                # store_id, date, sales, covid, semana_santa
├── test/test.csv                  # id, store_id, date, covid, semana_santa (sin sales)
└── forecast/test_2026.csv         # semanas ago-dic 2026 (previsión real)

eval/laie-sales-forecast/
├── grade.py                       # WAPE (menor = mejor), alinea por 'id'
├── valid.py                       # valida formato de submission
└── submission_test.csv            # verdad del holdout (id, sales)

sample/laie-sales-forecast/...     # subconjunto (3 tiendas) para debug
raw/ventas_laie_raw.csv            # copia del export original
```

- `id` = `"<store_id>__<fecha>"`. Fecha semanal = **lunes** (ISO) en `YYYY-MM-DD`.
- Features añadidas: `covid` (0/1) y `semana_santa` (0/1, derivada de `es_semana_santa`).

### Resultado de la preparación (datos reales)

- **36 tiendas**, rango semanal 2013-12-30 → 2026-07-27.
- **TRAIN**: 17.762 filas (COVID incluido, `covid=1`).
- **TEST**: 771 filas (holdout ago-dic 2025). `submission_test.csv` **cuadra** con 771.
- **FORECAST**: 792 filas, 2026-08-03 → 2026-12-31 (36 tiendas).
- Magnitudes coherentes (p. ej. T004 La Pedrera ~90-150k€/sem, T007 CaixaForum ~5-8k€/sem).

---

## 5. Preparación de datos — `prepare_laie_data.py`

Convierte el export SAP en la estructura anterior: agrega a semana (lunes), rellena huecos con
0 desde la primera venta real de cada tienda (recorta ceros previos a la apertura, que
confundían al agente), marca COVID, aplica el filtro de tiendas, monta el
holdout y genera el test de la previsión 2026.

```bash
cd ~/dev/RD-Agent
source .venv/bin/activate
python prepare_laie_data.py --sales git_ignore_folder/ds_data/raw/ventas_laie_raw.csv
# Opciones: --include-web  --include-all  --exclude-covid  --min-total-sales 1000
```

Para **actualizar** la previsión más adelante, vuelve a exportar de SAP y relanza el script.

---

## 6. Configuración (.env)

```bash
DS_SCEN="rdagent.scenarios.data_science.scen.DataScienceScen"   # modo local, NO Kaggle
DS_LOCAL_DATA_PATH="/home/toni/dev/RD-Agent/git_ignore_folder/ds_data"
DS_CODER_ON_WHOLE_PIPELINE=True
DS_IF_USING_MLE_DATA=False
DS_SAMPLE_DATA_BY_LLM=False
```

> Importante: fija `DS_LOCAL_DATA_PATH` a tu copia de trabajo (`~/dev/...`), no a `/mnt/c/...`,
> para no leer del disco de Windows (lento). Puedes hacerlo con:
> `dotenv set DS_LOCAL_DATA_PATH "/home/toni/dev/RD-Agent/git_ignore_folder/ds_data"`

---

## 7. Requisitos previos del entorno (puesta a punto, una vez)

Antes de lanzar el experimento, el entorno debe estar listo. Resumen de todo lo necesario
(detalle en `Instrucciones Instalación.md`):

1. **Python 3.10/3.11** en un venv, con `rdagent` instalado desde el código:
   ```bash
   cd ~/dev/RD-Agent
   python3 -m venv .venv && source .venv/bin/activate
   pip install -U pip setuptools wheel
   pip install -e .
   ```
2. **Fijar `pydantic-ai` a la serie 1.x** (si no, `ImportError: MCPServerStreamableHTTP`):
   ```bash
   pip install "pydantic-ai-slim[mcp,openai,prefect]<2"
   ```
3. **Docker funcionando sin `sudo`** — el escenario `data_science` ejecuta el pipeline
   generado dentro de un contenedor:
   ```bash
   docker run hello-world
   ```
4. **LLM por OpenRouter configurado y validado.** `rdagent health_check` NO soporta OpenRouter;
   valida con el script de LiteLLM (`Instrucciones Instalación.md §5.2`). En `.env`:
   `CHAT_MODEL=openrouter/deepseek/deepseek-v4-flash`, `OPENROUTER_API_KEY=...`,
   `EMBEDDING_MODEL=litellm_proxy/openai/text-embedding-3-small`, `LITELLM_PROXY_API_KEY=...`,
   `LITELLM_PROXY_API_BASE=https://openrouter.ai/api/v1`.
5. **`MLFLOW_ALLOW_FILE_STORE=true`** en `.env` (evita el fallo de mlflow con el file store).
6. **Config del escenario** `DS_*` en `.env` (ver §6) y `DS_LOCAL_DATA_PATH` apuntando a tu
   copia de trabajo (`~/dev/...`).
7. **Dataset preparado** (§4-§5): `prepare_laie_data.py` ejecutado y los ficheros en
   `git_ignore_folder/ds_data/laie-sales-forecast/` + `eval/`.

Chequeo rápido de que el dataset está bien:
```bash
ls git_ignore_folder/ds_data/laie-sales-forecast/{train/train.csv,test/test.csv,sample_submission.csv}
ls git_ignore_folder/ds_data/eval/laie-sales-forecast/{grade.py,valid.py,submission_test.csv}
# test y submission_test deben tener el MISMO nº de filas:
wc -l git_ignore_folder/ds_data/laie-sales-forecast/test/test.csv \
      git_ignore_folder/ds_data/eval/laie-sales-forecast/submission_test.csv
```

---

## 8. Ejecución

```bash
cd ~/dev/RD-Agent
source .venv/bin/activate

# 1) Validar la cadena (1 vuelta)
rdagent data_science --competition laie-sales-forecast --loop-n 1

# 2) Ciclo completo
rdagent data_science --competition laie-sales-forecast --loop-n 10
```

RD-Agent propone hipótesis (features, modelos, ensembles), escribe el pipeline completo
(`main.py`: datos → feature engineering → entrena → predice → `submission.csv`), lo puntúa con
`grade.py` (WAPE) y guarda el mejor (SOTA).

### Monitorización (UI) — en otra terminal

```bash
STREAMLIT_SERVER_FILE_WATCHER_TYPE=none rdagent ui --port 19899 --log-dir "log/" --data-science
```

- Abre http://localhost:19899 y elige tu run (carpeta con timestamp) en el desplegable
  **"Select from `log/`"**. `--log-dir` apunta a la carpeta **padre `log/`** (no al timestamp).

---

## 9. Previsión real (fase final)

Cuando tengas el pipeline ganador:

1. Reentrénalo con **todo** el histórico (train + holdout, hasta jul-2026).
2. Predice `forecast/test_2026.csv` (semanas ago-dic 2026 de las 36 tiendas).
3. Eso es tu **previsión por tienda hasta el 31/12/2026**.
4. Valida con sentido de negocio (Navidad, campañas) y revisa el WAPE por tienda.

---

## 10. Caveats

- RD-Agent es optimización estilo Kaggle (una métrica sobre test etiquetado); no es una
  herramienta nativa de series temporales. Funciona bien **si** el holdout está bien montado
  (sin fuga temporal).
- **Modelo global** (todas las tiendas con `store_id` como feature) > un modelo por tienda.
- **Tiendas nuevas de 2026** (p. ej. T019) entran en la previsión pero **sin histórico
  interanual**; se cubren con medias del grupo, con previsión menos fiable. Se pueden excluir.
- **Coste/tiempo**: cada iteración llama mucho al LLM y entrena modelos; empieza con `--loop-n 1`.

---

## 11. Esquema de datos (referencia)

| Fichero | Columnas |
|---|---|
| `train/train.csv` | `store_id, date, sales, covid, semana_santa` |
| `test/test.csv` | `id, store_id, date, covid, semana_santa` |
| `forecast/test_2026.csv` | `id, store_id, date, covid, semana_santa` |
| `sample_submission.csv` / `submission_test.csv` | `id, sales` |

- `id = "<store_id>__<fecha>"`; fecha = lunes de la semana (`YYYY-MM-DD`).
- `sales` en € (venta neta, con devoluciones). `covid` y `semana_santa` en 0/1.

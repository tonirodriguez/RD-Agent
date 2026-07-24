# Instrucciones — Configurar y lanzar un escenario concreto

Un escenario se configura en **tres capas** (de lo más global a lo más concreto) y se lanza
con `rdagent <escenario>`. Requisito previo en cada terminal: `source .venv/bin/activate`.

---

## 1. `.env` — configuración global y por escenario

- **LLM (común a todos):** chat y embeddings vía OpenRouter. No cambia entre escenarios.
- **Variables por escenario:** cada familia lee sus propias variables con prefijo.
  El caso principal es `data_science`, con prefijo `DS_`:

```bash
DS_SCEN="rdagent.scenarios.data_science.scen.DataScienceScen"   # o ...KaggleScen
DS_LOCAL_DATA_PATH="/ruta/al/repo/git_ignore_folder/ds_data"
DS_IF_USING_MLE_DATA=False        # True en modo Kaggle
DS_SAMPLE_DATA_BY_LLM=False       # True en modo Kaggle
DS_CODER_ON_WHOLE_PIPELINE=True
```

Cambiar una de estas variables y volver a lanzar es la forma principal de "reconfigurar"
el escenario. Los escenarios `fin_*` funcionan con sus valores por defecto y no necesitan
tocar `.env`.

---

## 2. Flags del comando — parámetros de esa ejecución

Parámetros aceptados (verificados en el código):

### Escenarios `fin_*` (`fin_factor`, `fin_model`, `fin_quant`)

| Flag | Efecto |
|---|---|
| `--loop-n N` | Nº de iteraciones del loop |
| `--step-n N` | Ejecuta solo N pasos |
| `--all-duration "2h"` | Presupuesto de tiempo total |
| `--path <sesión>` | Reanuda una sesión previa |
| `--checkout / --no-checkout` (`-c/-C`) | Reusar carpeta de logs limpiando o conservando |

```bash
rdagent fin_factor --loop-n 3
rdagent fin_factor --step-n 1
rdagent fin_factor --all-duration "2h"
rdagent fin_factor --path <sesión>
```

### Escenarios específicos

```bash
# fin_factor_report: carpeta de informes PDF
rdagent fin_factor_report --report-folder=git_ignore_folder/reports --loop-n 2

# general_model: URL o PDF de un paper (sin datos locales)
rdagent general_model "https://arxiv.org/pdf/2210.09789"

# data_science: competición + control de loop/tiempo
rdagent data_science --competition arf-12-hours-prediction-task --loop-n 5
```

`data_science` acepta además `--timeout`, `--step-n` y `--loop-n`.

---

## 3. Reanudar / controlar la sesión

- `--path $LOG_PATH/__session__/1/0_propose` → retoma un run desde un punto guardado.
- `--checkout` / `--no-checkout` → decide si reusar la carpeta de logs limpiando o
  conservando los pasos posteriores al punto indicado.

---

## 4. Flujo típico para lanzar un escenario

1. Ajusta lo necesario en `.env` (solo relevante para `data_science`; los `fin_*`
   funcionan sin tocar nada).
2. Lanza con los flags de esa corrida.

Ejemplo de prueba corta y barata de factores:

```bash
source .venv/bin/activate
rdagent fin_factor --loop-n 1
```

> Consejo: en la primera prueba de cualquier escenario, limita con `--loop-n 1` o
> `--all-duration "30m"` para controlar el coste de API antes de lanzar loops largos.


## 5. Copiar dentro del FileSystem de WSL

Utilizar el file system de Windows hace que vaya muy despacio

```bash
cp -r "/mnt/c/Users/trodriguez/src/RD-Agent/" ~/dev/
```

---

## 6. Desplegar un escenario completo de `fin_quant`

`fin_quant` es el loop conjunto que propone hipótesis, implementa **factores y modelos**
alternándolos, los backtestea en qlib dentro de Docker y realimenta la siguiente iteración.

### 6.1 Qué ocurre por debajo

- **Imagen Docker `local_qlib:latest`**: RD-Agent la **construye sola** la primera vez desde
  `rdagent/scenarios/qlib/docker/Dockerfile` (no se descarga). Tarda y ocupa disco.
- **Datos qlib**: se montan desde `~/.qlib/` en el contenedor (`/root/.qlib/`).
- **Loop** (`QuantRDLoop`): `propose → coding → running (qrun conf.yaml) → feedback`.
- **Resultados**: en `log/` y en `git_ignore_folder/RD-Agent_workspace/` (uno por intento).

### 6.2 Requisitos previos (deben estar OK)

Python 3.10/3.11, `pydantic-ai-slim<2`, Docker **sin sudo**, y `.env` con OpenRouter
validado (ver Instrucciones Instalación §5.2).

```bash
cd /home/toni/dev/RD-Agent
source .venv/bin/activate
docker run hello-world        # Docker sin sudo
df -h /                       # ten ~10-15 GB libres (imagen + datos + workspaces)
```

### 6.3 Primera ejecución (valida toda la cadena)

```bash
rdagent fin_quant --loop-n 1
```

La primera vez construye la imagen y prepara los datos: tarda bastante, es normal.
Cuando complete una vuelta con su backtest, el pipeline funciona.

### 6.4 Ciclo completo

```bash
rdagent fin_quant --loop-n 10        # por nº de iteraciones
rdagent fin_quant --all-duration "3h"  # o por presupuesto de tiempo
```

### 6.5 Monitorizar (otra terminal, venv activado)

```bash
rdagent ui --port 19899 --log-dir "log/"
```
http://localhost:19899 → hipótesis, código generado y métricas de backtest (IC, retorno
anualizado, Sharpe) por iteración.

### 6.6 Reanudar si se corta

```bash
rdagent fin_quant --path log/__session__/<loop>/<step>
```

### 6.7 Avisos

- **Coste**: cada vuelta hace muchas llamadas al LLM; empieza con `--loop-n 1`.
- **Disco**: los workspaces crecen por iteración; limpia
  `git_ignore_folder/RD-Agent_workspace/` y usa `sync_rdagent.sh` (ya los excluye).

---

## 7. Adaptaciones para datos US

> En este fork **las plantillas de qlib ya están configuradas para US** — no hay que
> tocarlas. Lo verás en `rdagent/scenarios/qlib/experiment/*/*.yaml`:
> `provider_uri: "~/.qlib/qlib_data/us_data"`, `region: us`, `market: us`,
> `benchmark: ^GSPC` (S&P 500).

Quedan **dos** cosas por resolver para correr sobre US: tener los datos US en su sitio y
evitar que el auto-descargador baje datos CN.

### 7.1 Preparar los datos US en `~/.qlib/qlib_data/us_data`

Usa tus scripts del repo (`prompts/`), que construyen los datos desde Yahoo con un clon de
qlib en `/mnt/c/Users/trodriguez/src/qlib`:

```bash
# Reconstrucción completa (histórico desde cero)
bash prompts/update_us_qlib_rebuild.sh

# Actualización diaria incremental
bash prompts/update_us_qlib_daily.sh

# Universos concretos (opcional)
bash prompts/update_sp500_qlib_daily.sh
bash prompts/update_nasdaq_qlib_daily.sh

# Comprobar estado / última fecha
python prompts/check_us_qlib_update.py
```

Variables útiles (definidas en `update_us_qlib_daily.sh`): `QLIB_REPO` (ruta del clon de
qlib), `DATA_DIR` (destino, por defecto `~/.qlib/qlib_data/us_data`), `MAX_WORKERS`.

Verifica que quedó poblado:
```bash
ls ~/.qlib/qlib_data/us_data/{instruments,calendars,features} 2>/dev/null && echo "US data OK"
```

### 7.2 Evitar la descarga automática de datos CN

El preparador de Docker (`rdagent/utils/env.py`, clase `QlibDockerEnv.prepare()`) todavía
comprueba y descarga **CN**:

```python
if not (Path(qlib_data_path) / "qlib_data" / "cn_data").exists():
    cmd = "python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/cn_data --region cn --interval 1d --delete_old False"
    self.check_output(entry=cmd)
```

Cámbialo para que apunte a **US** (así, si ya construiste `us_data` con tus scripts, se
salta la descarga; y si no, baja la de US):

```python
if not (Path(qlib_data_path) / "qlib_data" / "us_data").exists():
    cmd = "python -m qlib.run.get_data qlib_data --target_dir ~/.qlib/qlib_data/us_data --region us --interval 1d --delete_old False"
    self.check_output(entry=cmd)
```

> ✅ **Este parche ya está aplicado en el repo** (copia de Windows). Si ejecutas desde
> `~/dev/RD-Agent`, propágalo con `bash sync_rdagent.sh --to-wsl`.
>
> Sin este cambio, `fin_quant` seguiría funcionando con US (las plantillas mandan),
> pero perderías tiempo y disco descargando datos CN que no se usan.

### 7.3 Lanzar `fin_quant` sobre US

Con los datos US en su sitio y (opcional) el parche aplicado:

```bash
source .venv/bin/activate
rdagent fin_quant --loop-n 1     # valida
rdagent fin_quant --all-duration "3h"
```

Las fechas de train/valid/test y el benchmark (`^GSPC`) salen de las plantillas; ajusta ahí
`start_time`/`end_time` si quieres otro periodo o universo (ver §8).

---

## 8. Plantillas qlib que usa `fin_quant`

No existe una "plantilla US" aparte: `fin_quant` usa estas **cinco** plantillas, y **todas
están ya configuradas para US**. Ubicación:

```
rdagent/scenarios/qlib/experiment/
├── factor_template/
│   ├── conf_baseline.yaml
│   ├── conf_combined_factors.yaml
│   └── conf_combined_factors_sota_model.yaml
└── model_template/
    ├── conf_baseline_factors_model.yaml
    └── conf_sota_factors_model.yaml
```

### 8.1 Cuál se usa en cada momento

El loop de `fin_quant` alterna ramas de **factores** y de **modelos**; los *runners*
eligen la plantilla según el estado de la traza.

**Factores** (`rdagent/scenarios/qlib/developer/factor_runner.py`):

| Plantilla | Cuándo se usa | Modelo |
|---|---|---|
| `conf_baseline.yaml` | Primer factor, sin experimentos previos (`based_experiments` vacío) | LGBModel (GBDT) |
| `conf_combined_factors.yaml` | Factores nuevos combinados con los SOTA anteriores | LGBModel (GBDT) |
| `conf_combined_factors_sota_model.yaml` | Factores combinados corriendo con el modelo SOTA de la traza | GeneralPTNN (red neuronal PyTorch) |

**Modelos** (`rdagent/scenarios/qlib/developer/model_runner.py`):

| Plantilla | Cuándo se usa | Modelo |
|---|---|---|
| `conf_baseline_factors_model.yaml` | Modelo nuevo sobre factores base (Alpha) | GeneralPTNN |
| `conf_sota_factors_model.yaml` | Modelo nuevo sobre los factores SOTA | GeneralPTNN |

(Descripciones cortas en los `README.md` de `factor_template/` y `model_template/`.)

### 8.2 Configuración común (idéntica en las cinco)

| Parámetro | Valor |
|---|---|
| `provider_uri` | `~/.qlib/qlib_data/us_data` |
| `region` / `market` | `us` / `us` |
| `benchmark` | `^GSPC` (S&P 500) |
| Estrategia | `TopkDropoutStrategy`, `topk: 50`, `n_drop: 5` |
| `ann_scaler` | `252` (días bursátiles US) |

### 8.3 Rangos de fechas (valores por defecto)

Split temporal por defecto (con variables Jinja, sobreescribibles):

| Segmento | Rango por defecto |
|---|---|
| **train** | `2008-01-01` → `2014-12-31` |
| **valid** | `2015-01-01` → `2016-12-31` |
| **test / backtest** | `2017-01-01` → `null` (hasta el final de los datos disponibles) |

`fit_start_time`/`fit_end_time` coinciden con el rango de *train*.

### 8.4 Cómo cambiar periodo o universo

- **Fechas**: edita los campos `segments` (train/valid/test), `start_time`/`end_time` y
  `fit_*` en cada `.yaml`. Están parametrizados con Jinja
  (`{{ train_start | default("2008-01-01", true) }}`), así que puedes cambiar el `default`
  o pasar los valores por el scenario.
- **Universo / benchmark**: cambia `market: &market us` y `benchmark: &benchmark ^GSPC`
  (por ejemplo, a un universo SP500/NASDAQ propio si lo has construido con tus scripts de
  `prompts/`).
- Tras editar, si ejecutas desde `~/dev/RD-Agent`, sincroniza: `bash sync_rdagent.sh --to-wsl`.

> Nota: son **cinco** ficheros; si cambias el periodo, aplícalo en todos para mantener la
> coherencia entre las ramas de factores y de modelos.
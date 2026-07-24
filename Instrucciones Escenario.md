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
| `--loop_n N` | Nº de iteraciones del loop |
| `--step_n N` | Ejecuta solo N pasos |
| `--all_duration "2h"` | Presupuesto de tiempo total |
| `--path <sesión>` | Reanuda una sesión previa |
| `--checkout / --no-checkout` (`-c/-C`) | Reusar carpeta de logs limpiando o conservando |

```bash
rdagent fin_factor --loop-n 3
rdagent fin_factor --step-n 1
rdagent fin_factor --all_duration "2h"
rdagent fin_factor --path <sesión>
```

### Escenarios específicos

```bash
# fin_factor_report: carpeta de informes PDF
rdagent fin_factor_report --report-folder=git_ignore_folder/reports --loop_n 2

# general_model: URL o PDF de un paper (sin datos locales)
rdagent general_model "https://arxiv.org/pdf/2210.09789"

# data_science: competición + control de loop/tiempo
rdagent data_science --competition arf-12-hours-prediction-task --loop_n 5
```

`data_science` acepta además `--timeout`, `--step_n` y `--loop_n`.

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
rdagent fin_factor --loop_n 1
```

> Consejo: en la primera prueba de cualquier escenario, limita con `--loop_n 1` o
> `--all_duration "30m"` para controlar el coste de API antes de lanzar loops largos.


## 5. Copiar dentro del FileSystem de WSL

Utilizar el file system de Windows hace que vaya muy despacio

```bash
cp -r "/mnt/c/Users/trodriguez/src/RD-Agent/" ~/dev/
```
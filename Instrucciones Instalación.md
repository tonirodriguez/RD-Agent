# Instrucciones de Instalación — RD-Agent en WSL

Documento único para poner en marcha **RD-Agent** en el entorno **WSL (Ubuntu)** de esta máquina,
con **todos los escenarios** y el LLM configurado **íntegramente sobre OpenRouter**
(chat + embeddings con una sola API key).

Escenarios cubiertos: `fin_quant`, `fin_factor`, `fin_model`, `fin_factor_report`,
`general_model`, `data_science`.

---

## 1. Requisitos y estado del entorno

| Requisito | Estado | Nota |
|---|---|---|
| Sistema operativo | ✅ WSL Ubuntu | RD-Agent solo soporta Linux |
| Python | ✅ 3.10.12 | Probado en 3.10 / 3.11 |
| Instalación pip | ⚠️ Por hacer | En un venv, con `pip install -e .` |
| **Docker** | ❓ **Verificar** | **OBLIGATORIO en los 6 escenarios**, debe correr **sin `sudo`** |
| LLM (`.env`) | ✅ Configurado | OpenRouter → DeepSeek V4 Flash (chat) + embeddings |
| Datos qlib | ➖ Automáticos | Se descargan en la 1ª ejecución de `fin_*` (a `~/.qlib`) |
| Datos `data_science` | ⚙️ Script | Los prepara `setup_wsl.sh --with-data` |

> **Clave:** todos los escenarios ejecutan el código generado dentro de contenedores Docker.
> Si Docker no funciona **sin `sudo`**, no arranca ninguno.

---

## 2. Instalación (una sola vez)

Desde la raíz del repo, en tu terminal WSL:

```bash
bash setup_wsl.sh --with-data
```

El script:
- Crea el entorno virtual `.venv` e instala `rdagent` en modo editable.
- Verifica Docker y `.env`.
- Crea `git_ignore_folder/reports` y `git_ignore_folder/ds_data` y fija `DS_LOCAL_DATA_PATH`.
- Con `--with-data`, descarga los datasets de ejemplo (informes PDF + dataset ARF-12h).

Instalación manual equivalente (si prefieres no usar el script):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e . -c constraints/3.10.txt
```

> **Usa Python 3.10 o 3.11** (RD-Agent no está probado en 3.12; da fallos de dependencias).

> ⚠️ **Fijar `pydantic-ai` a la serie 1.x (obligatorio).** El repo deja `pydantic-ai-slim`
> sin versión y pip instala la 2.x, que rehízo la API de MCP y elimina
> `MCPServerStreamableHTTP` → error `ImportError: cannot import name 'MCPServerStreamableHTTP'`.
> Tras instalar, ejecuta:
>
> ```bash
> pip install "pydantic-ai-slim[mcp,openai,prefect]<2"
> python -c "from pydantic_ai.mcp import MCPServerStreamableHTTP; print('OK')"
> ```
>
> (Recomendado: fija también `pydantic-ai-slim[mcp,openai,prefect]<2` en `requirements.txt`.)

> En **cada nueva terminal** activa el entorno antes de usar rdagent:
> `source .venv/bin/activate`

---

## 3. Docker (obligatorio)

Comprueba que funciona **sin sudo**:

```bash
docker run hello-world
```

- **Docker Desktop** (Windows): *Settings → Resources → WSL Integration* → activa tu distro y reinicia la terminal.
- **Docker nativo en WSL**: `sudo usermod -aG docker $USER`, cierra y reabre la terminal.

---

## 4. Configuración del LLM (OpenRouter)

Todo va por OpenRouter con **una sola clave**. En `.env`:

```bash
# CHAT: DeepSeek V4 Flash (soporte nativo de OpenRouter en LiteLLM)
CHAT_MODEL="openrouter/deepseek/deepseek-v4-flash"
OPENROUTER_API_KEY="<TU_OPENROUTER_API_KEY>"

# EMBEDDING: enrutado por OpenRouter (endpoint compatible con OpenAI)
EMBEDDING_MODEL="litellm_proxy/openai/text-embedding-3-small"
LITELLM_PROXY_API_KEY="<TU_OPENROUTER_API_KEY>"
LITELLM_PROXY_API_BASE="https://openrouter.ai/api/v1"
```

**Pega tu clave de OpenRouter en las dos variables** (`OPENROUTER_API_KEY` y
`LITELLM_PROXY_API_KEY`), con el mismo valor.

Detalles:
- El chat usa el prefijo nativo `openrouter/`. El embedding usa `litellm_proxy/`
  apuntando a `https://openrouter.ai/api/v1`, porque LiteLLM no enruta embeddings
  por el prefijo `openrouter/`.
- Si DeepSeek devuelve etiquetas `<think>`, descomenta `REASONING_THINK_RM=True`.

### Modelos de embedding alternativos en OpenRouter

| Modelo (valor de `EMBEDDING_MODEL`) | Precio aprox. | Cuándo usarlo |
|---|---|---|
| `litellm_proxy/openai/text-embedding-3-small` | $0.02/M | **Por defecto**, probado con RD-Agent |
| `litellm_proxy/qwen/qwen3-embedding-8b` | $0.01/M | Más calidad por menos coste (algo más lento) |
| `litellm_proxy/baai/bge-m3` | $0.01/M | Multilingüe (útil si hay español) |
| `litellm_proxy/google/gemini-embedding-001` | $0.15/M | Máxima calidad, más caro |

> Si cambias de modelo de embedding tras haber ejecutado loops, limpia `pickle_cache/`
> para no mezclar vectores de dimensiones distintas.

---

## 5. Validación (antes de correr nada)

> ⚠️ **Importante con OpenRouter:** el comando `rdagent health_check` **no reconoce
> OpenRouter**. Su `env_check` solo contempla `DEEPSEEK_API_KEY` o `OPENAI_API_KEY`, así
> que con nuestra config (`OPENROUTER_API_KEY` + `LITELLM_PROXY_API_KEY`) muestra
> *"No valid configuration was found"* y falla con `UnboundLocalError`. Es una limitación
> del checker, **no** de tu `.env`: el runtime de RD-Agent sí lee `OPENROUTER_API_KEY`.

### 5.1 Verifica Docker + puertos (sin la parte de LLM)

```bash
source .venv/bin/activate
rdagent health_check --no-check-env
```

### 5.2 Verifica el LLM directamente con LiteLLM (chat + embedding por OpenRouter)

Esta es la prueba **autoritativa** del LLM, ya que es lo que RD-Agent usa por debajo:

```bash
cd /home/toni/src/RD-Agent      # ajusta a tu ruta del repo
source .venv/bin/activate
python - <<'PY'
import os, litellm
from dotenv import load_dotenv
load_dotenv(".env")
r = litellm.completion(model=os.getenv("CHAT_MODEL"),
                       messages=[{"role":"user","content":"Say hi"}])
print("CHAT OK:", r.choices[0].message.content[:60])
e = litellm.embedding(model=os.getenv("EMBEDDING_MODEL"),
                      input=["hello world"],
                      api_key=os.getenv("LITELLM_PROXY_API_KEY"),
                      api_base=os.getenv("LITELLM_PROXY_API_BASE"))
print("EMBED OK, dim:", len(e.data[0]["embedding"]))
PY
```

Si imprime `CHAT OK` y `EMBED OK`, la configuración funciona y puedes lanzar escenarios.

### 5.3 (Opcional) Hacer que `rdagent health_check` pase en verde

Si quieres que el checker oficial valide sin error, añade a `.env` la variable
`DEEPSEEK_API_KEY` con **el mismo valor de tu clave de OpenRouter**. Así `env_check` entra
por su rama DeepSeek (chat con tu `CHAT_MODEL=openrouter/...` + esa key, embedding por
`LITELLM_PROXY_*`). Es solo para contentar al checker; el runtime sigue usando
`OPENROUTER_API_KEY`.

---

## 6. Ejecución de los escenarios

> Activa siempre el entorno primero: `source .venv/bin/activate`.
> La 1ª ejecución de cualquier escenario `fin_*` descarga los datos de qlib a `~/.qlib`
> (dentro de Docker); puede tardar varios minutos.

### 6.1 `fin_quant` — factores + modelos (loop conjunto)
```bash
rdagent fin_quant
```
Sin datos extra.

### 6.2 `fin_factor` — solo factores
```bash
rdagent fin_factor
```
Sin datos extra.

### 6.3 `fin_model` — solo modelos
```bash
rdagent fin_model
```
Sin datos extra.

### 6.4 `fin_factor_report` — factores desde informes financieros (PDF)
Necesita una carpeta con PDFs (descargada por `setup_wsl.sh --with-data`). Manual:
```bash
wget https://github.com/SunsetWolf/rdagent_resource/releases/download/reports/all_reports.zip
unzip all_reports.zip -d git_ignore_folder/reports
```
Ejecutar:
```bash
rdagent fin_factor_report --report-folder=git_ignore_folder/reports
```
Puedes apuntar `--report-folder` a tu propia carpeta de PDFs.

### 6.5 `general_model` — modelo a partir de un paper (URL o PDF)
No necesita datos locales, solo Docker:
```bash
rdagent general_model "https://arxiv.org/pdf/2210.09789"
# o un PDF local:
rdagent general_model /ruta/a/tu/paper.pdf
```

### 6.6 `data_science` — competición / ML

**Modo dataset local (por defecto, ejemplo ARF-12h — NO Kaggle).**
Variables `DS_` ya configuradas en `.env`. Dataset descargado por el script; manual:
```bash
wget https://github.com/SunsetWolf/rdagent_resource/releases/download/ds_data/arf-12-hours-prediction-task.zip
unzip arf-12-hours-prediction-task.zip -d ./git_ignore_folder/ds_data/
```
Ejecutar:
```bash
rdagent data_science --competition arf-12-hours-prediction-task
```

**Modo Kaggle (competiciones reales).** En `.env` cambia:
```bash
DS_SCEN="rdagent.scenarios.data_science.scen.KaggleScen"
DS_IF_USING_MLE_DATA=True
DS_SAMPLE_DATA_BY_LLM=True
```
Configura la API de Kaggle y únete a la competición en la web:
```bash
mkdir -p ~/.config/kaggle
# copia kaggle.json (Kaggle > Settings > Create New Token) a ~/.config/kaggle/
chmod 600 ~/.config/kaggle/kaggle.json
rdagent data_science --competition tabular-playground-series-dec-2021
```

---

## 7. Monitorizar resultados (interfaz web)

En otra terminal (con el entorno activado):

```bash
rdagent ui --port 19899 --log-dir "log/"                 # escenarios fin_*
rdagent ui --port 19899 --log-dir "log/" --data-science  # escenario data_science
```

Abre **http://localhost:19899**

---

## 8. Resumen de comandos (arranque rápido)

```bash
# 1. Instalar y preparar datos
bash setup_wsl.sh --with-data

# 2. Pegar la OpenRouter API key en .env (OPENROUTER_API_KEY y LITELLM_PROXY_API_KEY)

# 3. Fijar pydantic-ai a la 1.x (evita el ImportError de MCP)
pip install "pydantic-ai-slim[mcp,openai,prefect]<2"

# 4. Activar entorno y validar (health_check NO soporta OpenRouter → ver §5)
source .venv/bin/activate
rdagent health_check --no-check-env          # Docker + puertos
#   y valida el LLM con el script de LiteLLM del §5.2

# 5. Lanzar cualquier escenario
rdagent fin_quant
rdagent fin_factor
rdagent fin_model
rdagent fin_factor_report --report-folder=git_ignore_folder/reports
rdagent general_model "https://arxiv.org/pdf/2210.09789"
rdagent data_science --competition arf-12-hours-prediction-task
```

---

## 9. Problemas frecuentes

- **`rdagent: command not found`** → falta activar el venv: `source .venv/bin/activate`.
- **`ImportError: cannot import name 'MCPServerStreamableHTTP'`** → `pydantic-ai` 2.x instalado;
  fija la 1.x: `pip install "pydantic-ai-slim[mcp,openai,prefect]<2"` (ver §2).
- **`health_check` → "No valid configuration was found" + `UnboundLocalError`** → el checker no
  soporta OpenRouter. Usa `rdagent health_check --no-check-env` + el script de LiteLLM del §5.2.
  (Opcional: añade `DEEPSEEK_API_KEY=<tu key de OpenRouter>` para que pase en verde, §5.3.)
- **Docker permission denied** → no estás en el grupo `docker` o falta la integración WSL (§3).
- **Error de embedding en la prueba LiteLLM** → revisa que la clave esté en `LITELLM_PROXY_API_KEY`
  y que `LITELLM_PROXY_API_BASE="https://openrouter.ai/api/v1"`.
- **`MlflowException: filesystem tracking backend ... maintenance mode`** (backtest de qlib
  falla con `No result file found`) → mlflow reciente rechaza el file store. Añade a `.env`
  `MLFLOW_ALLOW_FILE_STORE=true` (se propaga a `qrun` vía `os.environ`); o `export` en la shell.
- **`TypeError: bad argument type for built-in operation`** en la UI → watcher de Streamlit +
  torch; pon `fileWatcherType = "none"` en `.streamlit/config.toml` o
  `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none` al lanzar `rdagent ui`.
- **Coste de API** → cada loop hace muchas llamadas; puedes activar caché en `.env`
  (`USE_CHAT_CACHE=True`, `USE_EMBEDDING_CACHE=True`).
- **Datos qlib tardan** → es normal en la primera ejecución de `fin_*`; se cachean en `~/.qlib`.

---

## 10. Referencias

- Repo: https://github.com/microsoft/RD-Agent
- Documentación: https://rdagent.readthedocs.io
- Modelos DeepSeek en OpenRouter: https://openrouter.ai/deepseek
- Embeddings en OpenRouter: https://openrouter.ai/collections/embedding-models

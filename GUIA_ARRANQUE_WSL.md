# Guía de arranque de RD-Agent en WSL — los 6 escenarios

Cubre: **fin_quant**, **fin_factor**, **fin_model**, **fin_factor_report**,
**general_model** y **data_science**. Todos los comandos se ejecutan **dentro de tu WSL**,
desde la raíz del repo, con el entorno activado (`source .venv/bin/activate`).

---

## 0. Requisitos comunes

| Requisito | Estado | Nota |
|---|---|---|
| SO | ✅ WSL Ubuntu | RD-Agent solo soporta Linux |
| Python | ✅ 3.10.12 | Probado en 3.10 / 3.11 |
| **Docker** | ❓ **Verificar** | **OBLIGATORIO en los 6 escenarios**, debe correr **sin `sudo`** |
| LLM (`.env`) | ✅ OpenRouter | Chat + embeddings vía OpenRouter (una sola API key) |

**Todos** los escenarios ejecutan el código generado dentro de contenedores Docker.
Sin Docker sin `sudo`, no arranca ninguno.

---

## 1. Instalación (una sola vez)

```bash
bash setup_wsl.sh --with-data
```

- Sin `--with-data`: instala rdagent, verifica Docker/`.env` y crea las carpetas de datos.
- Con `--with-data`: además descarga los datasets de ejemplo (informes + arf-12h).

Luego, **pega tu OpenRouter API key** en `.env` (dos variables, mismo valor):
`OPENROUTER_API_KEY` y `LITELLM_PROXY_API_KEY`.

En cada nueva terminal: `source .venv/bin/activate`

---

## 2. Docker

```bash
docker run hello-world   # debe funcionar SIN sudo
```
Docker Desktop → *Settings → Resources → WSL Integration* → activa tu distro. O bien,
Docker nativo: `sudo usermod -aG docker $USER` y reabre la terminal.

---

## 3. Health check (antes de correr nada)

```bash
source .venv/bin/activate
rdagent health_check
```
Verifica Docker + puertos + acceso a chat y embedding. Para saltar comprobaciones:
`rdagent health_check --no-check-env` (salta el LLM) o `--no-check-docker`.

---

## 4. Los 6 escenarios

> Recuerda: `source .venv/bin/activate` en cada terminal.
> La 1ª ejecución de cualquier escenario `fin_*` descarga los datos de qlib a `~/.qlib`
> (dentro de Docker); puede tardar varios minutos.

### 4.1 fin_quant — factores + modelos (loop conjunto)
```bash
rdagent fin_quant
```
Sin datos extra. Solo Docker + qlib (automático).

### 4.2 fin_factor — solo factores
```bash
rdagent fin_factor
```
Sin datos extra.

### 4.3 fin_model — solo modelos
```bash
rdagent fin_model
```
Sin datos extra.

### 4.4 fin_factor_report — factores desde informes financieros (PDF)
Necesita una carpeta con PDFs. `setup_wsl.sh --with-data` ya los descarga en
`git_ignore_folder/reports`. Descarga manual si hace falta:
```bash
wget https://github.com/SunsetWolf/rdagent_resource/releases/download/reports/all_reports.zip
unzip all_reports.zip -d git_ignore_folder/reports
```
Ejecutar:
```bash
rdagent fin_factor_report --report-folder=git_ignore_folder/reports
```
(Puedes apuntar `--report-folder` a tu propia carpeta de PDFs.)

### 4.5 general_model — modelo desde un paper (URL o PDF)
No necesita datos locales, solo Docker. Le pasas la URL/ruta de un paper PDF:
```bash
rdagent general_model "https://arxiv.org/pdf/2210.09789"
# o un PDF local:
rdagent general_model /ruta/a/tu/paper.pdf
```

### 4.6 data_science — competición / ML
**Modo dataset local (por defecto, ejemplo ARF 12h — NO Kaggle):**
Variables `DS_` ya configuradas en `.env` (`DS_SCEN=...DataScienceScen`,
`DS_IF_USING_MLE_DATA=False`, etc.) y `DS_LOCAL_DATA_PATH` fijado por el script.
`setup_wsl.sh --with-data` ya descarga el dataset. Manual:
```bash
wget https://github.com/SunsetWolf/rdagent_resource/releases/download/ds_data/arf-12-hours-prediction-task.zip
unzip arf-12-hours-prediction-task.zip -d ./git_ignore_folder/ds_data/
```
Ejecutar:
```bash
rdagent data_science --competition arf-12-hours-prediction-task
```

**Modo Kaggle** (competiciones reales). En `.env` cambia a:
`DS_SCEN=...KaggleScen`, `DS_IF_USING_MLE_DATA=True`, `DS_SAMPLE_DATA_BY_LLM=True`.
Configura la API de Kaggle:
```bash
mkdir -p ~/.config/kaggle
# copia tu kaggle.json (Kaggle > Settings > Create New Token) a ~/.config/kaggle/
chmod 600 ~/.config/kaggle/kaggle.json
```
Únete a la competición en la web y luego:
```bash
rdagent data_science --competition tabular-playground-series-dec-2021
```

---

## 5. Monitorizar resultados (UI)

En otra terminal (venv activado):
```bash
rdagent ui --port 19899 --log-dir "log/"                 # escenarios fin_*
rdagent ui --port 19899 --log-dir "log/" --data-science  # data_science
```
Abre http://localhost:19899

---

## 6. Configuración LLM actual (.env)

- **Chat**: `openrouter/deepseek/deepseek-v4-flash` (OpenRouter, nativo LiteLLM).
- **Embeddings**: `litellm_proxy/openai/text-embedding-3-small` vía
  `https://openrouter.ai/api/v1` (OpenRouter, endpoint compatible OpenAI).
- Una sola clave de OpenRouter en `OPENROUTER_API_KEY` y `LITELLM_PROXY_API_KEY`.

Notas:
- Si DeepSeek devuelve etiquetas `<think>`, descomenta `REASONING_THINK_RM=True`.
- Si cambias de modelo de embedding, limpia `pickle_cache/` para no mezclar vectores.

---

## 7. Problemas frecuentes

- **`rdagent: command not found`** → falta `source .venv/bin/activate`.
- **Docker permission denied** → no estás en el grupo `docker` o falta integración WSL (§2).
- **Error de embedding en health_check** → revisa que la key esté en `LITELLM_PROXY_API_KEY`
  y `LITELLM_PROXY_API_BASE="https://openrouter.ai/api/v1"`.
- **Coste de API**: cada loop hace muchas llamadas. Puedes activar caché en `.env`
  (`USE_CHAT_CACHE=True`, `USE_EMBEDDING_CACHE=True`).

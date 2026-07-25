# Tutorial de RD-Agent — de cero a tu primer ciclo de I+D cuantitativa

Tutorial práctico para aprender a trabajar con **RD-Agent** en **tu entorno**
(WSL + OpenRouter + datos US, escenario `fin_quant`). Combina conceptos y práctica.
Complementa a `Instrucciones Instalación.md` y `Instrucciones Escenario.md`.

---

## 1. ¿Qué es RD-Agent y qué problema resuelve?

RD-Agent automatiza el ciclo de **Investigación y Desarrollo (I+D)** que normalmente hace
un investigador cuantitativo: proponer una idea, implementarla en código, backtestearla y
aprender del resultado para proponer la siguiente. Un LLM (en tu caso DeepSeek V4 Flash vía
OpenRouter) hace de "investigador"; qlib hace de "laboratorio" donde se prueban las ideas.

La idea central es el **loop evolutivo**: RD-Agent no da una respuesta única, sino que
**itera** mejorando factores y modelos vuelta a vuelta, guiado por los resultados de backtest.

> Contexto: en el paper de Microsoft, RD-Agent(Q) logra ~2× de retorno anualizado frente a
> librerías de factores de referencia usando 70% menos factores, con un coste < $10 por
> experimento. El coste depende del modelo LLM que uses.

---

## 2. Conceptos clave

- **Factor**: una señal predictiva calculada a partir de datos de mercado (p. ej. "momentum
  a 20 días"). Es *feature engineering* cuantitativo.
- **Modelo**: el algoritmo que combina factores para predecir retornos (GBDT/LightGBM, redes
  neuronales, etc.).
- **Hipótesis**: la idea que el agente propone en cada vuelta ("añadir un factor de
  volatilidad mejorará el Sharpe"). Es el motor del loop.
- **Backtest**: simulación histórica de la estrategia sobre los datos (qlib), que devuelve
  métricas como IC, retorno anualizado y Sharpe.
- **Traza (trace)**: el historial de hipótesis/experimentos de una ejecución. RD-Agent
  recuerda el mejor resultado hasta la fecha (**SOTA**) y construye sobre él.

---

## 3. El loop de RD-Agent (arquitectura mental)

Cada iteración tiene cuatro fases:

```
   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
   │  1. PROPOSE  │──▶│  2. CODING   │──▶│  3. RUNNING  │──▶│ 4. FEEDBACK  │
   │  (hipótesis) │   │ (implementa  │   │  (backtest   │   │ (evalúa y     │
   │   el LLM     │   │  factor/     │   │   en qlib,   │   │  decide la    │
   │   propone)   │   │  modelo)     │   │   Docker)    │   │  siguiente)   │
   └──────────────┘   └──────────────┘   └──────────────┘   └──────▲───────┘
          ▲                                                         │
          └─────────────────────  siguiente vuelta  ───────────────┘
```

- **Propose**: el LLM lee el estado de la traza y propone una hipótesis (nuevo factor o
  cambio de modelo).
- **Coding**: el LLM escribe el código del factor/modelo (CoSTEER: implementa + auto-corrige).
- **Running**: RD-Agent ejecuta el backtest dentro del contenedor `local_qlib` (`qrun`).
- **Feedback**: compara con el SOTA, guarda si mejora, y alimenta la siguiente hipótesis.

En `fin_quant` el loop **alterna** ramas de factores y de modelos (co-optimización).

---

## 4. Tu configuración (resumen)

- **LLM**: OpenRouter → `openrouter/deepseek/deepseek-v4-flash` (chat) + embeddings por
  OpenRouter. Una sola API key. (Detalles en `Instrucciones Instalación.md §4`.)
- **Datos**: US (`~/.qlib/qlib_data/us_data`), benchmark **S&P 500 (^GSPC)**. Las 5
  plantillas de qlib ya están en US. (Ver `Instrucciones Escenario.md §7-§8`.)
- **Ejecución**: en WSL, desde `~/dev/RD-Agent`, con Docker sin `sudo`.

### 4.1 ¿Hace falta GPU?

**No.** RD-Agent funciona perfectamente sin GPU:

- **El LLM no usa GPU local** — la inferencia (DeepSeek V4 Flash) ocurre en OpenRouter.
- **La GPU solo la usarían algunos modelos de qlib en el backtest**:
  - `LGBModel` (LightGBM/GBDT), en `conf_baseline` y `conf_combined_factors` → **CPU** siempre.
  - `GeneralPTNN` (red neuronal PyTorch), en las otras 3 plantillas → puede usar GPU
    (`GPU: 0` en sus kwargs), pero **cae a CPU automáticamente** si no hay CUDA.
- En `env.py`, `enable_gpu = True` con la lógica de *"desactivar GPU si no está disponible"*.

La única diferencia sin GPU es la **velocidad**: las iteraciones con red neuronal son más
lentas en CPU; las de LightGBM van igual. Para forzar CPU explícitamente:
`export CUDA_VISIBLE_DEVICES=""` antes de lanzar.

---

## 5. Práctica guiada — tu primer ciclo

### Paso 0 — Preparar la sesión
```bash
cd /home/toni/dev/RD-Agent
source .venv/bin/activate
docker run hello-world          # Docker OK sin sudo
df -h /                         # ~10-15 GB libres
```

### Paso 1 — Validar el LLM (no uses `health_check` con OpenRouter)
Usa el script de LiteLLM de `Instrucciones Instalación.md §5.2`. Debe imprimir
`CHAT OK` y `EMBED OK`.

### Paso 2 — Asegurar los datos US
```bash
ls ~/.qlib/qlib_data/us_data/{instruments,calendars,features} 2>/dev/null && echo "US data OK"
# Si no existen, constrúyelos con tus scripts:
bash prompts/update_us_qlib_rebuild.sh
```

### Paso 3 — Primera ejecución corta (valida toda la cadena)
```bash
rdagent fin_quant --loop-n 1
```
La primera vez construye la imagen Docker y prepara datos: **tarda**, es normal. Cuando
complete una vuelta con backtest, el pipeline funciona.

### Paso 4 — Ver resultados en la UI (en otra terminal)
```bash
cd /home/toni/dev/RD-Agent      # desde donde lanzaste fin_quant
source .venv/bin/activate
STREAMLIT_SERVER_FILE_WATCHER_TYPE=none rdagent ui --port 19899 --log-dir "log/"
```
**Importante:** `--log-dir` apunta a la carpeta **padre `log/`** (NO a la carpeta con
timestamp). En la UI, abre el desplegable **"Select from `log/`"** y elige la carpeta con
timestamp de tu run. Si apuntas directamente a `log/<timestamp>/`, el desplegable solo
mostrará plantillas como `debug_tpl` y no verás resultados.

Cada ejecución crea su carpeta `log/<timestamp>/`. El run "completo" es el que **más
ficheros/subcarpetas** tiene (los que fallaron pronto tienen muy pocos). Para identificarlo:
```bash
for d in log/2026-*/; do echo "$(find "$d" -type f | wc -l) ficheros  $d"; done | sort -n
```
Abre http://localhost:19899. No hace falta esperar al final: la UI se puebla por pasos.

### Paso 5 — Ciclo completo
```bash
rdagent fin_quant --loop-n 10          # por iteraciones
rdagent fin_quant --all-duration "3h"  # o por tiempo
```

### Paso 6 — Reanudar si se corta
```bash
rdagent fin_quant --path log/<timestamp>/__session__/<loop>/<step>
```

---

## 6. Cómo leer los resultados (métricas de backtest)

En la UI verás, por iteración: la hipótesis, el código generado y las métricas. Las más
importantes:

| Métrica | Qué mide | Interpretación rápida |
|---|---|---|
| **IC** (Information Coefficient) | Correlación entre predicción y retorno real | Más alto = mejor señal. >0.03-0.05 ya es útil |
| **ICIR** | IC ajustado por su estabilidad | Mide consistencia de la señal |
| **Annualized Return (ARR)** | Retorno anualizado de la estrategia | El objetivo a maximizar |
| **Sharpe** | Retorno ajustado por riesgo | >1 razonable; más alto mejor |
| **Max Drawdown** | Peor caída acumulada | Más cercano a 0 = menos riesgo |

La estrategia por defecto es `TopkDropoutStrategy` (top 50, drop 5): compra las 50 mejores
del universo y rota 5 cada periodo.

---

## 7. Cómo experimentar (qué tocar para aprender)

- **Periodo / universo**: edita `segments` (train/valid/test), `market` y `benchmark` en las
  5 plantillas `rdagent/scenarios/qlib/experiment/*/*.yaml` (ver `Instrucciones Escenario.md §8`).
- **Nº de iteraciones / tiempo**: flags `--loop-n`, `--all-duration`, `--step-n`.
- **Modelo LLM**: cambia `CHAT_MODEL` en `.env` (p. ej. a un modelo más barato para pruebas
  o uno más potente para calidad).
- **Otros escenarios**: prueba `fin_factor` (solo factores) o `fin_model` (solo modelos)
  para aislar cada rama; `general_model` para reproducir un paper.

Consejo de aprendizaje: empieza con `fin_factor --loop-n 1`, entiende una vuelta completa en
la UI (hipótesis → código → backtest), y solo después pasa a `fin_quant` con más iteraciones.

---

## 8. Problemas típicos (referencia rápida)

| Síntoma | Causa / solución |
|---|---|
| `ImportError: MCPServerStreamableHTTP` | `pydantic-ai` 2.x; fija `<2` (Instalación §2) |
| `health_check` "No valid configuration" | No soporta OpenRouter; valida con LiteLLM (Instalación §5) |
| Docker permission denied | Grupo `docker` / integración WSL (Instalación §3) |
| `TypeError: bad argument type...` en Streamlit | Watcher + torch; `fileWatcherType="none"` |
| `MlflowException: filesystem tracking backend...` / `No result file found` | mlflow rechaza file store; `MLFLOW_ALLOW_FILE_STORE=true` en `.env` |
| UI vacía / solo `debug_tpl` en el combo | Apunta `--log-dir` a la carpeta **padre `log/`** y elige el timestamp en el desplegable (no apuntes a `log/<timestamp>/`) |
| Disco lleno | Limpia `git_ignore_folder/RD-Agent_workspace/`, `docker system prune` |

---

## 9. Recursos oficiales

- **Documentación**: https://rdagent.readthedocs.io/
- **Escenario Quant**: https://rdagent.readthedocs.io/en/latest/scens/quant_agent_fin.html
- **Finance Data Agent**: https://rdagent.readthedocs.io/en/stable/scens/data_agent_fin.html
- **GitHub / README**: https://github.com/microsoft/RD-Agent
- **Informe técnico**: https://aka.ms/RD-Agent-Tech-Report
- **Demo en vivo**: https://rdagent.azurewebsites.net/
- **Qlib** (motor de backtest): https://github.com/microsoft/qlib

---

## 10. Ruta de aprendizaje sugerida

1. Lee §1-§3 de este tutorial para el modelo mental.
2. Haz `fin_factor --loop-n 1` y estudia esa vuelta en la UI.
3. Repite con `fin_model --loop-n 1` para ver la rama de modelos.
4. Lanza `fin_quant --loop-n 5` y observa la co-optimización factor+modelo.
5. Experimenta cambiando periodo/universo en las plantillas.
6. Profundiza con el informe técnico y la doc oficial del escenario Quant.

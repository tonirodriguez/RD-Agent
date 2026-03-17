Listed directory RD-Agent
Viewed README.md:1-506

Para realizar un experimento con **RD-Agent** orientado a **Quant** (Finanzas Cuantitativas), el repositorio oficial ya ofrece flujos de trabajo preconfigurados ("scenarios") especializados en iterar y evolucionar factores alfa y modelos predictivos, que conectan por debajo con **Qlib**.

Aquí tienes los pasos fundamentales para configurar y ejecutar un experimento Quant basándonos en la documentación del proyecto:

### 1. Configuración del Entorno Predictivo (Variables de Entorno)
Antes de lanzar el agente, RD-Agent necesita acceder a un modelo de lenguaje (LLM). Debes configurar el archivo **[.env](cci:7://file:///mnt/d/src/RD-Agent/.env:0:0-0:0)** en la raíz de tu proyecto ([/mnt/d/src/RD-Agent/.env](cci:7://file:///mnt/d/src/RD-Agent/.env:0:0-0:0)).

Ejemplo de configuración en [.env](cci:7://file:///mnt/d/src/RD-Agent/.env:0:0-0:0) usando OpenAI o modelos soportados vía LiteLLM:
```bash
# Modelos 
CHAT_MODEL=gpt-4o  # El modelo principal de razonamiento
EMBEDDING_MODEL=text-embedding-3-small

# Credenciales
OPENAI_API_KEY=<tu_api_key_aqui>
# OPENAI_API_BASE=<si_usas_base_personalizada_u_otro_proveedor>
```
*(Nota: RD-Agent permite configurar DeepSeek, Azure, y proveedores mediante LiteLLM si lo prefieres. Recuerda siempre revisar tu archivo [.env](cci:7://file:///mnt/d/src/RD-Agent/.env:0:0-0:0)).*

---

### 2. Ejecutar el Experimento Quant
RD-Agent dispone de comandos específicos para lanzar distintos bucles automatizados (loops de R&D) en el ámbito cuantitativo. Abre tu terminal, asegúrate de tener tu entorno activado (ej. `conda activate rdagent`) y ejecuta uno de los siguientes:

**A. Evolución Conjunta (Factores + Modelo)**
Si quieres que el agente proponga e implemente tanto factores (alphas) como código de modelos, ejecuta:
```bash
rdagent fin_quant
```
*Este es el experimento más completo. El agente analizará los datos, programará nuevos factores, entrenará un modelo de Machine Learning en Qlib y observará las métricas para seguir mejorando de manera cíclica.*

**B. Evolución Únicamente de Factores (Alpha Mining)**
Si sólo quieres que el agente invente, programe y valide nuevos factores técnicos:
```bash
rdagent fin_factor
```

**C. Evolución Únicamente del Modelo**
Si quieres que mantenga los factores fijos pero itere proponiendo diferentes arquitecturas de modelos de ML:
```bash
rdagent fin_model
```

**D. Extracción de Factores desde Reportes Financieros**
El agente puede leer texto de PDFs de investigación financiera y programar los factores que descubra allí:
```bash
rdagent fin_factor_report --report-folder=<Ruta_a_la_carpeta_con_pdfs>
```

---

### 3. Visualizar los Resultados y Métricas del Experimento
RD-Agent incluye una interfaz web (UI) donde puedes ver en tiempo real el log del experimento, qué factores/modelos está programando el agente y cómo rinden probabilísticamente.

Mientras el experimento de arriba corre (o cuando termine), puedes lanzar la interfaz gráfica:
```bash
rdagent ui --port 19899 --log-dir log/
```
Posteriormente, abre en tu navegador web `http://localhost:19899` para ver todo el rastro de la ejecución, el rendimiento iterativo del PnL/Information Ratio (IR) logrado en el entorno Qlib y el "razonamiento" o código generado paso a paso por el agente.

### 4. ¿Qué ocurre internamente?
Durante estos comandos, el sistema arranca **R&D-Agent-Quant (RD-Agent (Q))**, que utilizará una estructura compuesta por un agente *"Investigador"* (o3/GPT) para formular hipótesis matemáticas y un agente *"Desarrollador"* que traducirá esa fórmula en Python compatible con las interfaces `DataHandler` o `Model` de Qlib. Luego lo evaluará y retroalimentará su base de conocimiento con el log de errores o ganancias.


    > ¿Los valores de Qlib siempre están normalizados? Es eso correcto? No se corresponden con los valores reales de cotización de las acciones

Listed directory scenarios
Searched for "market"
Viewed conf_baseline.yaml:1-96
Viewed conf_sota_factors_model.yaml:1-120
Viewed conf_baseline_factors_model.yaml:1-100
Searched for "csi300"
Searched for "csi300"

¡Buenas noticias! A diferencia de los tutoriales estándar de Qlib (que suelen usar el mercado chino `csi300` y `cn_data` por defecto), **los escenarios de Quant de RD-Agent ya vienen configurados por defecto para atacar al mercado de Estados Unidos (US).**

Si revisamos el código fuente interno de los templates de experimentación de RD-Agent (por ejemplo, en [rdagent/scenarios/qlib/experiment/factor_template/conf_baseline.yaml](cci:7://file:///mnt/d/src/RD-Agent/rdagent/scenarios/qlib/experiment/factor_template/conf_baseline.yaml:0:0-0:0) o en las configuraciones de modelos), la inicialización base que utiliza el agente es la siguiente:

```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/us_data"
    region: us

market: &market us
benchmark: &benchmark ^GSPC  # S&P 500
```

Como ves:
- Utiliza la región **US**.
- Busca los datos locales por defecto en `~/.qlib/qlib_data/us_data` (que se descargan automáticamente si ejecutas los scripts de preparación).
- Utiliza el mercado de acciones **US**.
- Se compara contra el benchmark **^GSPC** (S&P 500).

### ¿Cómo cambiar el mercado si alguna vez lo necesitas (ej. para volver a CN)?
Si en algún momento deseas modificar el mercado o el benchmark contra el que el Agente itera (ya sea a China, Europa, o un índice de US distinto como el NASDAQ `^NDX`), debes alterar las plantillas base YAML (.yaml) que usa el framework para construir las tareas de Qlib.

Estas plantillas las encontrarás dentro del código fuente de `RD-Agent` en estas dos carpetas:
1. `rdagent/scenarios/qlib/experiment/factor_template/` *(para los loops de factores)*
2. `rdagent/scenarios/qlib/experiment/model_template/` *(para los loops de modelos)*

Dentro de los archivos como `conf_baseline.yaml` o `conf_baseline_factors_model.yaml`, solo tendrías que cambiar las 4 primeras líneas. Por ejemplo, para pasarlo al mercado Chino (`CSI300`), lo reemplazarías por:

```yaml
qlib_init:
    provider_uri: "~/.qlib/qlib_data/cn_data"
    region: cn

market: &market csi300
benchmark: &benchmark SH000300
```

Pero para responder directamente a tu pregunta: **no tienes que hacer nada para el mercado US**, RD-Agent ya está evaluando a los agentes matemáticos contra el mercado estadounidense en todos sus escenarios Quant oficiales.

    > ¿Como puedo visualizar el resultado de los experimentos realizados

Investigating how to visualize experiment results.

Viewed read_exp_res.py:1-56

Para visualizar los resultados de los experimentos realizados por RD-Agent, tienes tres vías principales, dependiendo del nivel de detalle técnico que estés buscando:

### 1. La Interfaz Web en tiempo real (RD-Agent UI)
Es la forma más sencilla de ver todo el flujo de razonamiento y el éxito de cada iteración del experimento. Guarda todo el historial de los factores/modelos creados.
```bash
rdagent ui --port 19899 --log-dir log/
```
*(Si no modificaste el directorio de logs, estará en la ruta de arranque. Luego abre `http://localhost:19899` en el navegador).*
Aquí podrás ver:
* El log de ejecución: Las hipótesis de factores de IA que inventó el nodo Investigador.
* El código final de ML y Features programados en Qlib.
* Un resumen de las métricas obtenidas (Annualized Return, Information Ratio, etc) por cada factor que fue evaluado.

### 2. Extracción programática (Script Qlib Recorder)
RD-Agent corre Qlib por debajo, así que todas las predicciones y métricas de backtest se guardan automáticamente (normalmente gestionadas por `mlflow` en segundo plano).
En tus archivos precisamente tienes un script de ejemplo ya construido para esto: `/mnt/d/src/RD-Agent/rdagent/scenarios/qlib/experiment/model_template/read_exp_res.py`.

Si ejecutas ese script:
```bash
python rdagent/scenarios/qlib/experiment/model_template/read_exp_res.py
```
El script buscará en todos los experimentos tu **último Tracker/Recorder**, y generará:
1. `qlib_res.csv`: Un archivo CSV con todas las métricas finales agrupadas del backtesting (sharpe ratio global, rendimientos máximos, drawdown).
2. `ret.pkl`: Un objeto DataFrame pkl que contiene la **curva de retornos diaria** (el valor del portafolio día a día).

### 3. Visualización de gráficas de Portafolio interactivo
Si utilizaste el script anterior y ya tienes tu DataFrame `ret.pkl`, puedes usar otra libreta (Jupyter Notebook) e importar las herramientas de graficado internas de Qlib (que utilizan pandas y matplotlib/plotly internamente) para dibujar el PnL y el Drawdown contra el benchmark:

```python
import pandas as pd
from qlib.contrib.report import analysis_position

# 1. Cargamos los resultados de retorno guardados
portfolio_df = pd.read_pickle("ret.pkl")

# 2. Generamos el resumen estadístico o directamente las gráficas 
# (En un Jupyter Notebook esto te imprimirá visualmente todos los gráficos de tu estrategia)
analysis_position.report_graph(portfolio_df)
```

    > Hazme una propuesta de segmentación de los conjuntos de entramiento, validación y test según fechas para los experimentos en Qlib teniendo en cuenta que estamos en marzo de 2026. Haz una propuesta, pero no cambies ningún fichero.

Viewed conf_baseline_factors_model.yaml:1-100

Dado que estamos en marzo de 2026 y partimos de la configuración por defecto actual de Qlib en tu archivo [conf_baseline_factors_model.yaml](cci:7://file:///mnt/d/src/RD-Agent/rdagent/scenarios/qlib/experiment/model_template/conf_baseline_factors_model.yaml:0:0-0:0) (que usaba los rangos originales de 2008-2014 para entrenamiento, 2015-2016 para validación y 2017 en adelante para pruebas), la proporción de datos ha quedado muy desbalanceada (¡el set de test tiene ahora más de 9 años!).

Para entrenar con datos más recientes y mantener unas proporciones sólidas (aproximadamente 75% / 10% / 15% o similar), te propongo actualizar los rangos retrospectivamente desde el año actual.

Aquí tienes dos propuestas viables:

### Propuesta 1: Énfasis en datos recientes (Test de 2 años)
Si quieres probar cómo rinde el modelo estrictamente en el mercado post-pandemias/recuperación (probando en 2024–2026).
* **Train** (`train_start`, `train_end`): `"2008-01-01"` a `"2021-12-31"` (14 años de historia para que el modelo vea distintos ciclos alcistas/bajistas y recesiones).
* **Valid** (`valid_start`, `valid_end`): `"2022-01-01"` a `"2023-12-31"` (2 años que incluyen parte del rally tecnológico y subidas de tipos para afinar hiperparámetros).
* **Test** (`test_start`, `test_end`): `"2024-01-01"` a `"null"` (evaluación final a lo largo de 2024, 2025 y lo que llevamos de 2026).

_Esta sería mi recomendación principal porque te mantiene muy cerca del comportamiento real y actual del mercado al llevar el test al periodo justo anterior a la fecha actual._

### Propuesta 2: Distribución algo más conservadora (Test de 4 años)
Si prefieres un set de evaluación largo para garantizar mayor robustez y suavizar varianzas al calcular las métricas (Information Ratio, retornos anualizados, etc.):
* **Train** (`train_start`, `train_end`): `"2008-01-01"` a `"2019-12-31"` (12 años).
* **Valid** (`valid_start`, `valid_end`): `"2020-01-01"` a `"2021-12-31"` (2 años, que incluye el crash de COVID y la inyección de liquidez).
* **Test** (`test_start`, `test_end`): `"2022-01-01"` a `"null"` (4+ años de evaluación que combinan los años duros de inflación y las subidas actuales en la bolsa). 

Tal como has pedido, **no he realizado ninguna modificación** en tu fichero [conf_baseline_factors_model.yaml](cci:7://file:///mnt/d/src/RD-Agent/rdagent/scenarios/qlib/experiment/model_template/conf_baseline_factors_model.yaml:0:0-0:0). Cuando estés listo, puedes reemplazar los valores [default](cci:1://file:///mnt/d/src/qlib/scripts/data_collector/yahoo/collector.py:750:4-752:22) en la cabecera `data_handler_config` y en ``dataset > kwargs > segments`` con el enfoque que más te convenga.
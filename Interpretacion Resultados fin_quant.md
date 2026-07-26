# Interpretación de resultados de `fin_quant` y cómo llevarlos a tu qlib

Guía para leer los resultados de RD-Agent (`fin_quant`/`fin_factor`/`fin_model`), decidir si
un factor/modelo merece incorporarse, y operativizarlo en tu pipeline qlib.

---

## 1. Qué métricas obtienes

Las plantillas registran (vía `SigAnaRecord` + `PortAnaRecord`, estrategia `TopkDropoutStrategy`
topk 50 / n_drop 5, benchmark `^GSPC`, con **costes**: open 0.05% / close 0.15%). Cada
experimento produce un `qlib_res.csv` con:

**Calidad de la señal:**
- **IC / ICIR**: correlación media predicción-retorno y su estabilidad. IC > 0.03 útil;
  ICIR > 0.3-0.5 = consistente.
- **Rank IC / Rank ICIR**: versión por ranking (más robusta a outliers). La métrica que más
  miran los quants.

**Rendimiento de cartera (con y sin coste):**
- **annualized_return**
- **information_ratio** (el "Sharpe" del exceso sobre benchmark)
- **max_drawdown**

> Regla de oro: mira siempre las métricas **`with_cost`**. Un factor que solo funciona
> `without_cost` no sobrevive en real.

---

## 2. Cómo leer la evolución de los loops

RD-Agent guarda el **SOTA** (mejor hasta la fecha) y construye sobre él. En la UI, por loop:
hipótesis, código generado, métricas y feedback (si reemplazó al SOTA).

Qué buscar:
- **Tendencia, no picos**: ¿Rank IC / IR mejora de forma sostenida, o fue un salto puntual?
  Un único loop bueno suele ser suerte/overfitting.
- **Valid vs Test**: si brilla en validación y cae en test → sobreajuste.
- **Baseline**: compara contra `conf_baseline` (Alpha158 + LGBModel). Lo relevante es la
  **mejora marginal** sobre esa base.

---

## 3. Cómo decidir si lo incorporas

Para el candidato (normalmente el SOTA final):

- **¿Aporta IC más allá de lo existente?** Valida la contribución marginal controlando por
  tus factores actuales (RD-Agent deduplica, pero verifícalo tú).
- **¿Es robusto?** ICIR alto, IC estable en el tiempo, aguanta en test.
- **¿Sobrevive a costes/turnover?** `information_ratio with_cost` y drawdown razonables.
- **¿Tiene sentido económico?** Interpretable (momentum, calidad, liquidez...) > data-mining.

---

## 4. Cómo llevarlo a la práctica

**a) Localiza el artefacto ganador** — usa el script incluido:

```bash
cd ~/dev/RD-Agent
source .venv/bin/activate
python analyze_fin_quant_results.py            # tabla comparativa + ganador
python analyze_fin_quant_results.py --csv resumen_fin_quant.csv
```

Cada workspace contiene `factor.py`/`model.py`, el `conf.yaml` usado, `result.h5` (valores
del factor) y `qlib_res.csv` (métricas).

**b) Reimplementa el factor** en tu librería qlib (añádelo como feature/expresión junto a tu
handler Alpha158).

**c) Revalida de forma independiente** (lo más importante):
- Walk-forward / varias ventanas, no solo 2017→hoy.
- Tu universo (sp500) y **tus** costes reales.
- Sin look-ahead ni fuga temporal.

**d) Combínalo con tus factores**, reentrena el modelo y backtestea el conjunto. Importa la
mejora del **portfolio completo**, no el factor aislado.

**e) Paper-trading / monitorización** antes de real, vigilando que el IC live no se degrade.

---

## 5. Caveats

- El "SOTA" se basa en **un split de test**; fácil sobreajustar. La validación independiente
  es innegociable.
- 10 loops es exploración inicial, no una estrategia lista para producción.
- Un factor solo es tan bueno como tus datos US (los construiste con los scripts de `prompts/`).

---

## 6. El script `analyze_fin_quant_results.py`

Escanea `git_ignore_folder/RD-Agent_workspace`, lee cada `qlib_res.csv`, arma una tabla
comparativa ordenada cronológicamente (≈ orden de loops) y marca el ganador por
`information_ratio with_cost` (configurable con `--sort`). Si no reconoce los nombres de las
métricas de tu versión de qlib, imprime los índices crudos del primer `qlib_res.csv` para que
ajustes las cadenas de búsqueda.

Además imprime un **desglose por año** del ganador (exceso de retorno sobre benchmark, IR y
max drawdown anuales, a partir de `ret.pkl`), marcando 2020-2021 como COVID y calculando qué
% del exceso acumulado proviene de esos años.

```bash
python analyze_fin_quant_results.py --help
```

---

## 7. COVID y dependencia de régimen

El COVID (crash de feb-mar 2020 + recuperación 2020-2021) es una **ruptura estructural**:
correlaciones disparadas, factores que se invirtieron, y una recuperación muy concentrada en
mega-caps por el estímulo. Riesgo: que un factor "gane" por ajustar esas dinámicas
irrepetibles y **no generalice**.

**Decisión de diseño (aplicada en `.env`):** el COVID queda **dentro del train**
(split train 2016-2021 | valid 2022-2023 | test 2024→hoy), fuera de valid/test. Así **no
distorsiona la evaluación**: el modelo lo ve como escenario de estrés en el aprendizaje, pero
tus métricas de test se calculan sobre datos recientes limpios. No se borra 2020 (romper la
serie estropea lags/medias móviles y elimina un evento de estrés valioso).

**Cómo detectar dependencia del COVID:**

- **Desglose por año** (`analyze_fin_quant_results.py`): revela si el exceso de retorno se
  concentra en 2020-2021. **Ojo con el alcance**: `ret.pkl` cubre el periodo de *backtest*
  (el test). Con el split nuevo (test 2024+), el desglose NO incluye COVID; solo lo verás si
  el test abarca 2020-2021 (como en las ejecuciones con el split antiguo 2017→hoy).
- **Run de robustez**: reevalúa el factor entrenando sin feb-dic 2020. Si aguanta, es sólido.
- **Backtest sobre el COVID**: para estresar un factor a propósito, fija temporalmente el test
  a 2020-2021 (`QLIB_QUANT_TEST_START=2020-01-01`, `QLIB_QUANT_TEST_END=2021-12-31`) y mira si
  colapsa.
- **Feature de régimen/volatilidad** (VIX / vol realizada): permite al modelo condicionar en
  vez de promediar regímenes opuestos; suele ser mejor que borrar datos.

**Recomendación:** deja el COVID en train, y valida cualquier factor ganador con el desglose
por año + un run excluyendo 2020. Así separas los factores robustos de los que solo cabalgaron
la anomalía.

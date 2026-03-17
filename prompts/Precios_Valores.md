## Precios y Valores

    ¿Los valores de Qlib siempre están normalizados? Es eso correcto? No se corresponden con los valores reales de cotización de las acciones

Es correcto, aunque hay un matiz importante entre datos ajustados y datos normalizados estadísticamente. Lo que estás observando en Qlib se debe principalmente a dos razones:

### 1. Precios Ajustados (Adjusted Prices) vs. Precios Nominales (Raw)
Los datos base que utiliza Qlib (como *$close, $open, $high, $low*) **no son los precios nominales o "crudos"** que la acción tenía en su momento en el mercado. Son **precios ajustados** (generalmente backward-adjusted o forward-adjusted).

* **¿Por qué se ajustan?** Las empresas realizan operaciones corporativas (como desdoblamientos/splits de acciones o pagos de dividendos) que hacen que el precio nominal caiga abruptamente de un día para otro. Si usaras los precios nominales, un modelo de Machine Learning interpretaría una caída del 50% por un split como una "bajada en bolsa", lo cual es falso.

* **Consecuencia**: Para evitar que estos "saltos" artificiales arruinen los cálculos de rentabilidad, las series históricas de precios se alteran de forma retroactiva (ajuste). Por eso, el valor que extraes directamente de Qlib con D.features(..., ['$close']) casi nunca coincide con el valor histórico nominal de esa misma fecha.

### 2. Normalización Estadística de Features (Data Processors)
Si estás obteniendo los datos no a través de una simple consulta directa a la base de datos (con el módulo D), sino a través de un **Dataset** o un **DataHandler** en un flujo de trabajo (pipeline) de experimentación, es muy probable que los datos **estén completamente normalizados**.

Los modelos de inteligencia artificial en Qlib requieren que los datos (features) tengan medias centradas y varianzas controladas. Qlib suele aplicar por defecto en sus DataHandlers de ejemplo herramientas como:

* **Z-Score Scaling**: Restar la media y dividir por la desviación estándar.
* **CSZScoreNorm**: Normalización de sección cruzada (Cross-sectional), que compara el valor actual de una acción frente al resto de las acciones ese mismo día.
* **Ratios técnicos**: Clases como Alpha158 o Alpha360 no usan precios directos, sino tasas de retorno (Return), volumen relativo, etc.

### ¿Cómo ver los datos reales sin procesar?
Si quieres ver exactamente qué datos crudos tiene la base de datos (precios ajustados, pero sin normalizar estadísticamente por algoritmos), puedes consultar lo siguiente usando el motor de datos base qlib.data.D:

```python
from qlib.data import D
# Extraer el precio de cierre y el factor de ajuste
df = D.features(['AAPL'], ['$close', '$factor'], start_time='2023-01-01', end_time='2023-01-10')
print(df)
```

(Nota: si los datos que descargaste en el entorno provienen de Yahoo Finance usando el script oficial de Qlib, el *$close* que verás ya es el valor que incorpora el *$factor* de los splits/dividendos).

**En resumen**: Lo que dices es totalmente cierto. Los precios que ves en Qlib no coinciden con los de una pantalla de operaciones histórica porque a nivel financiero **están ajustados por dividendos/splits** y, muy frecuentemente, a nivel informático **están normalizados o estandarizados** si provienen del DataHandler listo para entrenar el modelo.

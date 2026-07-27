# Laie — Previsión de ventas semanales por tienda

## Objetivo

Predecir las **ventas semanales** de **cada tienda** de Laie. El problema se plantea como una
regresión tabular sobre series temporales, con **previsión en bloque**: dado el histórico
(desde 2014), estimar la venta de cada (tienda, semana) del periodo de test **de una sola vez**,
sin usar valores intermedios del propio periodo.

Horizonte de negocio final: hasta el **31/12/2026** (se resuelve reentrenando el pipeline
ganador con todo el histórico; ver README).

## Ficheros

- `train/train.csv`: histórico de entrenamiento **con** la columna objetivo `sales`.
  Columnas: `store_id, date, sales, covid` (+ atributos de tienda si los hay).
- `test/test.csv`: periodo de test (holdout), **sin** `sales`. Columnas: `id, store_id, date, covid`.
- `sample_submission.csv`: formato de entrega. Columnas: `id, sales`.

## Definición de columnas

- `store_id` (str): identificador de la tienda.
- `date` (str, `YYYY-MM-DD`): **lunes** de la semana (semana ISO).
- `sales` (float): ventas netas de la semana en €. Es el **objetivo**.
- `covid` (int 0/1): 1 si la semana cae en 2020-2021 (periodo COVID), 0 en el resto.
- `id` (str): identificador único de fila = `"<store_id>__<date>"`.

## Entrega (submission)

`submission.csv` con **exactamente** las columnas `id, sales`, una fila por cada `id` de
`test/test.csv`, mismo número de filas.

## Métrica

**WAPE** (Weighted Absolute Percentage Error):

```
WAPE = sum(|sales_pred - sales_real|) / sum(|sales_real|)
```

**Menor es mejor** (minimización).

## RESTRICCIÓN CRÍTICA — sin fuga temporal (previsión en bloque)

El test es un **bloque** de varias semanas que se predice **todo a la vez**. Por tanto, para
predecir una semana del test **NO se pueden usar ventas de otras semanas del propio test**
(p. ej. no usar la venta de septiembre para predecir octubre).

Usa **solo features conocidas en el momento de prever**:
- **Calendario/estacionalidad**: semana del año, mes, y eventos del sector librería —
  **Sant Jordi (23 abril)**, Navidad, vuelta al cole (septiembre), festivos de Cataluña.
- **Atributos de tienda** (si están): m², ubicación, antigüedad, tipo.
- **Lags interanuales**: venta de la **misma semana del año anterior** (lag ≥ 52 semanas) y
  medias móviles calculadas **solo con datos anteriores al inicio del test**.

**Prohibido**: lags cortos (1-4 semanas) que dependan de valores dentro del periodo de test.

## Notas

- **COVID (2020-2021)**: se mantiene en el histórico marcado con `covid=1` (para que el modelo
  pueda condicionar), pero **queda fuera del test**. No se elimina, para no romper la
  continuidad ni perder un evento de estrés.
- Recomendado un **modelo global** (todas las tiendas juntas con `store_id` como feature) frente
  a un modelo por tienda.
- Tiendas nuevas sin histórico interanual: usar medias del grupo / tratarlas aparte.
- **Tiendas intermitentes**: algunas tiendas (de museo/monumento) tienen muchas semanas con
  venta 0 por cierres estacionales (p. ej. T017, T026, T030, T022, LAIE_CAF). Son ceros
  reales, no ausencia de datos; el modelo debe poder predecir 0 en esos casos.
- Todas las tiendas del test tienen histórico completo (algunas desde 2013, otras abrieron
  después pero con histórico interanual). La serie de cada tienda empieza en su primera venta.

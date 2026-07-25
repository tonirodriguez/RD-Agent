# Laie — Previsión de ventas por tienda

## Objetivo

Predecir las **ventas** de cada tienda de Laie para un horizonte futuro (por defecto,
semanal por tienda). El problema se plantea como una regresión tabular sobre series
temporales: dada la historia de ventas y variables de calendario/tienda, estimar la venta
de cada (tienda, periodo) del conjunto de test.

## Ficheros

- `train/train.csv`: histórico de entrenamiento **con** la columna objetivo `sales`.
  Columnas: `store_id, date, sales` (puede incluir features adicionales).
- `test/test.csv`: periodo a predecir, **sin** la columna `sales`.
  Columnas: `id, store_id, date`.
- `sample_submission.csv`: formato de entrega esperado. Columnas: `id, sales`.

## Definición de columnas

- `store_id` (str): identificador de la tienda (p.ej. `T01`).
- `date` (str, `YYYY-MM-DD`): inicio del periodo (semana = lunes).
- `sales` (float): ventas del periodo (€ o unidades). Es el **objetivo** a predecir.
- `id` (str): identificador único de fila = `"<store_id>__<date>"` (p.ej. `T01__2025-07-07`).

## Entrega (submission)

Genera un fichero `submission.csv` con **exactamente** las columnas `id, sales`, una fila por
cada `id` presente en `test/test.csv`, y en el **mismo número de filas**.

## Métrica de evaluación

**WAPE** (Weighted Absolute Percentage Error):

```
WAPE = sum(|sales_pred - sales_real|) / sum(|sales_real|)
```

**Menor es mejor** (minimización). Un WAPE de 0.10 significa un 10% de error agregado.

## Notas importantes

- **Evita fuga temporal**: ninguna feature del test puede usar información posterior a su
  fecha. Construye lags y medias móviles solo con datos pasados.
- Eventos relevantes del sector librería a modelar: **Sant Jordi (23 de abril)**, Navidad,
  vuelta al cole (septiembre), festivos locales de Cataluña.
- Considera marcar/excluir el periodo COVID (2020-2021) por su comportamiento anómalo.
- Recomendado un **modelo global** (todas las tiendas juntas con `store_id` como feature)
  frente a un modelo por tienda.

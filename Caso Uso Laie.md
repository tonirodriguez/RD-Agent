# Caso de uso — Previsión de ventas de Laie con RD-Agent

Plan para usar RD-Agent (escenario **`data_science`**, modo dataset local) para prever las
ventas de las tiendas de Laie hasta final de año a partir del histórico.

---

## Idea clave (condiciona todo el diseño)

RD-Agent **optimiza contra un conjunto de test con etiquetas conocidas**: necesita la
"verdad" para puntuar cada iteración. No puede optimizar sobre el futuro real (que no
tienes). Por eso el proyecto se plantea como un **backtest con holdout**:

1. Reservas un periodo histórico reciente como test (con ventas conocidas).
2. RD-Agent encuentra el mejor pipeline optimizando la métrica sobre ese test.
3. Reentrenas el pipeline ganador con **todo** el histórico y predices el futuro real.

---

## Fase 0 — Definición del problema

- **Objetivo**: ¿ventas en € o en unidades? ¿por tienda, o por tienda × categoría?
- **Granularidad**: recomendado **semanal por tienda** (mensual da pocas filas; diaria es muy
  ruidosa).
- **Horizonte**: de hoy (jul-2026) a dic-2026 (~5-6 meses).
- **Métrica**: **WAPE** o **MAPE** (error porcentual, interpretable por negocio). En las
  plantillas se usa **WAPE** (menor es mejor).

## Fase 1 — Preparación de datos

- Una fila por **(tienda, periodo)** con la venta como target.
- **Features** relevantes en librería/retail: calendario (mes, semana, festivos) y eventos
  del sector: **Sant Jordi (23 abril, clave en Cataluña)**, Navidad, vuelta al cole
  (septiembre). Lags (venta del mismo periodo el año anterior), medias móviles, tendencia,
  y atributos de tienda (tamaño, ubicación).
- **Cuidado con 2020-2021 (COVID)**: outliers a marcar o excluir.
- Limpieza: huecos, cierres, aperturas nuevas.

## Fase 2 — Carpeta del "competition" (customización principal)

Estructura exacta que espera RD-Agent dentro de `DS_LOCAL_DATA_PATH`:

```
git_ignore_folder/ds_data/
├── laie-sales-forecast/
│   ├── description.md          # tarea, columnas, target, MÉTRICA, formato de entrega
│   ├── train/                  # histórico CON la columna de ventas (target)
│   ├── test/                   # el periodo a predecir, SIN el target (solo features)
│   ├── sample_submission.csv   # formato de entrega: id, sales
│   └── sample.py               # (opcional) submuestra para debug
└── eval/
    └── laie-sales-forecast/
        ├── grade.py            # calcula WAPE: submission vs verdad
        ├── valid.py            # valida el formato de la submission
        └── submission_test.csv # la VERDAD del periodo de test
```

Ficheros a escribir a mano: `description.md`, `grade.py`, `valid.py` y las particiones
train/test/submission_test coherentes con el holdout. (Plantillas ya generadas.)

## Fase 3 — Diseño del holdout

- **train/** = histórico hasta un corte (p.ej. hasta jun-2025).
- **test/** + **submission_test.csv** = un periodo conocido de la **misma longitud que el
  horizonte** (p.ej. jul-dic 2025), para que `grade.py` puntúe.
- Evita **fuga temporal**: ninguna feature del test puede usar información futura.

## Fase 4 — Configuración (.env)

```bash
DS_SCEN="rdagent.scenarios.data_science.scen.DataScienceScen"   # modo local, NO Kaggle
DS_LOCAL_DATA_PATH="/home/toni/dev/RD-Agent/git_ignore_folder/ds_data"
DS_CODER_ON_WHOLE_PIPELINE=True
DS_IF_USING_MLE_DATA=False
DS_SAMPLE_DATA_BY_LLM=False
```

## Fase 5 — Ejecución del loop

```bash
source .venv/bin/activate
rdagent data_science --competition laie-sales-forecast --loop-n 1    # valida la cadena
rdagent data_science --competition laie-sales-forecast --loop-n 10   # ciclo completo
```

RD-Agent propone hipótesis (features, modelos, ensembles), escribe el pipeline completo
(`main.py`: datos → feature engineering → entrena → predice → `submission.csv`), lo puntúa
con `grade.py` y guarda el mejor (SOTA). Monitoriza:
`STREAMLIT_SERVER_FILE_WATCHER_TYPE=none rdagent ui --port 19899 --log-dir "log/" --data-science`.

## Fase 6 — Previsión real y entrega

- Toma el **mejor pipeline** de RD-Agent.
- **Reentrénalo con todo el histórico** (incluido el periodo de test).
- Predice el futuro real **jul-dic 2026** → previsión para negocio.
- Valida con sentido de negocio (Navidad, campañas).

## Caveats

- RD-Agent es optimización estilo Kaggle (una métrica sobre test etiquetado); no es una
  herramienta nativa de series temporales. Funciona bien **si** el holdout está bien montado.
- **Volumen**: pocas tiendas × pocos años puede sobreajustar. Un **modelo global** (todas las
  tiendas juntas, con `store_id` como feature) suele ir mejor que uno por tienda.
- **Coste/tiempo**: cada iteración llama mucho al LLM y entrena modelos; empieza con `--loop-n 1`.

---

## Esquema de datos usado en las plantillas

- **id**: identificador único de fila = `"<store_id>__<fecha>"` (p.ej. `T01__2025-07-07`).
- **target**: `sales` (ventas del periodo).
- **train/train.csv**: `store_id, date, sales` (+ features opcionales; RD-Agent generará más).
- **test/test.csv**: `id, store_id, date` (sin `sales`).
- **sample_submission.csv** y **submission_test.csv**: `id, sales`.
- Fecha semanal = fecha de inicio de semana (lunes) en formato `YYYY-MM-DD`.

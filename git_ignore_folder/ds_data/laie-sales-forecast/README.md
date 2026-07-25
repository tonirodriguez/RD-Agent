# laie-sales-forecast — esqueleto del dataset

Estructura lista para RD-Agent (`data_science`, modo local). Los CSV son **ejemplos** con 2
tiendas y unas pocas semanas; sustitúyelos por tus datos reales manteniendo las columnas.

```
laie-sales-forecast/
├── description.md          # NO tocar salvo para ajustar la tarea/métrica
├── sample_submission.csv   # formato de entrega: id, sales
├── train/train.csv         # histórico CON sales  (store_id, date, sales)
└── test/test.csv           # periodo a predecir SIN sales  (id, store_id, date)

eval/laie-sales-forecast/
├── grade.py                # métrica WAPE (menor = mejor)
├── valid.py                # valida formato de submission
└── submission_test.csv     # VERDAD del test (id, sales) — la usa grade.py
```

## Cómo rellenarlo con tus datos

1. **train/train.csv**: todo tu histórico hasta el corte, con la venta real en `sales`.
2. **Holdout**: elige un periodo reciente conocido (p.ej. jul-dic 2025) como test.
   - `test/test.csv`: filas de ese periodo **sin** `sales` (solo `id, store_id, date`).
   - `eval/.../submission_test.csv`: esas mismas filas **con** la venta real (`id, sales`).
   - Asegúrate de que `id`, orden y nº de filas coinciden entre `test.csv`, `sample_submission.csv`
     y `submission_test.csv`.
3. `id` = `"<store_id>__<date>"`. Fecha semanal = lunes en `YYYY-MM-DD`.

## Importante: ubicación y sincronización

- Esta carpeta está bajo `git_ignore_folder/`, que **está excluida de `sync_rdagent.sh`** y del
  control de versiones. Cópiala manualmente a tu copia de trabajo de WSL:

  ```bash
  cp -r /mnt/c/Users/trodriguez/src/RD-Agent/git_ignore_folder/ds_data/laie-sales-forecast \
        ~/dev/RD-Agent/git_ignore_folder/ds_data/
  cp -r /mnt/c/Users/trodriguez/src/RD-Agent/git_ignore_folder/ds_data/eval/laie-sales-forecast \
        ~/dev/RD-Agent/git_ignore_folder/ds_data/eval/
  ```

## Ejecutar

```bash
cd ~/dev/RD-Agent
source .venv/bin/activate
# .env: DS_SCEN=...DataScienceScen, DS_LOCAL_DATA_PATH=.../git_ignore_folder/ds_data,
#       DS_IF_USING_MLE_DATA=False, DS_SAMPLE_DATA_BY_LLM=False, DS_CODER_ON_WHOLE_PIPELINE=True
rdagent data_science --competition laie-sales-forecast --loop-n 1
```

"""
grade.py — Scoring de la previsión de ventas de Laie.

Métrica: WAPE (Weighted Absolute Percentage Error). MENOR ES MEJOR.
Alinea `submission.csv` con `submission_test.csv` por la columna `id`.

Ejecución (RD-Agent lo llama así, con ambos csv en el mismo directorio):
    python grade.py
Imprime: {"competition_id": "laie-sales-forecast", "score": <wape>}
"""
import json

import numpy as np
import pandas as pd


class InvalidSubmissionError(Exception):
    """Se lanza cuando la submission no cumple el formato esperado."""


ID_COL = "id"
TARGET_COL = "sales"
COMPETITION_ID = "laie-sales-forecast"


def _check(submission: pd.DataFrame, answers: pd.DataFrame) -> None:
    for col in (ID_COL, TARGET_COL):
        if col not in answers.columns:
            raise AssertionError(f"answers debe tener la columna '{col}'")
        if col not in submission.columns:
            raise InvalidSubmissionError(f"submission debe tener la columna '{col}'")
    if len(submission) != len(answers):
        raise InvalidSubmissionError(
            f"submission tiene {len(submission)} filas y answers {len(answers)}"
        )
    try:
        pd.to_numeric(submission[TARGET_COL])
    except ValueError:
        raise InvalidSubmissionError(f"La columna '{TARGET_COL}' debe ser numérica")


def grade(submission: pd.DataFrame, answers: pd.DataFrame) -> float:
    """Devuelve el WAPE (menor es mejor)."""
    _check(submission, answers)
    sub = submission.sort_values(ID_COL).reset_index(drop=True)
    ans = answers.sort_values(ID_COL).reset_index(drop=True)

    if (sub[ID_COL].astype(str).values != ans[ID_COL].astype(str).values).any():
        raise InvalidSubmissionError("Los 'id' de submission y answers no coinciden")

    y_true = pd.to_numeric(ans[TARGET_COL]).to_numpy(dtype=float)
    y_pred = pd.to_numeric(sub[TARGET_COL]).to_numpy(dtype=float)

    denom = np.abs(y_true).sum()
    if denom == 0:
        raise InvalidSubmissionError("La suma de ventas reales es 0; WAPE indefinido")

    wape = float(np.abs(y_pred - y_true).sum() / denom)
    return wape


if __name__ == "__main__":
    submission = pd.read_csv("submission.csv")
    answers = pd.read_csv("submission_test.csv")
    score = grade(submission=submission, answers=answers)
    print(json.dumps({"competition_id": COMPETITION_ID, "score": score}))

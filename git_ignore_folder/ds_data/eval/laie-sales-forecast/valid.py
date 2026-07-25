"""
valid.py — Validación de formato de la submission de Laie.
Comprueba que submission.csv existe y tiene el mismo nº de líneas que submission_test.csv.
"""
from pathlib import Path

assert Path("submission.csv").exists(), "Error: submission.csv no encontrado"

submission_lines = Path("submission.csv").read_text().splitlines()
test_lines = Path("submission_test.csv").read_text().splitlines()

is_valid = len(submission_lines) == len(test_lines)

if is_valid:
    message = "submission.csv y submission_test.csv tienen el mismo número de líneas."
else:
    message = (
        f"submission.csv tiene {len(submission_lines)} líneas, "
        f"mientras que submission_test.csv tiene {len(test_lines)} líneas."
    )

print(message)

if not is_valid:
    raise AssertionError("La submission no es válida")

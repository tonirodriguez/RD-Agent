#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
QLIB_REPO="${QLIB_REPO:-/mnt/c/Users/trodriguez/src/qlib}"         # ruta donde clonaste qlib
DATA_DIR="${DATA_DIR:-$HOME/.qlib/qlib_data/us_data}"
PYTHON_BIN="${PYTHON_BIN:-python}"
TODAY=$(date +%F)

# === CHECKS ===
if [ ! -d "$QLIB_REPO/scripts/data_collector/yahoo" ]; then
  echo "❌ No encuentro el repo qlib en: $QLIB_REPO"
  exit 1
fi

echo "➡️ Actualizando datos Qlib (Solo S&P 500) hasta $TODAY ..."

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

# Ejecutamos el script de python personalizado que filtra las acciones
$PYTHON_BIN scripts/update_sp500.py update_data_to_bin \
  --qlib_data_1d_dir "$DATA_DIR" \
  --end_date "$TODAY" \
  --region US

echo "✅ Update completado para S&P 500 hasta $TODAY."

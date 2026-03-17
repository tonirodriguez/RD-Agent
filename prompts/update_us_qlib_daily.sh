#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
QLIB_REPO="${QLIB_REPO:-/mnt/d/src/qlib}"         # ruta donde clonaste qlib
DATA_DIR="${DATA_DIR:-$HOME/.qlib/qlib_data/us_data}"
PYTHON_BIN="${PYTHON_BIN:-python}"
START_DATE="2025-12-31"
TODAY=$(date +%F)

# === CHECKS ===
if [ ! -d "$QLIB_REPO/scripts/data_collector/yahoo" ]; then
  echo "❌ No encuentro el repo qlib en: $QLIB_REPO"
  echo "   Clona qlib primero si no lo has hecho o ajusta la variable QLIB_REPO."
  exit 1
fi

if [ ! -d "$DATA_DIR" ]; then
  echo "⚠️  No encuentro el dataset Qlib US en: $DATA_DIR"
  echo "   Asegúrate de haber inicializado los datos primero o el collector lo hará."
fi

echo "➡️ Actualizando datos Qlib US desde $START_DATE hasta $TODAY ..."

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

# Nota: en collector.py de Qlib Yahoo, --trading_date funciona como 'start_date'
$PYTHON_BIN scripts/data_collector/yahoo/collector.py update_data_to_bin \
  --qlib_data_1d_dir "$DATA_DIR" \
  --trading_date "$START_DATE" \
  --end_date "$TODAY" \
  --region US

echo "✅ Update completado desde $START_DATE hasta $TODAY."
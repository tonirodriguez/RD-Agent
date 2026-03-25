#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
QLIB_REPO="${QLIB_REPO:-/mnt/c/Users/trodriguez/src/qlib}"         # ruta donde clonaste qlib
DATA_DIR="${DATA_DIR:-$HOME/.qlib/qlib_data/us_data}"
PYTHON_BIN="${PYTHON_BIN:-python}"
START_DATE="${START_DATE:-2025-12-31}"
REBUILD_START_DATE="${REBUILD_START_DATE:-1999-12-31}"
MAX_WORKERS="${MAX_WORKERS:-1}"
TODAY=$(date +%F)
MODE="update"
REBUILD_UNIVERSE_DIR="${REBUILD_UNIVERSE_DIR:-}"

if [ "${1:-}" = "--clean-rebuild" ]; then
  MODE="rebuild"
  shift
fi

# === CHECKS ===
if [ ! -d "$QLIB_REPO/scripts/data_collector/yahoo" ]; then
  echo "❌ No encuentro el repo qlib en: $QLIB_REPO"
  echo "   Clona qlib primero si no lo has hecho o ajusta la variable QLIB_REPO."
  exit 1
fi

if [ ! -d "$DATA_DIR" ] && [ "$MODE" = "update" ]; then
  echo "⚠️  No encuentro el dataset Qlib US en: $DATA_DIR"
  echo "   Asegúrate de haber inicializado los datos primero o el collector lo hará."
fi

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
export QLIB_MAX_WORKERS="$MAX_WORKERS"

if [ "$MODE" = "rebuild" ]; then
  echo "ℹ️  Usando QLIB_MAX_WORKERS=$QLIB_MAX_WORKERS"
  if [ -z "$REBUILD_UNIVERSE_DIR" ]; then
    if [ -s "$DATA_DIR/instruments/all.txt" ] && [ -s "$DATA_DIR/calendars/day.txt" ]; then
      REBUILD_UNIVERSE_DIR="$DATA_DIR"
    else
      for candidate in $(find "$(dirname "$DATA_DIR")" -maxdepth 1 -type d -name "$(basename "$DATA_DIR")_backup_*" | sort -r); do
        if [ -s "$candidate/instruments/all.txt" ] && [ -s "$candidate/calendars/day.txt" ]; then
          REBUILD_UNIVERSE_DIR="$candidate"
          break
        fi
      done
    fi
  fi

  if [ -z "$REBUILD_UNIVERSE_DIR" ]; then
    echo "❌ No encuentro una fuente de universo válida para el clean rebuild."
    echo "   Ajusta REBUILD_UNIVERSE_DIR o restaura un backup sano en $DATA_DIR."
    exit 1
  fi

  echo "➡️ Reconstruyendo datos Qlib US desde $REBUILD_START_DATE hasta $TODAY ..."
  $PYTHON_BIN scripts/update_us_all.py rebuild_data_to_bin \
    --qlib_data_1d_dir "$DATA_DIR" \
    --universe_data_dir "$REBUILD_UNIVERSE_DIR" \
    --start_date "$REBUILD_START_DATE" \
    --end_date "$TODAY" \
    --backup_existing True \
    --region US
  echo "✅ Reconstrucción completada desde $REBUILD_START_DATE hasta $TODAY."
else
  echo "ℹ️  Usando QLIB_MAX_WORKERS=$QLIB_MAX_WORKERS"
  echo "➡️ Actualizando datos Qlib US desde $START_DATE hasta $TODAY ..."
  $PYTHON_BIN scripts/update_us_all.py update_data_to_bin \
    --qlib_data_1d_dir "$DATA_DIR" \
    --trading_date "$START_DATE" \
    --end_date "$TODAY" \
    --region US
  echo "✅ Update completado desde $START_DATE hasta $TODAY."
fi

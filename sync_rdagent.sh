#!/usr/bin/env bash
# =============================================================================
# sync_rdagent.sh — Sincronización bidireccional (WSL <-> Windows) de RD-Agent
#
#   WSL (rápido):   /home/toni/dev/RD-Agent
#   Windows (mnt):  /mnt/c/Users/trodriguez/src/RD-Agent
#
# Estrategia: rsync en ambas direcciones con "el más nuevo gana" (-u/--update).
# NO borra archivos (sin --delete) para evitar pérdidas en sync bidireccional.
# EXCLUYE carpetas pesadas/generadas para no duplicar GB ni llenar el disco.
#
# Uso:
#   bash sync_rdagent.sh              # sincroniza en ambos sentidos
#   bash sync_rdagent.sh --dry-run    # simula, no copia nada (recomendado 1ª vez)
#   bash sync_rdagent.sh --to-win     # solo WSL  -> Windows
#   bash sync_rdagent.sh --to-wsl     # solo Windows -> WSL
#   bash sync_rdagent.sh --delete     # además propaga borrados (¡peligroso!)
# =============================================================================
set -euo pipefail

WSL_DIR="/home/toni/dev/RD-Agent"
WIN_DIR="/mnt/c/Users/trodriguez/src/RD-Agent"

GREEN='\033[0;32m'; YEL='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok(){ echo -e "${GREEN}✔ $1${NC}"; }
warn(){ echo -e "${YEL}⚠ $1${NC}"; }
err(){ echo -e "${RED}✘ $1${NC}"; }

# --- Opciones ----------------------------------------------------------------
DRY=""; DIRECTION="both"; DEL=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY="--dry-run" ;;
    --to-win)  DIRECTION="to-win" ;;
    --to-wsl)  DIRECTION="to-wsl" ;;
    --delete)  DEL="--delete" ;;
    *) err "Opción desconocida: $arg"; exit 1 ;;
  esac
done

# --- Comprobaciones ----------------------------------------------------------
command -v rsync >/dev/null 2>&1 || { err "rsync no instalado: sudo apt install rsync"; exit 1; }
[ -d "$WSL_DIR" ] || { err "No existe $WSL_DIR"; exit 1; }
[ -d "$WIN_DIR" ] || { err "No existe $WIN_DIR"; exit 1; }

# --- Exclusiones (código y config sí; artefactos pesados NO) ------------------
EXCLUDES=(
  --exclude ".git/"
  --exclude ".venv/"
  --exclude "venv/"
  --exclude "__pycache__/"
  --exclude "*.pyc"
  --exclude "*.egg-info/"
  --exclude ".mypy_cache/"
  --exclude ".pytest_cache/"
  --exclude ".ruff_cache/"
  --exclude "git_ignore_folder/"
  --exclude "log/"
  --exclude "logs/"
  --exclude "*.log"
  --exclude "pickle_cache/"
  --exclude "data/"
  --exclude ".qlib/"
  --exclude "mlruns/"
)

# rsync: -a archiva, -u solo copia si origen es más nuevo, -i muestra cambios,
# -h legible, --prune-empty-dirs evita crear árboles vacíos por exclusiones.
RSYNC_OPTS=(-a -u -i -h --prune-empty-dirs $DRY $DEL "${EXCLUDES[@]}")

sync_dir () { # $1=origen  $2=destino  $3=etiqueta
  echo "----------------------------------------------"
  echo "→ $3"
  rsync "${RSYNC_OPTS[@]}" "$1/" "$2/"
}

[ -n "$DRY" ] && warn "MODO DRY-RUN: no se copia nada, solo se muestran los cambios."
[ -n "$DEL" ] && warn "MODO --delete ACTIVO: se propagarán borrados."

case "$DIRECTION" in
  to-win) sync_dir "$WSL_DIR" "$WIN_DIR" "WSL  ->  Windows" ;;
  to-wsl) sync_dir "$WIN_DIR" "$WSL_DIR" "Windows  ->  WSL" ;;
  both)
    # Bidireccional "newer wins": dos pasadas con -u en sentidos opuestos.
    sync_dir "$WSL_DIR" "$WIN_DIR" "WSL  ->  Windows (newer wins)"
    sync_dir "$WIN_DIR" "$WSL_DIR" "Windows  ->  WSL (newer wins)"
    ;;
esac

echo "=============================================="
ok "Sincronización completada ($DIRECTION)."
[ -n "$DRY" ] && echo "  (era dry-run; ejecuta sin --dry-run para aplicar)"
echo "=============================================="

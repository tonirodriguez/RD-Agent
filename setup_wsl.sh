#!/usr/bin/env bash
# =============================================================================
# setup_wsl.sh — Puesta en marcha de RD-Agent en WSL (Ubuntu)
# Configura los 6 escenarios: fin_quant, fin_factor, fin_model,
#                             fin_factor_report, general_model, data_science
#
# Uso (DENTRO de tu WSL, desde la raíz del repo):
#     bash setup_wsl.sh              # instala + config + crea carpetas
#     bash setup_wsl.sh --with-data  # además descarga datasets de ejemplo
# =============================================================================
set -euo pipefail

WITH_DATA=false
[ "${1:-}" = "--with-data" ] && WITH_DATA=true

GREEN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✔ $1${NC}"; }
warn() { echo -e "${YEL}⚠ $1${NC}"; }
err()  { echo -e "${RED}✘ $1${NC}"; }

echo "=============================================="
echo "  RD-Agent · Setup WSL (6 escenarios)"
echo "=============================================="

# --- 1. Python ---------------------------------------------------------------
PYVER=$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python detectado: $PYVER"
case "$PYVER" in
  3.10|3.11) ok "Versión de Python compatible (3.10/3.11)";;
  *) warn "RD-Agent está probado en 3.10/3.11. La tuya es $PYVER; puede dar problemas.";;
esac

# --- 2. Entorno virtual ------------------------------------------------------
if [ ! -d ".venv" ]; then
  echo "Creando entorno virtual .venv ..."
  python3 -m venv .venv || { err "No se pudo crear venv. Instala: sudo apt install python3-venv"; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
ok "venv activado: $(which python)"

# --- 3. Instalación de RD-Agent (modo desarrollador) -------------------------
python -m pip install -U pip setuptools wheel
echo "Instalando rdagent en modo editable (esto tarda unos minutos)..."
pip install -e . -c "constraints/${PYVER}.txt" 2>/dev/null || pip install -e .
pip install -U kaggle || warn "kaggle no instalado (solo necesario para competiciones Kaggle)"
rdagent --help >/dev/null 2>&1 && ok "rdagent instalado" || warn "revisar instalación de rdagent"

# --- 4. Docker (obligatorio para TODOS los escenarios) -----------------------
echo "----------------------------------------------"
if command -v docker >/dev/null 2>&1; then
  if docker run --rm hello-world >/dev/null 2>&1; then
    ok "Docker funciona SIN sudo (requisito cumplido)"
  else
    err "Docker instalado pero no corre sin sudo."
    echo "   - Docker Desktop: Settings > Resources > WSL Integration > activa tu distro."
    echo "   - Docker nativo:  sudo usermod -aG docker \$USER  (reabre la terminal)."
  fi
else
  err "Docker NO instalado. Es OBLIGATORIO para los 6 escenarios."
  echo "   Docs: https://docs.docker.com/engine/install/ubuntu/"
fi

# --- 5. .env -----------------------------------------------------------------
echo "----------------------------------------------"
if [ -f ".env" ]; then
  ok ".env presente"
  if grep -q "PON_AQUI_TU_OPENROUTER_API_KEY" .env; then
    warn "Falta pegar tu OpenRouter API key en .env (OPENROUTER_API_KEY y LITELLM_PROXY_API_KEY)."
  else
    ok "OpenRouter API key configurada"
  fi
else
  warn ".env no encontrado. Copia .env.example y edítalo: cp .env.example .env"
fi

# --- 6. Carpetas y variables de datos por escenario --------------------------
echo "----------------------------------------------"
echo "Preparando carpetas de datos..."
mkdir -p git_ignore_folder/reports        # fin_factor_report
mkdir -p git_ignore_folder/ds_data         # data_science
ok "Carpetas creadas: git_ignore_folder/{reports,ds_data}"

# Fijar ruta de datos de data_science en .env
if command -v dotenv >/dev/null 2>&1; then
  dotenv set DS_LOCAL_DATA_PATH "$(pwd)/git_ignore_folder/ds_data" >/dev/null 2>&1 && \
    ok "DS_LOCAL_DATA_PATH fijado en .env" || warn "No se pudo fijar DS_LOCAL_DATA_PATH (hazlo a mano)."
else
  warn "'dotenv' CLI no disponible; añade a .env:  DS_LOCAL_DATA_PATH=\"$(pwd)/git_ignore_folder/ds_data\""
fi

# --- 7. Descarga de datasets de ejemplo (opcional) ---------------------------
if $WITH_DATA; then
  echo "----------------------------------------------"
  echo "Descargando datos de ejemplo (--with-data)..."

  # 7a. Informes financieros para fin_factor_report
  if [ -z "$(ls -A git_ignore_folder/reports 2>/dev/null)" ]; then
    echo "· fin_factor_report: descargando informes (all_reports.zip)..."
    wget -q --show-progress https://github.com/SunsetWolf/rdagent_resource/releases/download/reports/all_reports.zip -O /tmp/all_reports.zip \
      && unzip -q -o /tmp/all_reports.zip -d git_ignore_folder/reports && ok "Informes listos en git_ignore_folder/reports" \
      || warn "No se pudieron descargar los informes (hazlo manualmente, ver guía §4.4)."
  else
    ok "Ya hay informes en git_ignore_folder/reports"
  fi

  # 7b. Dataset de ejemplo para data_science (ARF 12h, NO Kaggle)
  if [ ! -d git_ignore_folder/ds_data/arf-12-hours-prediction-task ]; then
    echo "· data_science: descargando dataset arf-12-hours-prediction-task..."
    wget -q --show-progress https://github.com/SunsetWolf/rdagent_resource/releases/download/ds_data/arf-12-hours-prediction-task.zip -O /tmp/arf.zip \
      && unzip -q -o /tmp/arf.zip -d git_ignore_folder/ds_data/ && ok "Dataset listo" \
      || warn "No se pudo descargar el dataset (hazlo manualmente, ver guía §4.6)."
  else
    ok "Dataset arf-12-hours-prediction-task ya presente"
  fi
else
  warn "Datos de ejemplo NO descargados. Ejecuta 'bash setup_wsl.sh --with-data' o descárgalos según la guía."
fi

# --- 8. Kaggle (opcional, solo para modo Kaggle de data_science) -------------
echo "----------------------------------------------"
if [ -f "$HOME/.config/kaggle/kaggle.json" ]; then
  ok "Kaggle configurado (~/.config/kaggle/kaggle.json)"
else
  warn "Kaggle NO configurado (solo necesario para competiciones Kaggle). Ver guía §4.6."
fi

echo "=============================================="
echo "  Siguiente paso:  rdagent health_check"
echo "  Recuerda activar el entorno en cada sesión:"
echo "     source .venv/bin/activate"
echo "=============================================="

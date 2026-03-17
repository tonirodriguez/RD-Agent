#!/bin/bash

# Configuración de directorios
SOURCE_DIR="$HOME/.qlib/qlib_data/us_data"
DEST_DIR="$HOME/.qlib/backups"

# Crear el directorio de backups si no existe
mkdir -p "$DEST_DIR"

# Generar el nombre del archivo con un timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$DEST_DIR/us_data_backup_${TIMESTAMP}.zip"

echo "Iniciando el backup de: $SOURCE_DIR"

# Verificar que el directorio origen existe
if [ -d "$SOURCE_DIR" ]; then
    # Cambiar al directorio padre para que el zip guarde rutas relativas (us_data/...)
    cd "$(dirname "$SOURCE_DIR")" || { echo "Error al acceder a $(dirname "$SOURCE_DIR")"; exit 1; }
    
    # Comprimir la carpeta de forma recursiva
    zip -r "$BACKUP_FILE" "$(basename "$SOURCE_DIR")"
    
    # Comprobar si el comando zip fue exitoso
    if [ $? -eq 0 ]; then
        echo "=========================================="
        echo "✅ Backup completado con éxito."
        echo "📁 Archivo guardado en: $BACKUP_FILE"
        echo "=========================================="
    else
        echo "❌ Error al comprimir el directorio usando zip."
        exit 1
    fi
else
    echo "❌ Error: El directorio origen $SOURCE_DIR no existe."
    exit 1
fi

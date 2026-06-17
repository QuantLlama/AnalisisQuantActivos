#!/usr/bin/env bash
# =============================================================================
# setup_env.sh — Configuración automática del entorno (Linux/macOS)
# =============================================================================
set -e

echo "=============================================="
echo "  Analisis Activos — Setup de Entorno"
echo "=============================================="

# Verificar Python 3.10+
PYTHON_CMD=$(command -v python3 || command -v python)
if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Python no encontrado. Instala Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PYTHON_VERSION encontrado en: $PYTHON_CMD"

# Crear entorno virtual
VENV_PATH=".venv"
VENV_LOCAL=true

if [ ! -f ".venv/bin/activate" ]; then
    # Limpiar carpeta si existe pero está rota
    rm -rf .venv
    echo "[...] Intentando crear entorno virtual local .venv ..."
    if $PYTHON_CMD -m venv --copies .venv 2>/dev/null; then
        echo "[OK] Entorno virtual local creado."
    else
        echo "[WARNING] No se pudo crear el venv localmente (posible sistema de archivos montado sin permisos de enlaces)."
        VENV_PATH="$HOME/.venv_analisis_activos"
        VENV_LOCAL=false
        if [ ! -f "$VENV_PATH/bin/activate" ]; then
            rm -rf "$VENV_PATH"
            echo "[...] Creando entorno virtual en el Home: $VENV_PATH ..."
            $PYTHON_CMD -m venv "$VENV_PATH"
            echo "[OK] Entorno virtual en Home creado."
        else
            echo "[OK] Entorno virtual en Home ya existe."
        fi
    fi
else
    echo "[OK] Entorno virtual local ya existe."
fi

# Activar entorno
if [ "$VENV_LOCAL" = true ]; then
    source .venv/bin/activate
else
    source "$VENV_PATH/bin/activate"
    # Crear script activador local de conveniencia
    cat << 'EOF' > activate_env.sh
#!/usr/bin/env bash
source "$HOME/.venv_analisis_activos/bin/activate"
echo "[OK] Entorno virtual de Analisis Activos activado."
EOF
    chmod +x activate_env.sh
fi
echo "[OK] Entorno virtual activado."

# Actualizar pip
pip install --upgrade pip --quiet

# Instalar dependencias
echo "[...] Instalando dependencias..."
pip install -r requirements.txt

# Crear directorios necesarios
mkdir -p .cache logs exports data/raw

echo ""
echo "=============================================="
echo "  Setup completado exitosamente!"
echo ""
echo "  Para activar el entorno:"
if [ "$VENV_LOCAL" = true ]; then
    echo "    source .venv/bin/activate"
else
    echo "    source activate_env.sh"
fi
echo ""
echo "  Para iniciar el sistema:"
echo "    python main.py"
echo "=============================================="

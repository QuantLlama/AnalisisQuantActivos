#!/usr/bin/env bash

# Si estamos en el entorno virtual, usar ese python, sino python3 genérico
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif [ -f "$HOME/.venv_analisis_activos/bin/python" ]; then
    PYTHON_BIN="$HOME/.venv_analisis_activos/bin/python"
else
    PYTHON_BIN="python3"
fi

$PYTHON_BIN main.py "$@"

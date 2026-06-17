"""
main.py — Punto de entrada principal para el Sistema de Análisis Financiero Terminal.
Verifica dependencias e inicia el shell interactivo (REPL).
"""
from __future__ import annotations

import sys
from utils.logger import get_logger

logger = get_logger("main")


def check_dependencies() -> bool:
    """Verifica que las bibliotecas esenciales estén instaladas."""
    critical_libs = [
        "yfinance",
        "pandas",
        "numpy",
        "rich",
        "prompt_toolkit",
        "plotext",
        "toml",
    ]
    
    missing = []
    for lib in critical_libs:
        try:
            __import__(lib)
        except ImportError:
            missing.append(lib)
            
    if missing:
        print("=" * 60)
        print("❌ ERROR: Faltan dependencias críticas de Python:")
        for lib in missing:
            print(f"   • {lib}")
        print("=" * 60)
        print("Por favor, ejecuta el script de configuración del entorno para instalarlas:")
        print("   Linux/macOS : source setup_env.sh")
        print("   Windows     : setup_env.bat")
        print("=" * 60)
        return False
    return True


def main() -> None:
    """Función de inicio principal."""
    if not check_dependencies():
        sys.exit(1)

    try:
        from ui.shell import AnalysisShell
        shell = AnalysisShell()
        shell.run()
    except Exception as e:
        logger.exception("Error fatal al iniciar la aplicación")
        print(f"\n❌ Error fatal de inicialización: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

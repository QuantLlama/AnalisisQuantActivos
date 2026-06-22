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
        "fastapi",
        "uvicorn"
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
        if len(sys.argv) > 1 and sys.argv[1].lower() == "web":
            print("Iniciando Dashboard Web Profesional...")
            import uvicorn
            uvicorn.run("web.api:app", host="0.0.0.0", port=8555, reload=True)
        elif len(sys.argv) > 1 and sys.argv[1].lower() == "test":
            from ui.shell import AnalysisShell
            shell = AnalysisShell()
            shell.cmd_test(sys.argv[2:] or ["connections"])
        else:
            from ui.shell import AnalysisShell
            shell = AnalysisShell()
            shell.run()
    except Exception as e:
        logger.exception("Error fatal al iniciar la aplicación")
        print(f"\n❌ Error fatal de inicialización: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

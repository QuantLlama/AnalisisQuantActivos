#!/usr/bin/env python3
"""
install.py — Instalador universal multiplataforma para FLUX Quant
Detecta el sistema operativo y ejecuta el script de configuración correspondiente.
"""
import os
import sys
import platform
import subprocess
from pathlib import Path

def main():
    print("=" * 50)
    print("  🚀 Iniciando Instalador Universal de FLUX Quant")
    print("=" * 50)

    # Asegurarnos de estar en el directorio correcto
    project_root = Path(__file__).parent.absolute()
    os.chdir(project_root)

    system = platform.system()
    
    if system == "Windows":
        script = "setup_env.bat"
        print(f"[+] Detectado Windows. Ejecutando {script}...\n")
        try:
            subprocess.check_call([script], shell=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[!] Error ejecutando {script}. Código: {e.returncode}")
            sys.exit(1)
            
    elif system in ["Linux", "Darwin"]:
        script = "./setup_env.sh"
        print(f"[+] Detectado {system} (Unix). Ejecutando {script}...\n")
        
        # Dar permisos de ejecución por si no los tiene
        try:
            os.chmod("setup_env.sh", 0o755)
            os.chmod("flux", 0o755)
        except Exception as e:
            print(f"[*] Nota: no se pudieron cambiar los permisos (ignorar si es NTFS): {e}")

        try:
            subprocess.check_call([script])
        except subprocess.CalledProcessError as e:
            print(f"\n[!] Error ejecutando {script}. Código: {e.returncode}")
            sys.exit(1)
            
    else:
        print(f"[!] Sistema operativo '{system}' no reconocido.")
        print("Intenta ejecutar setup_env.sh o setup_env.bat manualmente.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Instalación cancelada por el usuario.")
        sys.exit(1)

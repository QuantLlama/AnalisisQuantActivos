import json
import os
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'symbols.json')
NT8_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'symbols_nt8.json')

def load_symbol_map(platform="mt5"):
    """Load symbol mapping for specified platform (mt5 or nt8)"""
    config_path = NT8_CONFIG_PATH if platform == "nt8" else CONFIG_PATH
    
    if not os.path.exists(config_path):
        # Create default structure if file doesn't exist
        default_map = {
            "Futures": {},
            "Stocks": {},
            "Crypto": {},
            "ETF": {}
        }
        save_symbol_map(default_map, platform)
        return default_map
    
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[red]Error cargando mapa de símbolos ({platform}): {e}[/red]")
        return {}

def save_symbol_map(data, platform="mt5"):
    """Save symbol mapping for specified platform"""
    config_path = NT8_CONFIG_PATH if platform == "nt8" else CONFIG_PATH
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)
        console.print(f"[green]Configuración guardada exitosamente ({platform}).[/green]")
    except Exception as e:
        console.print(f"[red]Error guardando configuración: {e}[/red]")

def configure_symbols():
    console.clear()
    console.print("[bold gold1]⚙️ CONFIGURACIÓN DE MAPEO DE SÍMBOLOS[/bold gold1]")
    
    # Select platform
    console.print("\n[1] MetaTrader 5 (MT5)")
    console.print("[2] NinjaTrader 8 (NT8)")
    platform_choice = Prompt.ask("Seleccione la plataforma a configurar", choices=["1", "2"], default="1")
    platform = "nt8" if platform_choice == "2" else "mt5"
    
    platform_name = "NinjaTrader 8" if platform == "nt8" else "MetaTrader 5"
    console.print(f"\n[cyan]Configurando símbolos para {platform_name}[/cyan]")
    console.print(f"Asocie los tickers del sistema (Yahoo Finance) con los símbolos de {platform_name}.\n")
    
    data = load_symbol_map(platform)
    
    while True:
        # Show current map
        table = Table(title="Mapeo Actual")
        table.add_column("Categoría", style="cyan")
        table.add_column("Ticker Sistema", style="white")
        table.add_column("Símbolo Broker ({platform_name})", style="green")
        
        for category, symbols in data.items():
            for sys_ticker, broker_ticker in symbols.items():
                table.add_row(category, sys_ticker, broker_ticker)
                
        console.print(table)
        
        console.print("\n[1] Editar un Símbolo")
        console.print("[2] Agregar Nuevo Símbolo")
        console.print("[3] Volver al Menú Principal")
        
        choice = Prompt.ask("Seleccione una opción", choices=["1", "2", "3"], default="3")
        
        if choice == "3":
            break
            
        elif choice == "1":
            sys_ticker = Prompt.ask("Ingrese el Ticker del Sistema a editar (ej. MNQ=F)")
            found = False
            for cat in data:
                if sys_ticker in data[cat]:
                    new_broker = Prompt.ask(f"Nuevo símbolo Broker para {sys_ticker}", default=data[cat][sys_ticker])
                    data[cat][sys_ticker] = new_broker
                    found = True
                    save_symbol_map(data, platform)
                    break
            if not found:
                console.print(f"[red]Ticker {sys_ticker} no encontrado.[/red]")
                
        elif choice == "2":
            cat = Prompt.ask("Categoría", choices=["Futures", "Stocks", "Crypto", "ETF"])
            sys_ticker = Prompt.ask("Ticker del Sistema (Yahoo Finance)")
            broker_ticker = Prompt.ask(f"Símbolo en {platform_name}")
            
            if cat not in data:
                data[cat] = {}
            
            data[cat][sys_ticker] = broker_ticker
            save_symbol_map(data, platform)

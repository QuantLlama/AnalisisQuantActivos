import os
import sys

# Desactivar CUDA antes de importar torch si se solicita modo CPU puro
if os.environ.get("FORCE_CPU") == "1":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import torch
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint
import time
import webbrowser

# Import training logic
from train import train_model
from qutils.config_manager import configure_symbols
from qutils.cleaner import clean_system_data

console = Console()

def show_header():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]LLAMA QUANTUM GAN V2.0.0 - SISTEMA DE PREDICCIÓN MULTI-MERCADO[/bold cyan]\n"
        "[white]Powered by PyTorch & Deep Learning Ing. Pablo Ez. M[/white]",
        subtitle="v2.0.0",
        border_style="blue"
    ))

def check_hardware():
    console.print("\n[bold yellow]Paso 1: Verificación de Hardware[/bold yellow]")
    
    # Si ya estamos en modo CPU forzado
    if os.environ.get("FORCE_CPU") == "1":
        console.print("ℹ️ [yellow]Modo CPU puro forzado para evitar conflictos de compatibilidad con CUDA.[/yellow]")
        from config import config
        config.DEVICE = torch.device("cpu")
        return "cpu"

    if torch.cuda.is_available():
        try:
            device_name = torch.cuda.get_device_name(0)
            console.print(f"✅ [green]GPU Detectada:[/green] {device_name}")
        except Exception:
            console.print("⚠️ [yellow]GPU Detectada pero no se pudo obtener información.[/yellow]")
        
        use_gpu = Confirm.ask("¿Desea utilizar la GPU (CUDA) para el entrenamiento?", default=True)
        if not use_gpu:
            console.print("[yellow]Reiniciando proceso en modo CPU puro para evitar conflictos con CUDA...[/yellow]")
            os.environ["FORCE_CPU"] = "1"
            os.execve(sys.executable, [sys.executable] + sys.argv, os.environ)
            
        device = "cuda"
    else:
        console.print("⚠️ [yellow]GPU no detectada o no disponible. Se utilizará la CPU.[/yellow]")
        console.print("   (El entrenamiento será considerablemente más lento)")
        device = "cpu"
        
    from config import config
    config.DEVICE = torch.device(device)
    return device

def select_asset_class():
    console.print("\n[bold yellow]Paso 2: Selección de Clase de Activo[/bold yellow]")
    asset_type = Prompt.ask(
        "Seleccione el tipo de mercado", 
        choices=["Futures", "Stocks", "Crypto", "ETF"], 
        default="Futures"
    )
    return asset_type

def select_ticker(asset_type):
    console.print(f"\n[bold yellow]Paso 3: Selección de Ticker ({asset_type})[/bold yellow]")
    
    if asset_type == "Futures":
        default_ticker = "MNQ=F"
        suggestions = "MNQ=F (Micro Nasdaq), MES=F (Micro S&P), NQ=F (Nasdaq), ES=F (S&P), GC=F (Gold), CL=F (Oil)"
    elif asset_type == "Stocks":
        default_ticker = "AAPL"
        suggestions = "AAPL, TSLA, NVDA, MSFT, AMZN, GOOGL"
    elif asset_type == "Crypto":
        default_ticker = "BTC-USD"
        suggestions = "BTC-USD, ETH-USD, SOL-USD, DOGE-USD, BNB-USD"
    elif asset_type == "ETF":
        default_ticker = "QQQ"
        suggestions = "QQQ (Nasdaq), SPY (S&P 500), GLD (Gold), ARKK (Innovation), SOXL (Semis)"
        
    console.print(f"[italic]Sugerencias: {suggestions}[/italic]")
    ticker = Prompt.ask("Ingrese el símbolo del activo", default=default_ticker)
    import re
    ticker = re.sub(r'[^A-Za-z0-9\=\-\.]', '', ticker).upper()
    return ticker

def select_parameters():
    console.print("\n[bold yellow]Paso 4: Configuración de Estrategia y Entrenamiento[/bold yellow]")
    
    console.print("\n[bold cyan]Seleccione el Modo de Estrategia (Timeframe & Arquitectura GAN):[/bold cyan]")
    console.print("1. [green]Scalping (1m)[/green] - GAN Ligera (Win: 60, Hidden: 64)")
    console.print("2. [blue]Intradía (5m)[/blue] - GAN Media (Win: 48, Hidden: 128)")
    console.print("3. [magenta]Intradía (15m)[/magenta] - GAN Estable (Win: 32, Hidden: 128)")
    console.print("4. [red]Swing (1h)[/red] - GAN Profunda (Win: 24, Hidden: 256)")
    console.print("5. [white]Personalizado[/white] - Configuración Manual")
    
    mode_choice = Prompt.ask("Opción", choices=["1", "2", "3", "4", "5"], default="4")
    
    # Defaults
    train_timeframe = "1h"
    trade_timeframe = "1h"
    seq_length = 60
    hidden_dim = 128
    num_layers = 2
    
    if mode_choice == "1": # Scalping 1m
        train_timeframe = "1m"
        trade_timeframe = "1m"
        seq_length = 60
        hidden_dim = 64
        num_layers = 2
    elif mode_choice == "2": # Intraday 5m
        train_timeframe = "5m"
        trade_timeframe = "5m"
        seq_length = 48
        hidden_dim = 128
        num_layers = 2
    elif mode_choice == "3": # Intraday 15m
        train_timeframe = "15m"
        trade_timeframe = "15m"
        seq_length = 32
        hidden_dim = 128
        num_layers = 2
    elif mode_choice == "4": # Swing 1h
        train_timeframe = "1h"
        trade_timeframe = "1h"
        seq_length = 24
        hidden_dim = 256
        num_layers = 3
    elif mode_choice == "5": # Custom
        train_timeframe = Prompt.ask("Timeframe de Entrenamiento", choices=["1m", "5m", "15m", "1h", "1d"], default="1h")
        trade_timeframe = Prompt.ask("Timeframe de Trading en Vivo", choices=["1m", "5m", "15m", "1h", "1d"], default="1m")
        seq_length = IntPrompt.ask("Ventana de Datos (Seq Length)", default=60)
        hidden_dim = IntPrompt.ask("Dimensión Oculta (Hidden Dim)", default=128)
        num_layers = IntPrompt.ask("Número de Capas LSTM", default=2)

    period = Prompt.ask("Periodo de datos históricos", choices=["1y", "2y", "5y", "max"], default="2y")
    epochs = IntPrompt.ask("Número de Épocas (Iteraciones)", default=50)
    
    return period, epochs, train_timeframe, trade_timeframe, seq_length, hidden_dim, num_layers

def get_available_timeframes(ticker):
    """Scans outputs/models for available timeframes for the given ticker"""
    safe_ticker = ticker.replace("=", "").replace("-", "")
    models_dir = "outputs/models"
    
    if not os.path.exists(models_dir):
        return []
        
    timeframes = []
    # Look for files like {safe_ticker}_{timeframe}_generator.pth
    for filename in os.listdir(models_dir):
        if filename.startswith(safe_ticker) and filename.endswith("_generator.pth"):
            # Extract timeframe: safe_ticker_TIMEFRAME_generator.pth
            try:
                parts = filename.split("_")
                # parts[0] is safe_ticker
                # parts[-1] is generator.pth (or parts[-2] if split by _)
                # The timeframe is in between. 
                # Example: MNQF_1h_generator.pth -> parts=["MNQF", "1h", "generator.pth"]
                if len(parts) >= 3:
                    tf = parts[1]
                    timeframes.append(tf)
            except:
                continue
                
    return sorted(list(set(timeframes)))

def select_timeframe(ticker):
    """Prompts user to select a timeframe if multiple exist"""
    timeframes = get_available_timeframes(ticker)
    
    if not timeframes:
        console.print(f"[yellow]⚠️ No se encontraron modelos específicos para {ticker}. Se intentará usar el modelo por defecto (1h).[/yellow]")
        return None
        
    if len(timeframes) == 1:
        console.print(f"[green]✅ Modelo encontrado: {timeframes[0]}[/green]")
        return timeframes[0]
        
    console.print(f"\n[bold cyan]Modelos disponibles para {ticker}:[/bold cyan]")
    for i, tf in enumerate(timeframes):
        console.print(f"{i+1}. {tf}")
        
    choice = Prompt.ask("Seleccione el timeframe a operar", choices=[str(i+1) for i in range(len(timeframes))], default="1")
    return timeframes[int(choice)-1]

def select_platform():
    console.print("\n[bold yellow]Selección de Plataforma de Trading[/bold yellow]")
    console.print("1. [blue]MetaTrader 5 (MT5)[/blue]")
    console.print("2. [green]NinjaTrader 8 (NT8)[/green]")
    console.print("3. [gold1]Binance (Crypto)[/gold1]")
    
    choice = Prompt.ask("Seleccione la plataforma", choices=["1", "2", "3"], default="1")
    
    if choice == "1":
        return "mt5"
    elif choice == "2":
        return "nt8"
    else:
        return "binance"

def select_volume():
    console.print("\n[bold yellow]Gestión de Riesgo y Volumen[/bold yellow]")
    volume_str = Prompt.ask("Ingrese la cantidad de lotaje/volumen para operar", default="1.0")
    try:
        return float(volume_str)
    except:
        return 1.0

def open_last_dashboard():
    dashboard_path = os.path.abspath("outputs/dashboard.html")
    if os.path.exists(dashboard_path):
        url = f"file://{dashboard_path}"
        console.print(f"\n[green]✓ Abriendo Dashboard local:[/green] [bold cyan]{url}[/bold cyan]")
        console.print("[dim]Si tu navegador no se abre automáticamente, puedes hacer Ctrl+Click en el enlace superior.[/dim]")
        webbrowser.open(url)
    else:
        console.print("\n[red]❌ No se encontró ningún dashboard generado previamente.[/red]")
        console.print("Ejecute un entrenamiento primero para generar el reporte.")

# Import live trading logic
# Import live trading logic
from live.live_trade import run_live_trading
import http.server
import socketserver
import threading
import json
import os

PORT = 8000
CONFIG_PATH = "config/live_config.json"

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'{}')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/update_config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                config_data = json.loads(post_data)
                # Ensure directory exists
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config_data, f, indent=4)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f'{{"status": "error", "message": "{str(e)}"}}'.encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        return # Suppress logs

def start_server():
    """Starts a custom HTTP server in a daemon thread"""
    try:
        with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
            httpd.serve_forever()
    except OSError:
        pass

# Start server on module load
server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()

def main():
    show_header()
    
    while True:
        console.print("\n[bold cyan]MENÚ PRINCIPAL[/bold cyan]")
        console.print("1. [bold green]🚀 Iniciar Nuevo Entrenamiento[/bold green]")
        console.print("2. [bold blue]📊 Ver Último Dashboard[/bold blue]")
        console.print("3. [bold gold1]⚙️ Configuración (Mapeo de Símbolos)[/bold gold1]")
        console.print("4. [bold red]🔴 Trading en Vivo[/bold red]")
        console.print("5. [bold magenta]🧹 Limpiar Datos y Reiniciar[/bold magenta]")
        console.print("6. [bold white]❌ Salir[/bold white]")
        
        choice = Prompt.ask("Seleccione una opción", choices=["1", "2", "3", "4", "5", "6"], default="1")
        
        if choice == "1":
            device = check_hardware()
            asset_type = select_asset_class()
            ticker = select_ticker(asset_type)
            period, epochs, train_timeframe, trade_timeframe, seq_length, hidden_dim, num_layers = select_parameters()
            
            console.print(f"\n[bold green]Resumen de Configuración:[/bold green]")
            console.print(f"• Clase: [cyan]{asset_type}[/cyan]")
            console.print(f"• Activo: [cyan]{ticker}[/cyan]")
            console.print(f"• Hardware: [magenta]{device.upper()}[/magenta]")
            console.print(f"• Periodo: [white]{period}[/white]")
            console.print(f"• Épocas: [white]{epochs}[/white]")
            console.print(f"• Timeframe Entrenamiento: [yellow]{train_timeframe}[/yellow]")
            console.print(f"• Timeframe Trading: [yellow]{trade_timeframe}[/yellow]")
            console.print(f"• Arquitectura GAN: [blue]Win={seq_length}, Hidden={hidden_dim}, Layers={num_layers}[/blue]")
            
            if Confirm.ask("\n¿Iniciar el proceso de entrenamiento?"):
                console.print("\n[bold blue]Iniciando Motor de IA...[/bold blue]")
                
                # Call the training function
                try:
                    train_model(ticker, period, epochs, asset_type, train_timeframe, trade_timeframe, seq_length, hidden_dim, num_layers)
                    console.print("\n[bold green]✨ Proceso Completado Exitosamente![/bold green]")
                    console.print("El Dashboard se abrirá automáticamente en tu navegador.")
                except Exception as e:
                    console.print(f"\n[bold red]Error Crítico:[/bold red] {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                console.print("[yellow]Operación cancelada por el usuario.[/yellow]")
                
        elif choice == "2":
            open_last_dashboard()
            
        elif choice == "3":
            configure_symbols()

        elif choice == "4":
            console.print("\n[bold red]🔴 MODO LIVE TRADING[/bold red]")
            
            # Select Platform
            platform = select_platform()
            
            asset_type = select_asset_class()
            ticker = select_ticker(asset_type)
            
            # Select Timeframe
            trade_timeframe = select_timeframe(ticker)
            
            # Select Volume
            volume = select_volume()
            
            # Open Live Dashboard via file:// protocol
            dashboard_path = os.path.abspath("live/live_dashboard.html")
            dashboard_url = f"file://{dashboard_path}"
            console.print(f"[green]✓ Abriendo Dashboard de Trading en Vivo local:[/green] [bold cyan]{dashboard_url}[/bold cyan]")
            console.print("[dim]Si tu navegador no se abre automáticamente, puedes hacer Ctrl+Click en el enlace superior.[/dim]")
            webbrowser.open(dashboard_url)
            
            # Start Loop
            run_live_trading(ticker, asset_type, platform=platform, timeframe=trade_timeframe, initial_volume=volume)
            
        elif choice == "5":
            clean_system_data()
            
        elif choice == "6":
            console.print("\n[yellow]¡Hasta luego![/yellow]")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Saliendo...[/red]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")

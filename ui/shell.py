"""
ui/shell.py — Shell REPL interactivo para el Sistema de Análisis Financiero.
Proporciona el bucle interactivo principal, autocompletado y enrutamiento de comandos.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.styles import Style as PromptStyle
from rich.console import Console
from rich.panel import Panel

# --- WINE COMPATIBILITY PATCH ---
# Wine's conhost.exe claims to support VT100 but leaks ANSI escape codes in prompt_toolkit.
# By forcing is_win_vt100_enabled to False under Wine, we force prompt_toolkit to use
# the Win32Output backend which Wine implements much more reliably.
if sys.platform == "win32" and ("WINEPREFIX" in os.environ or "WINELOADERNOEXEC" in os.environ):
    try:
        from prompt_toolkit.output import windows10
        windows10.is_win_vt100_enabled = lambda: False
    except ImportError:
        pass
# --------------------------------
from rich.table import Table
from rich.markdown import Markdown
from rich.box import ROUNDED

from core.config import config
from core.session import Session
from core.data_provider import DataProvider
from utils.logger import get_logger
from utils.validators import validate_timeframe, validate_period, validate_float

# Importaciones de análisis y renderizado
from analysis.support_resistance import full_sr_analysis
from analysis.fibonacci import full_fibonacci_analysis
from analysis.gann import full_gann_analysis
from analysis.imbalance import full_imbalance_analysis
from analysis.volatility import full_volatility_analysis
from analysis.volume_analysis import full_volume_analysis
from analysis.indicators import calculate_all_indicators
from analysis.market_structure import analyze_market_structure
from analysis.report_engine import generate_market_report
from analysis.quant import full_quant_analysis
from analysis.mean_reversion import full_mean_reversion_analysis

from core.order_builder import build_order, OrderSpec
from core.order_executor import order_executor

from ui.colors import get_style
from ui.formatters import format_price, format_percent, format_volume, colorize_text
from ui.tables import (
    make_sr_table,
    make_fibonacci_table,
    make_gann_table,
    make_imbalance_table,
    make_indicators_table,
    make_risk_setup_panel,
    make_quant_panel,
)
from ui.charts import show_terminal_chart, render_indicator_chart
from ui.dashboard import display_dashboard

logger = get_logger(__name__)
console = Console()


class AnalysisShell:
    """Consola REPL interactiva principal para el análisis financiero."""

    def __init__(self) -> None:
        self.session = Session()
        self.data_provider = DataProvider()
        
        # Historial de comandos persistente en el directorio cache/home
        history_path = Path.home() / ".flux_quant_history"
        self.prompt_session: PromptSession = PromptSession(
            history=FileHistory(str(history_path))
        )
        
        # Diccionario de autocompletado para prompt_toolkit
        self.completer = NestedCompleter.from_nested_dict({
            "help": None,
            "exit": None,
            "quit": None,
            "clear": None,
            "cls": None,
            "fetch": None,
            "dashboard": None,
            "test": {
                "connections": None,
                "binance": None,
                "mt5": None,
            },
            "set": {
                "symbol": None,
                "timeframe": {tf: None for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"]},
                "period": {p: None for p in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"]},
                "capital": None,
                "risk": None,
            },
            "analyze": {
                "sr": None,
                "volume": None,
                "fib": None,
                "gann": None,
                "imbalance": None,
                "volatility": None,
                "structure": None,
                "quant": None,
                "reversion": None,
                "all": None,
            },
            "indicator": {
                "rsi": None,
                "macd": None,
                "bb": None,
                "vwap": None,
                "ema": None,
                "sma": None,
                "all": None,
            },
            "chart": {
                "candles": None,
                "volume": None,
                "indicators": None,
                "rsi": None,
                "macd": None,
            },
            "report": {
                "signal": None,
                "risk": None,
            },
            "compare": None,
            "watchlist": {
                "add": None,
                "defaults": None,
                "load-defaults": None,
                "scan": None,
                "show": None,
                "clear": None,
            },
            "config": {
                "show": None,
                "set": None,
                "save": None,
            },
            "cache": {
                "clear": None,
                "status": None,
            },
            "export": {
                "csv": None,
                "report": None,
            },
            "order": {
                "send": {
                    "mt5": {"market": None, "limit": None},
                    "binance_spot": {"market": None, "limit": None},
                    "binance_futures": {"market": None, "limit": None},
                },
                "paper": {"on": None, "off": None},
                "history": None,
                "cancel": None,
                "status": None,
                "positions": None,
            }
        })
        
        # Estilos visuales del prompt
        self.prompt_style = PromptStyle.from_dict({
            "prompt": "bold cyan",
            "symbol": "bold yellow",
            "at": "dim white",
            "timeframe": "bold magenta",
            "arrow": "bold green",
        })

    def print_welcome(self) -> None:
        """Mensaje de bienvenida al iniciar."""
        ascii_f = r"""
[bold blue]
███████╗██╗     ██╗   ██╗██╗  ██╗
██╔════╝██║     ██║   ██║╚██╗██╔╝
█████╗  ██║     ██║   ██║ ╚███╔╝ 
██╔══╝  ██║     ██║   ██║ ██╔██╗ 
██║     ███████╗╚██████╔╝██╔╝ ██╗
╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
         Q  U  A  N  T
[/bold blue]
"""
        console.print(ascii_f)
        
        welcome_md = """
# 📈 FLUX Quant — Motor Interactivo de Análisis
---
* **Datos**: Binance/MetaTrader 5 con fallback a Yahoo Finance.
* **Motores**: Soportes/Resistencias, Volumen, Fibonacci, Gann, Imbalances (SMC), Volatilidad y Cuantitativo.
* **Ejecución**: Órdenes integradas a MT5 y Binance (Spot/Futuros).
* **Comandos**: Escribe `help` para ver la lista de comandos disponibles.
* **Autocompletado**: Usa la tecla [Tab] para completar comandos.
        """
        console.print(Markdown(welcome_md))
        # Cargar datos iniciales
        self.cmd_fetch([])

    def get_prompt_message(self) -> list:
        """Construye el mensaje dinámico del prompt."""
        symbol = self.session.symbol or "NINGUNO"
        tf = self.session.timeframe or "N/A"
        return [
            ("class:prompt", "FLUXQuant"),
            ("class:at", "@"),
            ("class:symbol", symbol),
            ("class:at", ":"),
            ("class:timeframe", tf),
            ("class:arrow", " > "),
        ]

    def run(self) -> None:
        """Bucle principal de lectura-evaluación-impresión (REPL)."""
        self.print_welcome()
        
        while True:
            try:
                # Solicitar comando al usuario
                user_input = self.prompt_session.prompt(
                    self.get_prompt_message(),
                    style=self.prompt_style,
                    completer=self.completer
                )
                
                # Limpiar espacios
                user_input = user_input.strip()
                if not user_input:
                    continue
                
                # Parsear comando
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd in ["exit", "quit", "q"]:
                    console.print("[yellow]Saliendo del sistema de análisis. ¡Buen trading![/yellow]")
                    break
                
                # Ejecutar comando
                self.execute_command(cmd, args)
                
            except KeyboardInterrupt:
                # Ctrl+C limpia la línea actual sin cerrar el programa
                console.print("\n[yellow]Operación cancelada. Escribe 'exit' para salir.[/yellow]")
                continue
            except EOFError:
                # Ctrl+D sale de la aplicación
                console.print("\n[yellow]Saliendo...[/yellow]")
                break
            except Exception as e:
                logger.exception("Error inesperado en el shell REPL")
                console.print(f"[bold red]Error al procesar el comando: {e}[/bold red]")

    def execute_command(self, cmd: str, args: list[str]) -> None:
        """Enruta el comando a su función correspondiente."""
        cmd_map = {
            "help": self.cmd_help,
            "clear": self.cmd_clear,
            "cls": self.cmd_clear,
            "set": self.cmd_set,
            "fetch": self.cmd_fetch,
            "analyze": self.cmd_analyze,
            "indicator": self.cmd_indicator,
            "chart": self.cmd_chart,
            "dashboard": self.cmd_dashboard,
            "test": self.cmd_test,
            "report": self.cmd_report,
            "compare": self.cmd_compare,
            "watchlist": self.cmd_watchlist,
            "config": self.cmd_config,
            "cache": self.cmd_cache,
            "export": self.cmd_export,
            "order": self.cmd_order,
        }
        
        func = cmd_map.get(cmd)
        if func:
            func(args)
        else:
            console.print(f"[bold red]Comando desconocido: '{cmd}'. Escribe 'help' para ver la lista de comandos.[/bold red]")

    # ──────────────────────────────────────────────────────────────
    # IMPLEMENTACIÓN DE COMANDOS
    # ──────────────────────────────────────────────────────────────

    def cmd_clear(self, args: list[str]) -> None:
        """Limpia la pantalla de la terminal."""
        os.system("clear" if os.name == "posix" else "cls")

    def cmd_help(self, args: list[str]) -> None:
        """Muestra la documentación de comandos."""
        help_text = """
### Comandos Disponibles:

* **set symbol <TICKER>**       : Cambia el activo actual (ej: `set symbol AAPL`, `set symbol BTC-USDT`).
* **set timeframe <TF>**        : Cambia el timeframe (ej: `set timeframe 4h`, `set timeframe 1d`).
* **set period <PER>**          : Período de datos históricos (ej: `set period 1y`, `set period 3mo`).
* **set capital <VALOR>**       : Cambia el tamaño de tu cuenta (ej: `set capital 100`).
* **set risk <PORCENTAJE>**     : Cambia el riesgo por trade (ej: `set risk 1`).
* **fetch**                     : Fuerza la descarga de datos históricos actualizados.
* **test connections**          : Verifica conectividad con Binance y MetaTrader 5.
* **dashboard**                 : Muestra el Dashboard multi-panel en tiempo real con gráfico.
* **report**                    : Genera el reporte consolidado completo del mercado.
* **chart candles**             : Dibuja un gráfico de velas japonesas en la terminal.

* **analyze <sr|volume|fib|gann|imbalance|volatility|structure|quant|reversion|all>** :
  Ejecuta un motor de análisis técnico específico (ej. 'analyze quant' para AI Institucional).

* **indicator <rsi|macd|bb|vwap|ema|sma|all>** :
  Calcula e imprime indicadores matemáticos individuales.

* **watchlist add <TICKER>**   : Agrega un activo a tu lista de seguimiento.
* **watchlist defaults**        : Precarga una watchlist multi-mercado por defecto.
* **watchlist scan**            : Escanea todos los activos en tu watchlist.
* **watchlist show**            : Muestra los elementos en tu watchlist.

* **compare <TICKER1> <TICKER2>...** : Compara rendimiento y volatilidad de varios activos.
* **order send [broker] [tipo]**  : Ejecuta una orden (ej: `order send mt5 market` o `order send binance_futures limit`)
* **order paper <on|off>**      : Cambia el modo entre Paper Trading y Live Trading.
* **order history**             : Muestra el historial de órdenes enviadas.
* **order positions**           : Muestra las posiciones abiertas actuales en MT5 y Binance.
* **config <show|save>**        : Ver o persistir la configuración de parámetros.
* **cache <clear|status>**      : Administrar la caché de datos local.
* **export <csv|report>**       : Exportar datos técnicos.
        """
        console.print(Markdown(help_text))

    def cmd_set(self, args: list[str]) -> None:
        """Establece parámetros de sesión (símbolo, timeframe, período, etc.)."""
        if not args or len(args) < 2:
            console.print("[bold red]Uso incorrecto. Ejemplos: 'set symbol BTC-USD', 'set timeframe 4h'[/bold red]")
            return
            
        param = args[0].lower()
        val = args[1].upper()

        if param == "symbol":
            self.session.symbol = val
            console.print(f"[green]Activo cambiado a: [bold]{val}[/bold][/green]")
            self.cmd_fetch([])  # Descargar datos para el nuevo activo
        elif param == "timeframe":
            valid, tf_val = validate_timeframe(val)
            if valid:
                self.session.timeframe = tf_val
                console.print(f"[green]Timeframe cambiado a: [bold]{tf_val}[/bold][/green]")
                self.cmd_fetch([])
            else:
                console.print(f"[bold red]{tf_val}[/bold red]")
        elif param == "period":
            valid, p_val = validate_period(val)
            if valid:
                self.session.period = p_val
                console.print(f"[green]Período de datos cambiado a: [bold]{p_val}[/bold][/green]")
                self.cmd_fetch([])
            else:
                console.print(f"[bold red]{p_val}[/bold red]")
        elif param == "capital":
            valid, cap = validate_float(val, "capital")
            if valid:
                self.session.capital = float(cap)
                console.print(f"[green]Capital de riesgo actualizado a: [bold]{format_price(cap)}[/bold][/green]")
            else:
                console.print(f"[bold red]{cap}[/bold red]")
        elif param == "risk":
            valid, rk = validate_float(val, "riesgo")
            if valid:
                self.session.risk_percent = float(rk)
                console.print(f"[green]Riesgo por operación actualizado a: [bold]{rk}%[/bold][/green]")
            else:
                console.print(f"[bold red]{rk}[/bold red]")
        else:
            console.print(f"[bold red]Parámetro de configuración desconocido: '{param}'[/bold red]")

    def cmd_fetch(self, args: list[str]) -> None:
        """Descarga datos históricos de Yahoo Finance."""
        symbol = self.session.symbol
        tf = self.session.timeframe
        period = self.session.period
        
        if not symbol:
            console.print("[yellow]No hay activo seleccionado. Usa 'set symbol <TICKER>' primero.[/yellow]")
            return

        with console.status(f"[bold green]Descargando datos históricos para {symbol} ({tf})...[/bold green]"):
            try:
                # Descargar datos
                df, info = self.data_provider.fetch(
                    symbol=symbol,
                    timeframe=tf,
                    period=period,
                    force_refresh=True
                )
                
                if df is not None and not df.empty:
                    df.attrs.update({
                        "symbol": info.get("symbol", symbol),
                        "asset_type": info.get("type"),
                        "source": info.get("source"),
                        "exchange": info.get("exchange"),
                    })
                    self.session.df = df
                    self.session.symbol_info = info
                    rows = len(df)
                    last_close = df["Close"].iloc[-1]
                    console.print(f"[bold green]✓[/bold green] [green]Datos cargados con éxito! [bold]{rows}[/bold] velas. Último Cierre: [bold]{format_price(last_close)}[/bold][/green]")
                else:
                    console.print(f"[bold red]❌ Error: No se pudieron recuperar datos para {symbol}. Verifica el símbolo.[/bold red]")
            except Exception as e:
                console.print(f"[bold red]❌ Error de descarga: {e}[/bold red]")

    def cmd_test(self, args: list[str]) -> None:
        """Verifica conexiones externas de datos."""
        subcmd = args[0].lower() if args else "connections"

        if subcmd not in {"connections", "binance", "mt5"}:
            console.print("[bold red]Uso: test connections | test binance | test mt5[/bold red]")
            return

        def print_result(name: str, result: dict) -> None:
            if result.get("ok"):
                details = []
                if result.get("symbols") is not None:
                    details.append(f"{result['symbols']} símbolos")
                if result.get("version") is not None:
                    details.append(f"versión {result['version']}")
                suffix = f" ({', '.join(details)})" if details else ""
                console.print(f"[green]✓ {name}: conectado{suffix}[/green]")
            else:
                console.print(f"[yellow]⚠ {name}: {result.get('error', 'no disponible')}[/yellow]")

        if subcmd in {"connections", "binance"}:
            from core.binance_provider import test_connection as test_binance_connection
            print_result("Binance", test_binance_connection())

        if subcmd in {"connections", "mt5"}:
            from core.mt5_provider import test_connection as test_mt5_connection
            print_result("MetaTrader 5", test_mt5_connection())

    def _check_data(self) -> bool:
        """Verifica si la sesión tiene datos cargados."""
        if not self.session.has_data():
            console.print("[bold red]Error: No hay datos cargados. Ejecuta 'fetch' o selecciona un activo con 'set symbol <TICKER>'[/bold red]")
            return False
        return True

    def cmd_analyze(self, args: list[str]) -> None:
        """Ejecuta un motor de análisis y renderiza su tabla correspondiente."""
        if not self._check_data():
            return
            
        subcmd = args[0].lower() if args else "all"
        df = self.session.df
        
        if subcmd == "sr":
            res = full_sr_analysis(df)
            console.print(make_sr_table(res))
        elif subcmd == "fib":
            res = full_fibonacci_analysis(df)
            console.print(make_fibonacci_table(res))
        elif subcmd == "gann":
            res = full_gann_analysis(df)
            console.print(make_gann_table(res))
        elif subcmd == "imbalance":
            res = full_imbalance_analysis(df)
            console.print(make_imbalance_table(res))
        elif subcmd == "volatility":
            res = full_volatility_analysis(df, self.session.capital, self.session.risk_percent)
            texto = (
                f"ATR: {format_price(res['atr'])}\n"
                f"ATR %: {res['atr_pct']:.2f}%\n"
                f"Régimen: {res['volatility_regime']['regime']} (Z-Score: {res['volatility_regime']['z_score']:.2f})\n"
                f"Posición Sugerida: {format_volume(res['position_size']['suggested_position_size'])}"
            )
            console.print(Panel(texto, title="Volatilidad y Tamaño de Posición", border_style="yellow"))
        elif subcmd == "structure":
            res = analyze_market_structure(df)
            res["source"] = "structure"
            self.session.last_analysis = res
            texto = (
                f"Tendencia: {res['trend']}\n"
                f"Último BOS: {res['last_bos']['type'] if res['last_bos'] else 'N/A'}\n"
                f"Último CHoCH: {res['last_choch']['type'] if res['last_choch'] else 'N/A'}"
            )
            console.print(Panel(texto, title="Estructura de Mercado (SMC)", border_style="green"))
        elif subcmd == "quant":
            res = full_quant_analysis(df, self.session.capital, self.session.risk_percent)
            res["source"] = "quant"
            self.session.last_analysis = res
            console.print(make_quant_panel(res))
        elif subcmd == "reversion":
            res = full_mean_reversion_analysis(df)
            res["source"] = "mean_reversion"
            self.session.last_analysis = res
            if "error" in res:
                console.print(Panel(f"[red]{res['error']}[/red]", title="Reversión a la Media"))
            else:
                texto = (
                    f"Z-Score (VWAP): {res.get('z_score', 0):.2f}\n"
                    f"VWAP: {format_price(res.get('vwap', 0))}\n"
                    f"Media de vida (Half-Life): {res.get('half_life_bars', 0)}\n"
                    f"Régimen de reversión: {'Sí' if res.get('is_mean_reverting_regime') else 'No'}\n"
                    f"Señal: {res.get('signal_type', 'N/A')} (Score: {res.get('signal_score', 0)})\n"
                    f"Objetivo: {format_price(res.get('target_price', 0))}"
                )
                console.print(Panel(texto, title="Reversión a la Media", border_style="cyan"))
        elif subcmd == "volume":
            res = full_volume_analysis(df)
            console.print(Panel(f"POC de Volumen: {format_price(res['profile']['poc'])}\nVAH: {format_price(res['profile']['vah'])}\nVAL: {format_price(res['profile']['val'])}", title="Volume Profile"))
        elif subcmd == "all":
            self.cmd_report([])
        else:
            console.print(f"[bold red]Motor de análisis desconocido: '{subcmd}'. Opciones: sr, volume, fib, gann, imbalance, volatility, structure, quant, reversion, all.[/bold red]")

    def cmd_indicator(self, args: list[str]) -> None:
        """Calcula y muestra indicadores clásicos."""
        if not self._check_data():
            return
            
        subcmd = args[0].lower() if args else "all"
        df = self.session.df
        
        if subcmd == "all":
            res = calculate_all_indicators(df)
            console.print(make_indicators_table(res))
        else:
            # Mostrar indicador específico
            res = calculate_all_indicators(df)
            if subcmd == "rsi":
                console.print(f"RSI (14): {res['rsi']['value']} ({res['rsi']['state']})")
            elif subcmd == "macd":
                console.print(f"MACD: {res['macd']['macd']} | Signal: {res['macd']['signal']} ({res['macd']['state']})")
            elif subcmd == "stoch":
                console.print(f"Stochastic %K: {res['stochastic']['k']} | %D: {res['stochastic']['d']}")
            elif subcmd == "adx":
                console.print(f"ADX: {res['adx']['adx']} ({res['adx']['strength']}) | Tendencia: {res['adx']['direction']}")
            else:
                console.print(f"[bold red]Indicador desconocido: '{subcmd}'. Opciones: rsi, macd, stoch, adx, all.[/bold red]")

    def cmd_chart(self, args: list[str]) -> None:
        """Dibuja el gráfico técnico en la terminal.
        
        Subcomandos:
          chart candles     — Velas + Volumen + EMAs (9, 21, 50)
          chart rsi         — RSI(14) en gráfico de línea
          chart macd        — MACD + Signal + Histograma
          (sin args)        — Equivale a 'chart candles'
        """
        if not self._check_data():
            return

        df = self.session.df.copy()
        subcmd = args[0].lower() if args else "candles"

        if subcmd in ("candles", "volume", "indicators"):
            # EMAs para superponer
            ind_df = pd.DataFrame(index=df.index)
            ind_df["EMA_9"]  = df["Close"].ewm(span=9,   adjust=False).mean()
            ind_df["EMA_21"] = df["Close"].ewm(span=21,  adjust=False).mean()
            ind_df["EMA_50"] = df["Close"].ewm(span=50,  adjust=False).mean()

            show_terminal_chart(
                df=df,
                symbol=self.session.symbol,
                timeframe=self.session.timeframe,
                indicators_df=ind_df,
                show_volume=(subcmd != "indicators"),
            )

        elif subcmd == "rsi":
            # RSI de 14 períodos
            close = df["Close"]
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss.replace(0, float("nan"))
            rsi   = 100 - (100 / (1 + rs))
            chart = render_indicator_chart(
                {"RSI(14)": rsi},
                title=f"RSI(14) — {self.session.symbol} [{self.session.timeframe}]",
            )
            print(chart)

        elif subcmd == "macd":
            close  = df["Close"]
            ema12  = close.ewm(span=12, adjust=False).mean()
            ema26  = close.ewm(span=26, adjust=False).mean()
            macd_l = ema12 - ema26
            signal = macd_l.ewm(span=9,  adjust=False).mean()
            chart  = render_indicator_chart(
                {"MACD": macd_l, "Signal": signal},
                title=f"MACD — {self.session.symbol} [{self.session.timeframe}]",
            )
            print(chart)

        else:
            console.print(f"[bold red]Subcomando de chart desconocido: '{subcmd}'. Opciones: candles, rsi, macd[/bold red]")

    def cmd_dashboard(self, args: list[str]) -> None:
        """Muestra el Dashboard Web Profesional en el navegador."""
        import webbrowser
        import urllib.request
        import time
        import subprocess

        url = "http://127.0.0.1:8555"
        console.print("[bold green]Abriendo Dashboard Web Profesional...[/bold green]")

        def is_server_running():
            try:
                urllib.request.urlopen(url, timeout=1)
                return True
            except Exception:
                return False

        if not is_server_running():
            console.print("[yellow]Iniciando servidor web en segundo plano...[/yellow]")
            # Iniciar el proceso de uvicorn en segundo plano
            subprocess.Popen([sys.executable, "main.py", "web"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Esperar a que levante
            for _ in range(10):
                time.sleep(0.5)
                if is_server_running():
                    break

        webbrowser.open(url)
        console.print(f"[green]✓ Dashboard abierto en tu navegador: {url}[/green]")

    def cmd_report(self, args: list[str]) -> None:
        """Muestra un reporte técnico de texto estructurado y coloreado en consola."""
        if not self._check_data():
            return

        report = generate_market_report(
            self.session.df,
            self.session.symbol,
            self.session.timeframe,
            self.session.capital,
            self.session.risk_percent
        )
        report["source"] = "report"
        self.session.last_analysis = report

        results = report["results"]

        # Encabezado largo
        console.print(Panel(
            f"Activo: [bold yellow]{report['symbol']}[/bold yellow]  |  Timeframe: [cyan]{report['timeframe']}[/cyan]  |  Precio: [green]{format_price(report['price'])}[/green]\nFecha del reporte: {report['date']}",
            title="📋 REPORTE CONSOLIDADO DE MERCADO",
            border_style="cyan",
            box=ROUNDED
        ))

        # Imprimir las tablas de forma secuencial
        console.print(make_sr_table(results["sr"]))
        console.print(make_imbalance_table(results["imbalance"]))
        console.print(make_indicators_table(results["indicators"]))
        console.print(make_risk_setup_panel(report["setup"]))
        
        console.print("\n[dim italic]Pista: Puedes usar el comando 'order send' para ejecutar la señal generada.[/dim italic]")

    def cmd_compare(self, args: list[str]) -> None:
        """Compara una lista de activos."""
        if not args:
            console.print("[bold red]Uso: compare <TICKER1> <TICKER2> <TICKER3>...[/bold red]")
            return

        # Limpiar comas que el usuario pueda haber incluido accidentalmente
        tickers = [a.strip(",").upper() for a in args if a.strip(",")]

        table = Table(title="📈 TABLA COMPARATIVA DE ACTIVOS", box=ROUNDED)
        table.add_column("Ticker", style="bold yellow")
        table.add_column("Último Precio", justify="right")
        table.add_column("Cambio Período", justify="right")
        table.add_column("ATR % (Volatilidad)", justify="right")
        table.add_column("Tendencia SMC", justify="center")

        with console.status("[bold green]Descargando y analizando activos...[/bold green]"):
            for sym in tickers:
                try:
                    df, _ = self.data_provider.fetch(sym, self.session.timeframe, "3mo")
                    if df is not None and not df.empty:
                        # Rendimiento
                        p_start = df["Close"].iloc[0]
                        p_end   = df["Close"].iloc[-1]
                        perf    = ((p_end - p_start) / p_start) * 100

                        # Volatilidad ATR  ← key corregida: 'atr_pct'
                        vol_res = full_volatility_analysis(df, 10000, 1)
                        atr_pct = vol_res.get("atr_pct", vol_res.get("atr_percent", 0.0))

                        # Tendencia
                        trend = analyze_market_structure(df)["trend"].upper()
                        trend_color = (
                            "green"  if trend == "ALCISTA" else
                            "red"    if trend == "BAJISTA" else
                            "yellow"
                        )
                        trend_styled = f"[{trend_color}]{trend}[/{trend_color}]"

                        table.add_row(
                            sym,
                            format_price(p_end),
                            format_percent(perf),
                            f"{atr_pct:.2f}%",
                            trend_styled,
                        )
                    else:
                        table.add_row(sym, "[dim]Sin datos[/dim]", "-", "-", "-")
                except Exception as e:
                    logger.warning(f"No se pudo comparar el activo {sym}: {e}")
                    table.add_row(sym, f"[red]Error: {e}[/red]", "-", "-", "-")

        if table.row_count == 0:
            console.print("[yellow]No se obtuvieron datos para ningún activo.[/yellow]")
        else:
            console.print(table)

    def cmd_watchlist(self, args: list[str]) -> None:
        """Gestiona la watchlist de activos del usuario."""
        if not args:
            console.print("[bold red]Uso: 'watchlist add <TICKER>', 'watchlist defaults', 'watchlist show', 'watchlist scan', 'watchlist clear'[/bold red]")
            return

        subcmd = args[0].lower()
        if subcmd == "add":
            if len(args) < 2:
                console.print("[bold red]Especifica el ticker. Ej: watchlist add ETH-USD[/bold red]")
                return
            ticker = args[1].upper()
            if ticker not in self.session.watchlist:
                self.session.watchlist.append(ticker)
                console.print(f"[green]✓ Activo [bold]{ticker}[/bold] agregado a la watchlist.[/green]")
            else:
                console.print(f"[yellow]El activo {ticker} ya está en la watchlist.[/yellow]")
        elif subcmd in {"defaults", "load-defaults"}:
            defaults = config.get("watchlist.default_symbols", [])
            added = 0
            for ticker in defaults:
                ticker = str(ticker).upper()
                if ticker and ticker not in self.session.watchlist:
                    self.session.watchlist.append(ticker)
                    added += 1
            console.print(f"[green]✓ Watchlist por defecto cargada: [bold]{added}[/bold] activos nuevos.[/green]")
            console.print(f"[dim]MT5 usa alias configurables por broker en config.toml → [bold]mt5.symbol_aliases[/bold].[/dim]")
        elif subcmd == "show":
            if not self.session.watchlist:
                console.print("[yellow]La watchlist está vacía.[/yellow]")
            else:
                console.print(f"Watchlist actual: [bold yellow]{', '.join(self.session.watchlist)}[/bold yellow]")
        elif subcmd == "scan":
            if not self.session.watchlist:
                console.print("[yellow]La watchlist está vacía. Agrega activos usando 'watchlist add <TICKER>'.[/yellow]")
                return
            self.cmd_compare(self.session.watchlist)
        elif subcmd == "clear":
            self.session.watchlist.clear()
            console.print("[green]Watchlist vaciada.[/green]")

    def cmd_config(self, args: list[str]) -> None:
        """Muestra o modifica la configuración actual del archivo TOML."""
        if not args:
            console.print("[bold red]Uso: 'config show' o 'config save'[/bold red]")
            return

        subcmd = args[0].lower()
        if subcmd == "show":
            # Imprimir llaves de configuración de forma legible
            table = Table(title="⚙️ CONFIGURACIÓN ACTUAL (config.toml)", box=ROUNDED)
            table.add_column("Sección / Parámetro", style="bold cyan")
            table.add_column("Valor", style="bold white")
            
            # Recorremos la configuración cargada
            for section in config._data:
                for key, val in config._data[section].items():
                    table.add_row(f"{section}.{key}", str(val))
            console.print(table)
        elif subcmd == "save":
            config.save()
            console.print("[green]✓ Configuración guardada en config.toml[/green]")

    def cmd_cache(self, args: list[str]) -> None:
        """Administra la caché local de Parquet."""
        if not args:
            console.print("[bold red]Uso: 'cache status' o 'cache clear'[/bold red]")
            return
            
        subcmd = args[0].lower()
        cache_dir = Path(config.get("data.cache_dir", ".cache"))
        
        if subcmd == "status":
            if cache_dir.exists():
                files = list(cache_dir.glob("*.parquet"))
                size = sum(f.stat().st_size for f in files)
                console.print(f"Caché activa en: [cyan]{cache_dir.absolute()}[/cyan]")
                console.print(f"Archivos Parquet guardados: [bold yellow]{len(files)}[/bold yellow]")
                console.print(f"Tamaño total de la caché: [bold yellow]{size / 1024:.2f} KB[/bold yellow]")
            else:
                console.print("[yellow]El directorio de caché no existe aún.[/yellow]")
        elif subcmd == "clear":
            if cache_dir.exists():
                for f in cache_dir.glob("*.parquet"):
                    f.unlink()
                console.print("[green]✓ Caché de archivos Parquet limpiada correctamente.[/green]")
            else:
                console.print("[yellow]No hay archivos de caché para limpiar.[/yellow]")

    def cmd_export(self, args: list[str]) -> None:
        """Exporta los datos de análisis activos."""
        if not self._check_data():
            return
            
        if not args:
            console.print("[bold red]Uso: 'export csv' o 'export report'[/bold red]")
            return

        subcmd = args[0].lower()
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        symbol = self.session.symbol
        tf = self.session.timeframe
        
        if subcmd == "csv":
            filename = export_dir / f"{symbol}_{tf}_data.csv"
            self.session.df.to_csv(filename)
            console.print(f"[green]✓ Datos exportados a CSV en: [bold]{filename.absolute()}[/bold][/green]")
        elif subcmd == "report":
            # Generar reporte completo de texto
            filename = export_dir / f"{symbol}_{tf}_report.txt"
            report = generate_market_report(
                self.session.df,
                self.session.symbol,
                self.session.timeframe,
                self.session.capital,
                self.session.risk_percent
            )
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"REPORTE CONSOLIDADO - {symbol} [{tf}]\n")
                f.write(f"Fecha: {report['date']}\n")
                f.write(f"Precio: {report['price']}\n")
                f.write(f"Señal: {report['direction']} (Compra: {report['score_buy']}/100, Venta: {report['score_sell']}/100)\n\n")
                setup = report["setup"]
                f.write("SETUP RECOMENDADO:\n")
                for k, v in setup.items():
                    f.write(f"  {k}: {v}\n")
            console.print(f"[green]✓ Reporte exportado a texto en: [bold]{filename.absolute()}[/bold][/green]")

    def cmd_order(self, args: list[str]) -> None:
        """Gestiona la ejecución de órdenes (MT5, Binance)."""
        if not args:
            console.print("[yellow]Uso: order <send|status|paper|history|cancel> ...[/yellow]")
            return
            
        subcmd = args[0].lower()
        
        if subcmd == "status":
            mode = order_executor.mode
            color = "green" if mode == "paper" else "red"
            broker = config.get("trading.default_broker", "mt5")
            console.print(Panel(f"Modo: [bold {color}]{mode.upper()}[/bold {color}]\nBroker predeterminado: {broker}", title="Estado de Órdenes"))
            return
            
        elif subcmd == "paper":
            if len(args) < 2 or args[1] not in ["on", "off"]:
                console.print("[yellow]Uso: order paper <on|off>[/yellow]")
                return
            new_mode = "paper" if args[1] == "on" else "live"
            config.set("trading.mode", new_mode)
            color = "green" if new_mode == "paper" else "red bold"
            console.print(f"Modo de trading cambiado a: [{color}]{new_mode.upper()}[/{color}]")
            if new_mode == "live":
                console.print("[bold red]⚠️  ATENCIÓN: LAS ÓRDENES SE ENVIARÁN AL BROKER REAL. ⚠️[/bold red]")
            return
            
        elif subcmd == "history":
            try:
                n = int(args[1]) if len(args) > 1 else 10
            except ValueError:
                n = 10
                
            history = order_executor.get_history(n)
            if not history:
                console.print("[dim]No hay órdenes recientes.[/dim]")
                return
                
            table = Table(title="Historial de Órdenes")
            table.add_column("Fecha")
            table.add_column("Modo")
            table.add_column("Broker")
            table.add_column("Símbolo")
            table.add_column("Lado")
            table.add_column("Estado")
            
            for h in reversed(history):
                date = h.get("timestamp", "").split("T")[0]
                ok_color = "green" if h.get("ok") else "red"
                side_color = "green" if h.get("side") == "BUY" else "red"
                
                table.add_row(
                    date,
                    h.get("mode", ""),
                    h.get("broker", ""),
                    h.get("symbol", ""),
                    f"[{side_color}]{h.get('side', '')}[/{side_color}]",
                    f"[{ok_color}]{'OK' if h.get('ok') else 'ERROR'}[/{ok_color}]"
                )
            console.print(table)
            return

        elif subcmd == "send":
            if not self.session.has_data():
                console.print("[red]Error: No hay datos cargados. Usa 'fetch' primero.[/red]")
                return
                
            if not self.session.last_analysis:
                console.print("[yellow]No hay un análisis reciente. Ejecuta 'analyze <tipo>' primero.[/yellow]")
                return
                
            broker = args[1] if len(args) > 1 else config.get("trading.default_broker", "mt5")
            order_type = args[2].upper() if len(args) > 2 else "MARKET"
            
            source = self.session.last_analysis.get("source", "manual")
            entry_price = None
            if order_type == "LIMIT":
                try:
                    p = console.input(f"Precio de Entrada (Actual: {format_price(self.session.current_price())}): ")
                    entry_price = float(p.replace(',', ''))
                except ValueError:
                    console.print("[red]Precio inválido.[/red]")
                    return
                    
            try:
                rr_input = console.input("Ratio Riesgo/Beneficio (R:R) [2.0]: ")
                rr_ratio = float(rr_input.replace(',', '.')) if rr_input.strip() else 2.0
            except ValueError:
                console.print("[red]Valor inválido, usando 2.0[/red]")
                rr_ratio = 2.0
                
            spec = build_order(
                symbol=self.session.symbol,
                current_price=self.session.current_price() or 0.0,
                df=self.session.df,
                analysis_results=self.session.last_analysis,
                source=source,
                capital=self.session.capital,
                risk_pct=self.session.risk_percent,
                order_type=order_type,
                entry_price=entry_price,
                rr_ratio=rr_ratio
            )
            
            if not spec:
                console.print("[yellow]El análisis actual no generó una señal clara o confiable.[/yellow]")
                return
                
            # Mostrar resumen
            table = Table(title="📋 Confirmación de Orden")
            table.add_column("Parámetro", style="cyan")
            table.add_column("Valor")
            
            side_color = "green" if spec.side == "BUY" else "red"
            
            table.add_row("Símbolo", spec.symbol)
            table.add_row("Lado", f"[{side_color} bold]{spec.side}[/{side_color} bold]")
            table.add_row("Tipo", spec.order_type)
            if spec.entry_price:
                table.add_row("Entrada (Limit)", format_price(spec.entry_price))
            else:
                table.add_row("Entrada (Mercado aprox)", format_price(self.session.current_price() or 0.0))
                
            table.add_row("Stop Loss", f"[red]{format_price(spec.sl)}[/red]")
            table.add_row("Take Profit 1", f"[green]{format_price(spec.tp1)}[/green]")
            if spec.tp2:
                table.add_row("Take Profit 2", f"[dim green]{format_price(spec.tp2)}[/dim green]")
                
            table.add_row("Tamaño (USD)", f"${spec.size_usd:.2f}")
            table.add_row("Señal", spec.notes)
            
            mode = order_executor.mode
            mode_str = f"[bold red]LIVE[/bold red] en {broker}" if mode == "live" else f"[bold green]PAPER[/bold green] ({broker})"
            
            panel = Panel(table, title=mode_str, border_style="red" if mode == "live" else "green")
            console.print(panel)
            
            confirm = console.input("¿Confirmar envío de orden? [y/N]: ").strip().lower()
            if confirm in ("y", "yes", "s", "si", "sí"):
                console.print(f"[cyan]Enviando orden a {broker}...[/cyan]")
                res = order_executor.send(spec, broker)
                if res.get("ok"):
                    console.print(f"[bold green]✅ Orden enviada exitosamente[/bold green] (ID: {res.get('order_id')})")
                else:
                    console.print(f"[bold red]❌ Error enviando orden:[/bold red] {res.get('error')}")
            else:
                console.print("[yellow]Orden cancelada por el usuario.[/yellow]")
                
        elif subcmd == "positions":
            with console.status("[bold green]Obteniendo posiciones...[/bold green]"):
                mt5_pos = order_executor.get_mt5_positions()
                binance_pos = order_executor.get_binance_positions()
                
            all_pos = mt5_pos + binance_pos
            if not all_pos:
                console.print("[dim]No hay posiciones abiertas.[/dim]")
                return
                
            table = Table(title="📈 Posiciones Abiertas", box=ROUNDED)
            table.add_column("Plataforma", style="cyan")
            table.add_column("Símbolo", style="bold yellow")
            table.add_column("Tamaño", justify="right")
            table.add_column("PnL", justify="right")
            
            total_pnl = 0.0
            for pos in all_pos:
                pnl = pos['pnl']
                total_pnl += pnl
                pnl_color = "green" if pnl >= 0 else "red"
                table.add_row(
                    pos["platform"],
                    pos["symbol"],
                    str(pos["size"]),
                    f"[{pnl_color}]{pnl:+.2f}[/{pnl_color}]"
                )
                
            total_color = "bold green" if total_pnl >= 0 else "bold red"
            table.add_row("Total", "", "", f"[{total_color}]{total_pnl:+.2f}[/{total_color}]", style="bold")
            
            console.print(table)
            
        else:
            console.print(f"[red]Comando no reconocido: order {subcmd}[/red]")

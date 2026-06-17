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

from ui.colors import get_style
from ui.formatters import format_price, format_percent, format_volume, colorize_text
from ui.tables import (
    make_sr_table,
    make_fibonacci_table,
    make_gann_table,
    make_imbalance_table,
    make_indicators_table,
    make_risk_setup_panel,
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
        history_path = Path.home() / ".analisis_activos_history"
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
        welcome_md = """
# 📈 Sistema de Análisis Técnico Profesional (Terminal)
---
Bienvenido al motor interactivo de análisis de mercados. 

* **Datos**: Alimentado en tiempo real por Yahoo Finance.
* **Motores**: Soportes/Resistencias, Volumen (VPVR/VWAP), Fibonacci, Gann, Imbalances (SMC) y Volatilidad.
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
            ("class:prompt", "AnalisisActivos"),
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
            "report": self.cmd_report,
            "compare": self.cmd_compare,
            "watchlist": self.cmd_watchlist,
            "config": self.cmd_config,
            "cache": self.cmd_cache,
            "export": self.cmd_export,
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

* **set symbol <TICKER>**       : Cambia el activo actual (ej: `set symbol AAPL`, `set symbol BTC-USD`).
* **set timeframe <TF>**        : Cambia el timeframe (ej: `set timeframe 4h`, `set timeframe 1d`).
* **set period <PER>**          : Período de datos históricos (ej: `set period 1y`, `set period 3mo`).
* **fetch**                     : Fuerza la descarga de datos históricos actualizados.
* **dashboard**                 : Muestra el Dashboard multi-panel en tiempo real con gráfico.
* **report**                    : Genera el reporte consolidado completo del mercado.
* **chart candles**             : Dibuja un gráfico de velas japonesas en la terminal.

* **analyze <sr|volume|fib|gann|imbalance|volatility|structure|all>** :
  Ejecuta un motor de análisis técnico específico.

* **indicator <rsi|macd|bb|vwap|ema|sma|all>** :
  Calcula e imprime indicadores matemáticos individuales.

* **watchlist add <TICKER>**   : Agrega un activo a tu lista de seguimiento.
* **watchlist scan**            : Escanea todos los activos en tu watchlist.
* **watchlist show**            : Muestra los elementos en tu watchlist.

* **compare <TICKER1> <TICKER2>...** : Compara rendimiento y volatilidad de varios activos.
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
                    self.session.df = df
                    self.session.symbol_info = info
                    rows = len(df)
                    last_close = df["Close"].iloc[-1]
                    console.print(f"[bold green]✓[/bold green] [green]Datos cargados con éxito! [bold]{rows}[/bold] velas. Último Cierre: [bold]{format_price(last_close)}[/bold][/green]")
                else:
                    console.print(f"[bold red]❌ Error: No se pudieron recuperar datos para {symbol}. Verifica el símbolo.[/bold red]")
            except Exception as e:
                console.print(f"[bold red]❌ Error de descarga: {e}[/bold red]")

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
            console.print(Panel(f"ATR (14): {format_price(res['atr'])} ({res['atr_percent']:.2f}%)\nStop Loss Sugerido: {format_price(res['stop_loss_distance'])}", title="Volatilidad"))
        elif subcmd == "structure":
            res = analyze_market_structure(df)
            console.print(Panel(f"Tendencia Estructural: {res['trend'].upper()}\nÚltimo BOS: {res['last_bos']}\nÚltimo CHoCH: {res['last_choch']}", title="Estructura de Mercado"))
        elif subcmd == "volume":
            res = full_volume_analysis(df)
            console.print(Panel(f"POC de Volumen: {format_price(res['profile']['poc'])}\nVAH: {format_price(res['profile']['vah'])}\nVAL: {format_price(res['profile']['val'])}", title="Volume Profile"))
        elif subcmd == "all":
            self.cmd_report([])
        else:
            console.print(f"[bold red]Motor de análisis desconocido: '{subcmd}'. Opciones: sr, volume, fib, gann, imbalance, volatility, structure, all.[/bold red]")

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
        """Muestra el Dashboard consolidado en pantalla completa."""
        if not self._check_data():
            return
            
        report = generate_market_report(
            self.session.df,
            self.session.symbol,
            self.session.timeframe,
            self.session.capital,
            self.session.risk_percent
        )
        display_dashboard(report, self.session.df)
        # Esperar tecla del usuario para salir del dashboard
        input("\n[Presiona Enter para volver a la línea de comandos]")
        os.system("clear" if os.name == "posix" else "cls")

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
            console.print("[bold red]Uso: 'watchlist add <TICKER>', 'watchlist show', 'watchlist scan', 'watchlist clear'[/bold red]")
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

"""
strategies/asian_session/run.py — CLI entry point.

Interactive terminal UI for the Asian Session Breakout strategy.
Prompts for symbol and lot size, then runs a live loop:
fetch data -> process Asian range -> check breakout -> execute signal.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt
from rich.table import Table

from core.config import config
from core.data_provider import DataProvider
from core.order_executor import order_executor
from strategies.asian_session.asian_breakout_strategy import AsianBreakoutStrategy


def load_strategy_config() -> dict:
    raw = config.get("asian_session", {})
    if not raw:
        return {}
    return {
        "symbols": raw.get("symbols", ["MES=F", "MNQ=F"]),
        "max_trades_per_day": raw.get("max_trades_per_day", 2),
        "min_atr_percentile": raw.get("min_atr_percentile", 60),
        "atr_sl_multiplier": raw.get("atr_sl_multiplier", 1.5),
        "rr_target_1": raw.get("rr_target_1", 2.0),
        "rr_target_2": raw.get("rr_target_2", 3.0),
        "cooldown_minutes": raw.get("cooldown_minutes", 30),
        "data_timeframe": raw.get("data_timeframe", "5m"),
        "entry_timeframe": raw.get("entry_timeframe", "1m"),
        "news_filter_enabled": raw.get("news_filter_enabled", True),
        "news_block_minutes": raw.get("news_block_minutes", 30),
    }


def _load_symbol_categories() -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {
        "Futuros (MT5)": config.get("screener.futures_symbols", ["ES=F", "NQ=F", "YM=F", "RTY=F", "GC=F", "CL=F"]),
        "Forex (MT5)": config.get("screener.forex_symbols", ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]),
        "Crypto (Binance)": config.get("screener.crypto_symbols", ["BTC-USD", "ETH-USD", "SOL-USD"]),
        "Commodities (MT5)": config.get("screener.commodity_symbols", ["GC=F", "SI=F", "CL=F", "NG=F"]),
        "Índices (yfinance)": config.get("screener.indices_symbols", ["^GSPC", "^NDX", "^DJI"]),
    }
    watchlist = config.get("watchlist.default_symbols", [])
    if watchlist:
        cats["Watchlist (MT5)"] = watchlist
    return cats


def _show_symbol_table(console: Console, categories: dict[str, list[str]]) -> None:
    table = Table(title="Símbolos disponibles por categoría", box=None, padding=(0, 2), title_style="bold cyan")
    table.add_column("Categoría", style="yellow bold", no_wrap=True)
    table.add_column("Símbolos", style="white")
    for cat, syms in categories.items():
        if syms:
            table.add_row(cat, "  ".join(f"[bold green]{s}[/bold green]" for s in syms))
    console.print(table)
    console.print("[dim]Podés escribir cualquier símbolo que acepte tu broker (MT5, Binance, NinjaTrader, yfinance).[/dim]")


def main() -> None:
    console = Console()
    mode = order_executor.mode.upper()

    console.print(Panel(
        "[bold cyan]ASIAN SESSION BREAKOUT ENGINE v1.0.0[/bold cyan]\n"
        "[white]Estrategia basada en rango asiático — soporta futuros, forex, cryptos[/white]\n\n"
        f"Modo de Operación: "
        + ("[bold green]REAL (LIVE)[/bold green]" if mode == "LIVE"
           else "[bold yellow]SIMULADO (PAPER)[/bold yellow]"),
        border_style="cyan",
    ))

    cats = _load_symbol_categories()
    _show_symbol_table(console, cats)

    symbol = Prompt.ask(
        "Símbolo a operar",
        default="MES=F",
    ).strip().upper()
    lot_size = FloatPrompt.ask("Cantidad de contratos / lotes", default=1.0)

    cfg = load_strategy_config()
    cfg["lot_size"] = lot_size
    strat = AsianBreakoutStrategy(cfg)
    provider = DataProvider()
    data_tf = cfg.get("data_timeframe", "5m")

    console.print(
        f"\n[green]Conectando con el proveedor de datos para [bold]{symbol}[/bold]...[/green]\n"
        f"[dim]Timeframe: {data_tf} | Lotaje: {lot_size} | "
        f"Entry window: 07:30-09:30 UTC | "
        f"Presioná Ctrl+C para detener.[/dim]\n"
    )

    try:
        while True:
            now = datetime.now(timezone.utc)

            is_futures = symbol.upper().endswith("=F") or any(
                symbol.upper().startswith(p)
                for p in ("MES", "ES", "MNQ", "NQ", "MYM", "YM", "RTY", "M2K", "CL", "GC", "SI", "NG", "HG", "ZC", "ZS", "ZW")
            )
            df, info = provider.fetch(
                symbol,
                timeframe=data_tf,
                period="60d",
                force_refresh=True,
                futures=is_futures,
            )

            if df is not None and not df.empty:
                strat.process_bars(df)

                can_trade, reason = strat.can_enter_now(now)
                status = strat.get_status(now)

                if can_trade:
                    console.print(
                        f"[bold green]✓ Señal detectada: {reason}[/bold green]"
                    )
                    result = strat.execute_signal(
                        symbol, broker=_resolve_broker(symbol), now=now
                    )
                    if result.get("ok"):
                        console.print(
                            f"[bold green]✓ Orden ejecutada. "
                            f"ID: {result.get('order_id')}[/bold green]"
                        )
                    else:
                        console.print(
                            f"[bold red]❌ Error: {result.get('error')}[/bold red]"
                        )

                _display_status(console, now, status, symbol)
            else:
                err = info.get("error", "Esperando datos...")
                console.print(f"[yellow]{err}[/yellow]", end="\r")

            time.sleep(5)

    except KeyboardInterrupt:
        console.print(
            "\n[yellow]Estrategia detenida por el usuario.[/yellow]"
        )


def _resolve_broker(symbol: str) -> str:
    s = symbol.upper().strip()
    if s.endswith("=F") or any(
        s.startswith(p) for p in ("MES", "ES", "MNQ", "NQ", "MYM", "YM", "RTY", "M2K", "CL", "GC", "SI", "NG", "HG", "ZC", "ZS", "ZW")
    ):
        return "mt5"
    if s.endswith("=X"):
        return "mt5"
    if "-USD" in s or "-BTC" in s or "-ETH" in s or "-USDT" in s:
        return "binance_futures"
    futures_prefixes = ("MES", "ES", "MNQ", "NQ", "MYM", "YM", "RTY", "M2K", "CL", "GC", "SI", "NG", "HG", "ZC", "ZS", "ZW")
    if any(s.startswith(p) for p in futures_prefixes) and any(c.isdigit() for c in s):
        return "mt5"
    forex_pairs = {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "NZDUSD", "USDCHF", "EURGBP", "EURAUD", "EURJPY", "GBPJPY"}
    if s in forex_pairs:
        return "mt5"
    if s.startswith("^"):
        return "mt5"
    return "mt5"


def _display_status(
    console: Console,
    now: datetime,
    status: dict,
    symbol: str,
) -> None:
    import shutil
    cols = shutil.get_terminal_size().columns
    sep = "─" * min(cols, 80)

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Value", no_wrap=True)

    table.add_row("Hora UTC", now.strftime("%H:%M:%S"))
    table.add_row("Símbolo", symbol)
    table.add_row("Modo", order_executor.mode.upper())
    table.add_row("Ventana entrada", "Sí" if status.get("in_entry_window") else "No")
    table.add_row("Puede operar", "Sí" if status.get("can_trade") else "No")
    table.add_row("Razón", status.get("reason", ""))

    guard = status.get("guard", {})
    table.add_row("Trades hoy", f"{guard.get('trades_today', 0)}/{guard.get('max_trades', 2)}")
    cd = guard.get("cooldown_remaining", 0)
    if cd:
        table.add_row("Cooldown", f"{cd:.0f}s")

    sig = status.get("last_signal")
    if sig:
        table.add_row("Señal", sig.get("direction", "—"))
        table.add_row("Confianza", f"{sig.get('confidence', 0):.1%}")
        table.add_row("Disparada", "Sí" if sig.get("triggered") else "No")

    console.print(f"\n{sep}")
    console.print(table)
    console.print(sep)


if __name__ == "__main__":
    main()

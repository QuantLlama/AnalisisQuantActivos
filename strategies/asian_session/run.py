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


def main() -> None:
    console = Console()
    mode = order_executor.mode.upper()

    console.print(Panel(
        "[bold cyan]ASIAN SESSION BREAKOUT ENGINE v1.0.0[/bold cyan]\n"
        "[white]Estrategia para MES/MNQ — Rango Asiático 00:00-08:00 UTC[/white]\n\n"
        f"Modo de Operación: "
        + ("[bold green]REAL (LIVE)[/bold green]" if mode == "LIVE"
           else "[bold yellow]SIMULADO (PAPER)[/bold yellow]"),
        border_style="cyan",
    ))

    symbol = Prompt.ask(
        "Seleccioná el símbolo a operar",
        choices=["MES=F", "MNQ=F"],
        default="MES=F",
    )
    lot_size = FloatPrompt.ask("Cantidad de contratos", default=1.0)

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

            df, info = provider.fetch(
                symbol,
                timeframe=data_tf,
                period="60d",
                force_refresh=True,
                futures=True,
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
    if symbol.upper().endswith("=F") or any(
        symbol.upper().startswith(p)
        for p in ("MES", "ES", "MNQ", "NQ", "MYM", "YM", "RTY", "M2K")
    ):
        return "mt5"
    if "-USD" in symbol or "-BTC" in symbol:
        return "binance_futures"
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

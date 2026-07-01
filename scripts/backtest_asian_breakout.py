"""
Backtest for Asian Session Breakout strategy on MNQ=F.
Uses yfinance 5m data — simulates daily Asian range + breakout during entry window.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from strategies.asian_session.range_calculator import AsianSessionRangeCalculator
from strategies.asian_session.breakout_logic import BreakoutLogic
from strategies.asian_session.breakout_logic import BreakoutSignal


console = Console()


def fetch_data(symbol: str) -> pd.DataFrame:
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            rates = mt5.copy_rates_from_pos(symbol.replace("=F", ""), mt5.TIMEFRAME_M5, 0, 100000)
            mt5.shutdown()
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["Date"] = pd.to_datetime(df["time"], unit="s", utc=True)
                df.set_index("Date", inplace=True)
                df.rename(columns={"tick_volume": "Volume"}, inplace=True)
                return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        pass

    ticker = yf.Ticker(symbol)
    df = ticker.history(period="6mo", interval="5m", auto_adjust=True)
    if df.empty:
        df = ticker.history(period="1mo", interval="5m", auto_adjust=True)
    if df.empty:
        raise ValueError(f"No data for {symbol}")

    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    df.index.name = "Date"
    return df


def get_trading_days(df: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(df.index.normalize().unique())


def simulate_day(
    day: pd.Timestamp,
    df: pd.DataFrame,
    calc: AsianSessionRangeCalculator,
    logic: BreakoutLogic,
    min_atr_pct: int = 40,
) -> dict | None:
    day_start = day.replace(hour=0, minute=0, tzinfo=timezone.utc)
    day_end = day.replace(hour=23, minute=59, tzinfo=timezone.utc)

    day_bars = df[(df.index >= day_start) & (df.index <= day_end)]
    if len(day_bars) < 10:
        return None

    asian_start = day.replace(hour=0, minute=0, tzinfo=timezone.utc)
    asian_end = day.replace(hour=8, minute=0, tzinfo=timezone.utc)
    asian_bars = df[(df.index >= asian_start) & (df.index < asian_end)]
    if len(asian_bars) < 6:
        return None

    range_data = calc.calculate(asian_bars)
    if range_data is None:
        return None

    entry_start = day.replace(hour=7, minute=30, tzinfo=timezone.utc)
    entry_end = day.replace(hour=9, minute=30, tzinfo=timezone.utc)
    entry_bars = df[(df.index >= entry_start) & (df.index <= entry_end)]

    if entry_bars.empty:
        return None

    signal = None
    entry_time = None
    for idx, bar in entry_bars.iterrows():
        sig = logic.evaluate(float(bar["Close"]), range_data, idx.to_pydatetime())
        if sig.triggered:
            signal = sig
            entry_time = idx
            break

    if signal is None or entry_time is None:
        return None

    exit_bars = df[df.index > entry_time]

    sl_hit, tp1_hit, tp2_hit = simulate_exit(
        exit_bars, signal, entry_time
    )

    return {
        "date": day.date(),
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit_1": signal.take_profit_1,
        "take_profit_2": signal.take_profit_2,
        "confidence": signal.confidence,
        "range_high": range_data.high,
        "range_low": range_data.low,
        "range_size": range_data.range_size,
        "atr": range_data.atr,
        "atr_percentile": range_data.atr_percentile,
        "sl_hit": sl_hit,
        "tp1_hit": tp1_hit,
        "tp2_hit": tp2_hit,
        "result": "TP2" if tp2_hit else ("TP1" if tp1_hit else ("SL" if sl_hit else "OPEN")),
    }


def simulate_exit(
    exit_bars: pd.DataFrame,
    signal: BreakoutSignal,
    entry_time: pd.Timestamp,
) -> tuple[bool, bool, bool]:
    if signal.entry_price is None or signal.stop_loss is None:
        return False, False, False

    sl_hit = False
    tp1_hit = False
    tp2_hit = False

    for idx, bar in exit_bars.iterrows():
        if idx <= entry_time:
            continue

        high = float(bar["High"])
        low = float(bar["Low"])

        if signal.direction == "LONG":
            if low <= signal.stop_loss:
                sl_hit = True
                break
            if signal.take_profit_2 and high >= signal.take_profit_2:
                tp2_hit = True
                break
            if signal.take_profit_1 and high >= signal.take_profit_1:
                tp1_hit = True
        else:
            if high >= signal.stop_loss:
                sl_hit = True
                break
            if signal.take_profit_2 and low <= signal.take_profit_2:
                tp2_hit = True
                break
            if signal.take_profit_1 and low <= signal.take_profit_1:
                tp1_hit = True

    return sl_hit, tp1_hit, tp2_hit


def main():
    console.print(Panel("[bold cyan]Asian Session Breakout — Backtest MNQ=F[/bold cyan]", border_style="cyan"))

    with console.status("[yellow]Descargando datos MNQ=F..."):
        df = fetch_data("MNQ=F")

    console.print(f"[green]Datos descargados: {len(df):,} barras 5m[/green]")
    console.print(f"[dim]Rango: {df.index[0]} → {df.index[-1]}[/dim]")

    calc = AsianSessionRangeCalculator({"min_atr_percentile": 40})
    logic = BreakoutLogic({"rr_target_1": 2.0, "rr_target_2": 3.0, "min_atr_percentile": 40, "atr_sl_multiplier": 1.5})

    trading_days = get_trading_days(df)
    console.print(f"[yellow]Simulando {len(trading_days)} días...[/yellow]")

    results: list[dict] = []
    for i, day in enumerate(trading_days):
        result = simulate_day(day, df, calc, logic)
        if result:
            results.append(result)

    if not results:
        console.print("[red]No se encontraron señales en el período.[/red]")
        return

    total = len(results)
    tp2 = sum(1 for r in results if r["result"] == "TP2")
    tp1 = sum(1 for r in results if r["result"] == "TP1")
    sl = sum(1 for r in results if r["result"] == "SL")
    opened = sum(1 for r in results if r["result"] == "OPEN")

    winners = tp2 + tp1
    win_rate = winners / total * 100 if total else 0

    longs = sum(1 for r in results if r["direction"] == "LONG")
    shorts = sum(1 for r in results if r["direction"] == "SHORT")
    long_wins = sum(1 for r in results if r["direction"] == "LONG" and r["result"] in ("TP1", "TP2"))
    short_wins = sum(1 for r in results if r["direction"] == "SHORT" and r["result"] in ("TP1", "TP2"))

    avg_conf = sum(r["confidence"] for r in results) / total * 100
    avg_range = sum(r["range_size"] for r in results) / total
    avg_atr = sum(r["atr"] for r in results) / total

    table = Table(title="Resultados Backtest — Asian Session Breakout MNQ=F", box=None)
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")

    table.add_row("Período", f"{results[0]['date']} → {results[-1]['date']}")
    table.add_row("Total señales", str(total))
    table.add_row("", "")
    table.add_row("TP2 (3R)", f"{tp2} ({tp2/total*100:.1f}%)")
    table.add_row("TP1 (2R)", f"{tp1} ({tp1/total*100:.1f}%)")
    table.add_row("Stop Loss", f"{sl} ({sl/total*100:.1f}%)")
    table.add_row("Abiertas", f"{opened} ({opened/total*100:.1f}%)")
    table.add_row("", "")
    table.add_row("Win Rate", f"{win_rate:.1f}%")
    table.add_row("Longs", f"{longs} ({long_wins} wins)")
    table.add_row("Shorts", f"{shorts} ({short_wins} wins)")
    table.add_row("", "")
    table.add_row("Confianza prom.", f"{avg_conf:.1f}%")
    table.add_row("Rango prom.", f"{avg_range:.1f} pts")
    table.add_row("ATR prom.", f"{avg_atr:.1f} pts")

    console.print(table)

    detail = Table(title="Señales Detalladas", box=None)
    detail.add_column("Fecha", style="dim")
    detail.add_column("Dir", justify="center")
    detail.add_column("Entry", justify="right")
    detail.add_column("SL", justify="right")
    detail.add_column("TP1", justify="right")
    detail.add_column("TP2", justify="right")
    detail.add_column("Conf", justify="right")
    detail.add_column("Result", justify="center")

    for r in results:
        color = "green" if r["result"] in ("TP1", "TP2") else ("red" if r["result"] == "SL" else "yellow")
        detail.add_row(
            str(r["date"]),
            "L" if r["direction"] == "LONG" else "S",
            f"{r['entry_price']:.1f}" if r["entry_price"] else "—",
            f"{r['stop_loss']:.1f}" if r["stop_loss"] else "—",
            f"{r['take_profit_1']:.1f}" if r["take_profit_1"] else "—",
            f"{r['take_profit_2']:.1f}" if r["take_profit_2"] else "—",
            f"{r['confidence']:.0%}",
            f"[{color}]{r['result']}[/{color}]",
        )

    console.print(detail)


if __name__ == "__main__":
    main()

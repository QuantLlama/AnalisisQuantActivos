"""
ui/charts.py — Generación de gráficos de velas (candlesticks) en terminal usando Plotext.
Soporta layout horizontal: [Candlestick | Volumen] con EMAs superpuestas.
"""
from __future__ import annotations

import shutil
from typing import Optional

import pandas as pd
import plotext as plt

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_dates(index) -> list[str]:
    """Formatea un índice de fechas a strings DD/MM/YYYY que acepta plotext."""
    return [
        str(d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d))
        for d in index
    ]


def _terminal_size() -> tuple[int, int]:
    """Retorna (cols, rows) del terminal actual."""
    size = shutil.get_terminal_size(fallback=(120, 40))
    return size.columns, size.lines


# ──────────────────────────────────────────────────────────────────────────────
# Gráfico principal: Velas + Volumen
# ──────────────────────────────────────────────────────────────────────────────

def render_terminal_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    indicators_df: Optional[pd.DataFrame] = None,
    show_volume: bool = True,
    lookback: int = 60,
) -> str:
    """
    Dibuja un gráfico de velas + volumen en la terminal.

    Layout: [Candlestick (75%) | Volumen (25%)] lado a lado.
    Plotext candlestick espera:
        dates  : list[str] formato DD/MM/YYYY
        data   : dict {"Open": [...], "High": [...], "Low": [...], "Close": [...]}
    """
    if df is None or df.empty:
        return "[red]No hay datos disponibles para graficar.[/red]"

    term_cols, term_rows = _terminal_size()
    # Reservar márgenes
    total_w = min(term_cols - 4, config.get("chart.width", 120))
    total_h = min(term_rows - 6, config.get("chart.height", 32))
    lookback = min(len(df), lookback)
    df_slice = df.iloc[-lookback:].copy()

    dates   = _fmt_dates(df_slice.index)
    candle_data = {
        "Open":  df_slice["Open"].values.tolist(),
        "High":  df_slice["High"].values.tolist(),
        "Low":   df_slice["Low"].values.tolist(),
        "Close": df_slice["Close"].values.tolist(),
    }
    volumes = df_slice["Volume"].values.tolist()
    colors  = [
        "green" if c >= o else "red"
        for o, c in zip(df_slice["Open"].values, df_slice["Close"].values)
    ]

    plt.clf()

    if show_volume and "Volume" in df_slice.columns:
        # ── Layout horizontal: col-1 = velas (75%), col-2 = volumen (25%) ──
        w_candle = int(total_w * 0.76)
        w_volume = total_w - w_candle

        plt.subplots(1, 2)

        # ── Panel izquierdo: Candlestick ──────────────────────────────────
        plt.subplot(1, 1)
        plt.theme("dark")
        plt.candlestick(dates, candle_data)
        plt.title(f"  {symbol} [{timeframe}]  ")
        plt.grid(True, True)
        plt.plotsize(w_candle, total_h)

        # Superponer EMAs/SMAs si se suministran
        if indicators_df is not None:
            ema_colors = ["cyan", "magenta", "yellow", "orange"]
            for i, col in enumerate(indicators_df.columns):
                ind_slice = indicators_df.iloc[-lookback:][col].dropna()
                if len(ind_slice) >= 2:
                    ind_dates = _fmt_dates(ind_slice.index)
                    clr = ema_colors[i % len(ema_colors)]
                    plt.plot(
                        ind_dates,
                        ind_slice.values.tolist(),
                        label=col,
                        color=clr,
                    )

        # ── Panel derecho: Volumen ────────────────────────────────────────
        plt.subplot(1, 2)
        plt.theme("dark")
        plt.bar(dates, volumes, label="Vol", color=colors)
        plt.title("  Volumen  ")
        plt.grid(False, True)
        plt.plotsize(w_volume, total_h)

    else:
        # ── Sin volumen: sólo velas ──────────────────────────────────────
        plt.theme("dark")
        plt.candlestick(dates, candle_data)
        plt.title(f"  {symbol} [{timeframe}]  ")
        plt.grid(True, True)
        plt.plotsize(total_w, total_h)

        if indicators_df is not None:
            ema_colors = ["cyan", "magenta", "yellow", "orange"]
            for i, col in enumerate(indicators_df.columns):
                ind_slice = indicators_df.iloc[-lookback:][col].dropna()
                if len(ind_slice) >= 2:
                    ind_dates = _fmt_dates(ind_slice.index)
                    clr = ema_colors[i % len(ema_colors)]
                    plt.plot(ind_dates, ind_slice.values.tolist(), label=col, color=clr)

    try:
        return plt.build()
    except Exception as e:
        logger.error(f"Error al construir el gráfico plotext: {e}")
        return f"[red]Error en el gráfico: {e}[/red]"


# ──────────────────────────────────────────────────────────────────────────────
# Gráfico de indicadores (RSI, MACD) — panel único
# ──────────────────────────────────────────────────────────────────────────────

def render_indicator_chart(
    series_dict: dict[str, pd.Series],
    title: str = "Indicador",
    lookback: int = 60,
) -> str:
    """
    Dibuja una o varias series de indicadores (RSI, MACD, etc.) en la terminal.
    series_dict: {'RSI': pd.Series, 'Signal': pd.Series, ...}
    """
    if not series_dict:
        return "[red]No hay datos de indicadores para graficar.[/red]"

    term_cols, term_rows = _terminal_size()
    total_w = min(term_cols - 4, 120)
    total_h = min(term_rows - 6, 20)
    clrs = ["cyan", "magenta", "yellow", "green", "red"]

    plt.clf()
    plt.theme("dark")
    plt.title(f"  {title}  ")

    for i, (name, series) in enumerate(series_dict.items()):
        series = series.dropna().iloc[-lookback:]
        if series.empty:
            continue
        dates = _fmt_dates(series.index)
        plt.plot(dates, series.values.tolist(), label=name, color=clrs[i % len(clrs)])

    plt.grid(True, True)
    plt.plotsize(total_w, total_h)

    try:
        return plt.build()
    except Exception as e:
        logger.error(f"Error en render_indicator_chart: {e}")
        return f"[red]Error en indicador chart: {e}[/red]"


# ──────────────────────────────────────────────────────────────────────────────
# Wrapper directo para impresión en consola
# ──────────────────────────────────────────────────────────────────────────────

def show_terminal_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    indicators_df: Optional[pd.DataFrame] = None,
    show_volume: bool = True,
) -> None:
    """Imprime directamente el gráfico de velas en la terminal actual."""
    chart_str = render_terminal_chart(df, symbol, timeframe, indicators_df, show_volume)
    if chart_str:
        print(chart_str)

"""
ui/dashboard.py — Dashboard multi-panel en tiempo real para la terminal usando Rich.
Integra los gráficos de Plotext y las tablas de Rich en una vista consolidada.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

from ui.colors import get_style
from ui.formatters import format_price, format_percent, format_volume, colorize_text
from ui.tables import (
    make_sr_table,
    make_fibonacci_table,
    make_imbalance_table,
    make_indicators_table,
    make_risk_setup_panel,
)
from ui.charts import render_terminal_chart

console = Console()


def create_header(report_data: dict) -> Panel:
    """Crea la cabecera del dashboard con información resumida del activo."""
    symbol    = report_data.get("symbol", "N/A")
    timeframe = report_data.get("timeframe", "N/A")
    price     = report_data.get("price", 0.0)

    df_results  = report_data.get("results", {})
    vol_res     = df_results.get("volatility", {})
    struct_res  = df_results.get("market_structure", {})

    trend       = struct_res.get("trend", "NEUTRAL").upper()
    trend_color = "green" if trend == "ALCISTA" else ("red" if trend == "BAJISTA" else "yellow")

    atr     = vol_res.get("atr", 0.0)
    # "atr_pct" es la key real que retorna full_volatility_analysis()
    atr_pct = vol_res.get("atr_pct", vol_res.get("atr_percent", 0.0))

    title_text = Text.assemble(
        ("📊 SISTEMA PROFESIONAL DE ANÁLISIS DE ACTIVOS  |  ", "bold white"),
        (f"{symbol}", "bold yellow"),
        (f" ({timeframe})", "cyan"),
    )

    info_text = Text()
    info_text.append("\nPrecio Actual: ", style="bold white")
    info_text.append(
        f"{format_price(price)}   ",
        style="bold green" if trend == "ALCISTA" else "bold red",
    )
    info_text.append("Tendencia SMC: ", style="bold white")
    info_text.append(f"{trend}   ", style=f"bold {trend_color}")
    info_text.append("ATR (14): ", style="bold white")
    info_text.append(f"{format_price(atr)} ({atr_pct:.2f}%)   ", style="bold magenta")
    info_text.append("Fecha/Hora Barra: ", style="bold white")
    info_text.append(f"{report_data.get('date', 'N/A')}", style="cyan")

    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=3)
    grid.add_row(Align.left(title_text))
    grid.add_row(Align.left(info_text))

    return Panel(
        grid,
        style="white on dark_blue",
        border_style="cyan",
        box=ROUNDED,
    )


def create_footer() -> Panel:
    """Pie de página del Dashboard con los comandos rápidos de ayuda."""
    text = Text(
        "Ayuda: Escribe 'help' para comandos. 'q' o 'exit' para salir. "
        "| Analisis de Activos CLI v1.0",
        style="bold dim white",
        justify="center",
    )
    return Panel(text, border_style="dim white", box=ROUNDED)


def build_dashboard(report_data: dict) -> Layout:
    """
    Construye la estructura de Layout de Rich con todos los paneles de información.
    """
    layout = Layout()

    # Cabecera, cuerpo y pie
    layout.split(
        Layout(name="header", size=5),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    # Cuerpo: Gráfico (izquierda, 60%) | Datos (derecha, 40%)
    layout["body"].split_row(
        Layout(name="chart_panel", ratio=3),
        Layout(name="data_panel",  ratio=2),
    )

    # Panel de datos: Setup (arriba) | Métricas (abajo)
    layout["body"]["data_panel"].split(
        Layout(name="setup",   ratio=5),
        Layout(name="metrics", ratio=4),
    )

    # Cabecera y pie
    layout["header"].update(create_header(report_data))
    layout["footer"].update(create_footer())

    # Panel derecho: setup de riesgo + indicadores
    setup_data = report_data.get("setup", {})
    layout["body"]["data_panel"]["setup"].update(make_risk_setup_panel(setup_data))

    ind_data = report_data.get("results", {}).get("indicators", {})
    layout["body"]["data_panel"]["metrics"].update(make_indicators_table(ind_data))

    return layout


def display_dashboard(report_data: dict, df: pd.DataFrame) -> None:
    """Dibuja y muestra el dashboard en pantalla completa."""
    # 1. Construir layout
    layout = build_dashboard(report_data)

    # 2. Calcular EMAs para superponer en el gráfico del dashboard
    symbol    = report_data.get("symbol", "Activo")
    timeframe = report_data.get("timeframe", "1d")

    df_chart = df.copy()
    ind_df   = pd.DataFrame(index=df_chart.index)

    emas = report_data.get("results", {}).get("indicators", {}).get("emas", {})
    for name in emas:
        try:
            period = int(name.split("_")[1])
            if "EMA" in name.upper():
                ind_df[name] = df_chart["Close"].ewm(span=period, adjust=False).mean()
            else:
                ind_df[name] = df_chart["Close"].rolling(window=period).mean()
        except Exception:
            pass

    # Si no hay EMAs en el reporte, usar las estándar
    if ind_df.empty:
        ind_df["EMA_9"]  = df_chart["Close"].ewm(span=9,   adjust=False).mean()
        ind_df["EMA_21"] = df_chart["Close"].ewm(span=21,  adjust=False).mean()
        ind_df["EMA_50"] = df_chart["Close"].ewm(span=50,  adjust=False).mean()

    # 3. Generar el gráfico ANSI (sin width/height — se adapta al terminal)
    chart_ansi = render_terminal_chart(
        df_chart,
        symbol=symbol,
        timeframe=timeframe,
        indicators_df=ind_df if not ind_df.empty else None,
        show_volume=True,
        lookback=60,
    )

    if chart_ansi:
        chart_text = Text.from_ansi(chart_ansi)
        layout["body"]["chart_panel"].update(
            Panel(
                chart_text,
                title="📈 GRÁFICO TÉCNICO INTERACTIVO",
                border_style="cyan",
                box=ROUNDED,
            )
        )
    else:
        # Fallback: tabla de imbalances si el gráfico falla
        imb_data = report_data.get("results", {}).get("imbalance", {})
        layout["body"]["chart_panel"].update(make_imbalance_table(imb_data))

    # 4. Limpiar pantalla y renderizar
    os.system("clear" if os.name == "posix" else "cls")
    console.print(layout)

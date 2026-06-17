"""
ui/dashboard.py — Dashboard multi-panel en tiempo real para la terminal usando Rich.
Integra los gráficos de Plotext y las tablas de Rich en una vista consolidada.
"""
from __future__ import annotations

import os
from typing import Any
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
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
    symbol = report_data.get("symbol", "N/A")
    timeframe = report_data.get("timeframe", "N/A")
    price = report_data.get("price", 0.0)
    
    # Calcular variación porcentual del último cierre (simulada o calculada de los datos)
    df_results = report_data.get("results", {})
    vol_res = df_results.get("volatility", {})
    struct_res = df_results.get("market_structure", {})
    
    trend = struct_res.get("trend", "NEUTRAL").upper()
    trend_color = "bullish" if trend == "ALCISTA" else ("bearish" if trend == "BAJISTA" else "neutral")
    
    atr = vol_res.get("atr", 0.0)
    atr_pct = vol_res.get("atr_percent", 0.0)

    title_text = Text.assemble(
        ("📊 SISTEMA PROFESIONAL DE ANÁLISIS DE ACTIVOS  |  ", "bold white"),
        (f"{symbol}", "bold yellow"),
        (f" ({timeframe})", "cyan"),
    )

    info_text = Text()
    info_text.append("\nPrecio Actual: ", style="bold white")
    info_text.append(f"{format_price(price)}   ", style="bold green" if trend == "ALCISTA" else "bold red")
    
    info_text.append("Tendencia SMC: ", style="bold white")
    info_text.append(f"{trend}   ", style=trend_color)
    
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
        box=ROUNDED
    )


def create_footer() -> Panel:
    """Pie de página del Dashboard con los comandos rápidos de ayuda."""
    text = Text(
        "Ayuda: Escribe 'help' para comandos. 'q' o 'exit' para salir. | Analisis de Activos CLI v1.0",
        style="bold dim white",
        justify="center"
    )
    return Panel(text, border_style="dim white", box=ROUNDED)


def build_dashboard(report_data: dict) -> Layout:
    """
    Construye la estructura de Layout de Rich cargando todos los paneles de información.
    """
    # Obtener el tamaño de la terminal
    try:
        term_cols, term_rows = os.get_terminal_size()
    except OSError:
        term_cols, term_rows = 120, 40

    # Crear el layout raíz
    layout = Layout()

    # Dividir el layout en Header (cabecera), Body (cuerpo) y Footer (pie)
    layout.split(
        Layout(name="header", size=5),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )

    # Dividir el cuerpo en Izquierda (Gráfico) y Derecha (Datos / Setup)
    layout["body"].split_row(
        Layout(name="chart_panel", ratio=3),
        Layout(name="data_panel", ratio=2),
    )

    # Dividir el panel de datos verticalmente en dos secciones: setup y estadísticas
    layout["body"]["data_panel"].split(
        Layout(name="setup", ratio=5),
        Layout(name="metrics", ratio=4),
    )

    # Asignar la cabecera y pie de página
    layout["header"].update(create_header(report_data))
    layout["footer"].update(create_footer())

    # Generar el gráfico de Plotext y convertirlo a Text de Rich para renderizado
    # Le pasamos el dataframe si lo tenemos o usamos el slice disponible
    df_results = report_data.get("results", {})
    # Intentamos recuperar el df original de una caché o proveedor (lo ideal es pasarlo)
    # Si no lo pasamos directamente, podemos graficar solo el resumen o las tablas
    # Pero como es interactivo, podemos pasar un dataframe en el contexto de llamada.
    
    # Asignar el panel de Setup
    setup_data = report_data.get("setup", {})
    layout["body"]["data_panel"]["setup"].update(make_risk_setup_panel(setup_data))

    # Asignar el panel de métricas/indicadores
    ind_data = df_results.get("indicators", {})
    layout["body"]["data_panel"]["metrics"].update(make_indicators_table(ind_data))

    # El gráfico se inyecta en el panel izquierdo
    # Si el terminal es pequeño, reducimos dimensiones
    chart_width = max(60, term_cols - 60)
    chart_height = max(18, term_rows - 14)
    
    # NOTA: El llamador inyectará el gráfico compilado en ANSI en el layout o
    # utilizaremos una función que lo pinte directamente.
    
    return layout


def display_dashboard(report_data: dict, df: pd.DataFrame) -> None:
    """Dibuja y muestra el dashboard en la pantalla completa."""
    # 1. Construir layout
    layout = build_dashboard(report_data)
    
    # 2. Generar el gráfico en ANSI e inyectarlo en el layout
    symbol = report_data.get("symbol", "Activo")
    timeframe = report_data.get("timeframe", "1d")
    
    # Obtener EMAs y SMAs para superponer en el gráfico
    emas = report_data.get("results", {}).get("indicators", {}).get("emas", {})
    indicator_cols = []
    # Inyectar temporalmente las EMAs al dataframe de gráfico
    df_chart = df.copy()
    for name, val in emas.items():
        # Para graficar en plotext, necesitamos la serie completa del indicador.
        # Volvemos a calcular la EMA 50 y 200 en el dataframe temporal
        try:
            period = int(name.split("_")[1])
            if "EMA" in name:
                df_chart[name] = df_chart["Close"].ewm(span=period, adjust=False).mean()
            else:
                df_chart[name] = df_chart["Close"].rolling(window=period).mean()
            indicator_cols.append(name)
        except Exception:
            pass

    chart_ansi = render_terminal_chart(
        df_chart,
        symbol=symbol,
        timeframe=timeframe,
        indicators_df=df_chart[indicator_cols] if indicator_cols else None,
        show_volume=True,
        width=80,
        height=22
    )

    if chart_ansi:
        # Convertir ANSI escape sequences a Rich Text
        chart_text = Text.from_ansi(chart_ansi)
        layout["body"]["chart_panel"].update(Panel(chart_text, title="📈 GRÁFICO TÉCNICO INTERACTIVO", border_style="cyan", box=ROUNDED))
    else:
        # Si falla plotext, inyectamos una tabla con el imbalance
        imb_data = report_data.get("results", {}).get("imbalance", {})
        layout["body"]["chart_panel"].update(make_imbalance_table(imb_data))

    # Limpiar pantalla y renderizar
    os.system("clear" if os.name == "posix" else "cls")
    console.print(layout)
from rich.table import Table

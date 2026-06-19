"""
ui/tables.py — Renderizado de tablas y paneles estilizados con Rich.
Proporciona componentes visuales claros y estéticos para mostrar análisis en la terminal.
"""
from __future__ import annotations

from typing import Any
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.box import ROUNDED

from ui.formatters import format_price, format_percent, format_volume, colorize_text


def make_sr_table(sr_data: dict) -> Table:
    """Crea una tabla con niveles Pivote y niveles de precio calculados."""
    table = Table(title="📍 PIVOTS Y ZONAS DE PRECIO CLAVE", box=ROUNDED)
    table.add_column("Nivel / Tipo", style="bold cyan")
    table.add_column("Precio", justify="right")
    table.add_column("Descripción / Estado", style="dim white")

    # Pivots clásicos
    pivots_raw = sr_data.get("pivots", {})
    pivots = pivots_raw.get("levels", {}) if isinstance(pivots_raw, dict) and "levels" in pivots_raw else pivots_raw
    # Ordenar niveles de mayor a menor
    sorted_pivots = sorted(pivots.items(), key=lambda x: x[1], reverse=True)
    
    for level, price in sorted_pivots:
        desc = "Resistencia" if "R" in level else ("Soporte" if "S" in level else "Punto Pivote Central")
        style = "price_down" if "R" in level else ("price_up" if "S" in level else "neutral")
        table.add_row(
            level,
            colorize_text(format_price(price), style),
            desc
        )

    # Añadir swing levels e información de fractales si existe
    fractals = sr_data.get("fractals", {})
    if fractals:
        table.add_section()
        recent_highs = fractals.get("bullish_fractals", [])
        recent_lows = fractals.get("bearish_fractals", [])
        
        for h in recent_highs[:2]:
            table.add_row("Fractal High", format_price(h), "Resistencia horizontal reciente")
        for l in recent_lows[:2]:
            table.add_row("Fractal Low", format_price(l), "Soporte horizontal reciente")

    return table


def make_fibonacci_table(fib_data: dict) -> Table:
    """Crea la tabla de retrocesos y extensiones de Fibonacci."""
    direction = fib_data.get("direction", "up")
    dir_str = "IMPULSO ALCISTA" if direction == "up" else "IMPULSO BAJISTA"
    
    # Mostrar el rango correcto según la dirección
    start_p = fib_data.get('swing_low') if direction == "up" else fib_data.get('swing_high')
    end_p = fib_data.get('swing_high') if direction == "up" else fib_data.get('swing_low')
    
    table = Table(
        title=f"🌀 FIBONACCI ({dir_str}: {format_price(start_p)} ➔ {format_price(end_p)})",
        box=ROUNDED
    )
    table.add_column("Nivel", justify="center", style="bold magenta")
    table.add_column("Precio", justify="right")
    table.add_column("Confluencia / Importancia", style="dim white")

    # Juntar retracements y extensions
    ret_levels = fib_data.get("retracements", {}).get("levels", {})
    ext_levels = fib_data.get("extensions", {}).get("levels", {})
    
    levels = {**ret_levels, **ext_levels}
    
    # Definición de importancia
    labels = {
        0.0: "Inicio de Onda",
        0.236: "Retroceso Menor",
        0.382: "Primer Soporte / Resistencia",
        0.5: "Nivel Psicológico (50%)",
        0.618: "Golden Ratio (Número Áureo Clave)",
        0.786: "Nivel Profundo de Descuento",
        1.0: "Fin de Onda (Origen)",
        1.272: "Extensión Menor (Target 1)",
        1.618: "Extensión Áurea (Target Clave)",
        2.0: "Extensión Mayor (Target 2)",
        2.618: "Extensión Extrema",
    }

    # Ordenar niveles de mayor a menor para presentación descendente
    sorted_levels = sorted(levels.items(), key=lambda x: x[1], reverse=True)
    for lvl, price in sorted_levels:
        label = labels.get(lvl, "Nivel Personalizado")
        style = "success" if lvl in [0.5, 0.618] else "neutral"
        
        table.add_row(
            f"{lvl * 100:.1f}%",
            colorize_text(format_price(price), style),
            label
        )

    return table


def make_gann_table(gann_data: dict) -> Table:
    """Crea la tabla de abanico de Gann y cuadrado de 9."""
    table = Table(title="📐 ANÁLISIS GEOMÉTRICO DE GANN", box=ROUNDED)
    table.add_column("Ángulo (Precio x Tiempo)", style="bold yellow")
    table.add_column("Precio Actual Proyectado", justify="right")
    table.add_column("Descripción / Importancia", style="dim white")

    fan = gann_data.get("fan", {})
    fan_levels = fan.get("fan_levels", {})
    if fan_levels:
        for angle, data in fan_levels.items():
            price_proj = data.get("price_now")
            ratio = data.get("ratio")
            desc = "Ángulo Principal de Tendencia (1x1)" if angle == "1x1" else (
                "Aceleración Alcista Fuerte" if ratio > 1 else "Tendencia Lenta / Soporte Profundo"
            )
            table.add_row(angle, format_price(price_proj), desc)
            
    # Cuadrado de 9
    sq9 = gann_data.get("square_of_9", {})
    if sq9:
        table.add_section()
        levels = sq9.get("all_levels", [])
        for lvl in levels[:4]:
            table.add_row(
                f"Sq9 +{lvl.get('angle_deg')}°",
                format_price(lvl.get("price")),
                f"Soporte/Resistencia estático cíclico"
            )

    return table


def make_imbalance_table(imb_data: dict) -> Table:
    """Crea la tabla de FVG, Order Blocks y Liquidity Pools."""
    table = Table(title="⚡ LIQUIDEZ E IMBALANCES DE MERCADO (SMC)", box=ROUNDED)
    table.add_column("Tipo", style="bold magenta")
    table.add_column("Rango / Zona", justify="center")
    table.add_column("Detalle", style="dim white")
    table.add_column("Estado", justify="center")

    fvgs = imb_data.get("fvgs", {})
    # FVG Alcistas
    for fvg in fvgs.get("bullish", [])[:3]:
        table.add_row(
            colorize_text("FVG Alcista", "bullish"),
            f"{format_price(fvg['bottom'])} - {format_price(fvg['top'])}",
            f"Vela del {fvg['date']}",
            colorize_text("Activo ⚡", "warning")
        )
    # FVG Bajistas
    for fvg in fvgs.get("bearish", [])[:3]:
        table.add_row(
            colorize_text("FVG Bajista", "bearish"),
            f"{format_price(fvg['bottom'])} - {format_price(fvg['top'])}",
            f"Vela del {fvg['date']}",
            colorize_text("Activo ⚡", "warning")
        )

    # Order Blocks
    obs = imb_data.get("order_blocks", {})
    for ob in obs.get("bullish", [])[:3]:
        table.add_row(
            colorize_text("Order Block Alcista (OB)", "bullish"),
            f"{format_price(ob['bottom'])} - {format_price(ob['top'])}",
            f"Volumen: {format_volume(ob.get('volume'))}",
            colorize_text("Zona de Demanda ★", "success")
        )
    for ob in obs.get("bearish", [])[:3]:
        table.add_row(
            colorize_text("Order Block Bajista (OB)", "bearish"),
            f"{format_price(ob['bottom'])} - {format_price(ob['top'])}",
            f"Volumen: {format_volume(ob.get('volume'))}",
            colorize_text("Zona de Oferta ★", "error")
        )

    # Liquidity Pools
    pools = imb_data.get("liquidity_pools", {})
    for eq_high in pools.get("equal_highs", [])[:2]:
        table.add_row(
            colorize_text("Equal Highs (Resistencia)", "neutral"),
            format_price(eq_high["price"]),
            f"Pool de Liquidez (Máximos iguales)",
            colorize_text("Atracción Liquidez 🎯", "warning")
        )
    for eq_low in pools.get("equal_lows", [])[:2]:
        table.add_row(
            colorize_text("Equal Lows (Soporte)", "neutral"),
            format_price(eq_low["price"]),
            f"Pool de Liquidez (Mínimos iguales)",
            colorize_text("Atracción Liquidez 🎯", "warning")
        )

    return table


def make_indicators_table(ind_data: dict) -> Table:
    """Crea la tabla consolidada de indicadores técnicos clásicos."""
    table = Table(title="📊 MOMENTUM E INDICADORES CLÁSICOS", box=ROUNDED)
    table.add_column("Indicador", style="bold cyan")
    table.add_column("Valor", justify="center")
    table.add_column("Señal / Estado", justify="center")

    # RSI
    rsi = ind_data.get("rsi", {})
    rsi_state_style = "success" if rsi.get("state") == "sobreventa" else (
        "error" if rsi.get("state") == "sobrecompra" else "neutral"
    )
    table.add_row(
        "RSI (14)",
        f"{rsi.get('value'):.2f}",
        colorize_text(rsi.get("state").upper(), rsi_state_style)
    )

    # MACD
    macd = ind_data.get("macd", {})
    macd_style = "bullish" if "alcista" in macd.get("state", "") else "bearish"
    table.add_row(
        "MACD Line / Signal / Hist",
        f"{macd.get('macd'):.4f} / {macd.get('signal'):.4f} / {macd.get('hist'):.4f}",
        colorize_text(macd.get("state").upper(), macd_style)
    )

    # Estocástico
    stoch = ind_data.get("stochastic", {})
    stoch_style = "success" if stoch.get("state") == "sobreventa" else (
        "error" if stoch.get("state") == "sobrecompra" else "neutral"
    )
    table.add_row(
        "Stochastic %K / %D",
        f"{stoch.get('k'):.1f} / {stoch.get('d'):.1f}",
        colorize_text(stoch.get("state").upper(), stoch_style)
    )

    # ADX
    adx = ind_data.get("adx", {})
    table.add_row(
        f"ADX ({adx.get('strength')})",
        f"{adx.get('adx'):.1f} (+DI: {adx.get('plus_di'):.1f} | -DI: {adx.get('minus_di'):.1f})",
        colorize_text(adx.get("direction").upper(), "bullish" if adx.get("direction") == "alcista" else (
            "bearish" if adx.get("direction") == "bajista" else "neutral"
        ))
    )

    return table


def make_risk_setup_panel(setup: dict) -> Panel:
    """Dibuja un panel muy visual y estético del setup de trading sugerido."""
    dir_str = setup.get("direccion", "NEUTRAL")
    style_dir = "bullish" if "COMPRA" in dir_str else ("bearish" if "VENTA" in dir_str else "neutral")
    
    text = Text()
    text.append("════════════════════════════════════════════════════════════\n", style="dim white")
    text.append("📌 SETUP SUGERIDO DE OPERACIÓN\n", style="bold yellow")
    text.append("════════════════════════════════════════════════════════════\n", style="dim white")
    
    text.append("DIRECCIÓN: ", style="bold white")
    text.append(f"{dir_str}\n\n", style=style_dir)
    
    if "NEUTRAL" not in dir_str:
        text.append("🟢 ENTRADA SUGERIDA : ", style="bold green")
        text.append(f"{format_price(setup.get('entrada'))}\n", style="bold white")
        
        text.append("🔴 STOP LOSS SL      : ", style="bold red")
        text.append(f"{format_price(setup.get('stop_loss'))}\n", style="bold white")
        
        text.append("🎯 TAKE PROFIT 1     : ", style="bold cyan")
        text.append(f"{format_price(setup.get('take_profit_1'))} ", style="bold white")
        text.append(f"(R:R 1:{setup.get('rr_tp1')})\n", style="dim green")
        
        text.append("🎯 TAKE PROFIT 2     : ", style="bold cyan")
        text.append(f"{format_price(setup.get('take_profit_2'))} ", style="bold white")
        text.append(f"(R:R 1:{setup.get('rr_tp2')})\n\n", style="dim green")
        
        text.append("💼 GESTIÓN DE RIESGO:\n", style="bold yellow")
        text.append(f"  • Riesgo asignado  : ", style="dim white")
        text.append(f"{format_price(setup.get('riesgo_dinero'))}\n", style="bold white")
        text.append(f"  • Tamaño de posición: ", style="dim white")
        text.append(f"{setup.get('tamano_posicion')} unidades\n", style="bold white")
        text.append(f"  • Valor nominal    : ", style="dim white")
        text.append(f"{format_price(setup.get('valor_nominal'))}\n\n", style="bold white")
    
    text.append("💡 JUSTIFICACIÓN DE LA SEÑAL:\n", style="bold yellow")
    for j in setup.get("justificacion", []):
        text.append(f"  • {j}\n", style="dim white")

    return Panel(
        text,
        title="🎯 SETUP PROFESIONAL DE TRADING",
        border_style="green" if "COMPRA" in dir_str else ("red" if "VENTA" in dir_str else "cyan"),
        box=ROUNDED
    )


def make_quant_panel(quant_data: dict) -> Panel:
    """Crea el panel para el análisis Cuantitativo AI."""
    if "error" in quant_data:
        return Panel(f"[red]{quant_data['error']}[/red]", title="🔬 QUANT AI")

    dir_str = quant_data.get("direction", "NEUTRAL")
    style_dir = "bold green" if "COMPRA" in dir_str else ("bold red" if "VENTA" in dir_str else "bold yellow")
    
    fourier = quant_data.get("fourier", {})
    of = quant_data.get("order_flow", {})
    
    text = Text()
    text.append("🧠 DIRECCIÓN ALGORÍTMICA: ", style="bold white")
    text.append(f"{dir_str}\n", style=style_dir)
    text.append("Probabilidad Win: ", style="bold white")
    text.append(f"{quant_data.get('win_probability', 50):.1f}%\n\n", style="bold cyan")
    
    text.append("📊 FOURIER (Ciclos Temporales)\n", style="bold yellow")
    text.append(f"  • Fase del Ciclo: {fourier.get('phase', '—')}\n", style="dim white")
    text.append(f"  • Ciclo Dominante: {fourier.get('main_cycle_bars', '—')} barras\n\n", style="dim white")
    
    text.append("🌊 ORDER FLOW SINTÉTICO (Volumen)\n", style="bold yellow")
    text.append(f"  • Estado: {of.get('state', '—')}\n\n", style="dim white")
    
    ml = quant_data.get('ml_data')
    if ml:
        text.append("🤖 REDES / MACHINE LEARNING (Random Forest)\n", style="bold yellow")
        text.append(f"  • Estado: {ml.get('status', '—')}\n", style="dim white")
        text.append(f"  • Probabilidad Alcista ML: {ml.get('prob_up', 0):.1f}%\n", style="dim white")

    text.append("\n🎯 SETUP INSTITUCIONAL\n", style="bold magenta")
    text.append(f"  • Entrada sugerida: {format_price(quant_data.get('entry'))}\n", style="bold white")
    text.append(f"  • Stop Loss: {format_price(quant_data.get('stop_loss'))}\n", style="red")
    text.append(f"  • Take Profit 1: {format_price(quant_data.get('take_profit_1'))}\n", style="green")
    text.append(f"  • Take Profit 2: {format_price(quant_data.get('take_profit_2'))}\n", style="green")
    text.append(f"  • Tamaño de Posición: {quant_data.get('position_size', 0):.4f}\n", style="dim white")

    return Panel(
        text,
        title="🔬 QUANT AI (Fourier + Order Flow)",
        border_style="cyan",
        box=ROUNDED
    )

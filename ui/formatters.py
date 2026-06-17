"""
ui/formatters.py — Utilidades de formateo para la interfaz de terminal.
Asegura que los precios, porcentajes y volúmenes se presenten de manera óptima y legible.
"""
from __future__ import annotations


def format_price(value: float | None) -> str:
    """Formatea precios adaptándose a la escala del activo."""
    if value is None:
        return "N/A"
    
    abs_v = abs(value)
    if abs_v == 0:
        return "0.00"
    
    if abs_v >= 1000:
        return f"${value:,.2f}"
    elif abs_v >= 1:
        return f"${value:.2f}"
    elif abs_v >= 0.01:
        return f"${value:.4f}"
    else:
        return f"${value:.6f}"


def format_percent(value: float | None) -> str:
    """Formatea variaciones porcentuales añadiendo signos e indicadores visuales."""
    if value is None:
        return "N/A"
    
    if value > 0:
        return f"▲ +{value:.2f}%"
    elif value < 0:
        return f"▼ {value:.2f}%"
    else:
        return f"─ 0.00%"


def format_volume(value: float | None) -> str:
    """Formatea cifras grandes de volumen usando sufijos legibles (K, M, B)."""
    if value is None:
        return "N/A"
    
    abs_v = abs(value)
    if abs_v >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif abs_v >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif abs_v >= 1_000:
        return f"{value / 1_000:.2f}K"
    else:
        return f"{value:.0f}"


def colorize_text(text: str, style_name: str) -> str:
    """Retorna el texto envuelto en etiquetas de marcado de Rich."""
    return f"[{style_name}]{text}[/{style_name}]"

"""
ui/colors.py — Paleta de colores y estilos para la terminal usando Rich.
Estilos consistentes con una estética premium oscura por defecto.
"""
from __future__ import annotations

from rich.style import Style

# Paleta de colores en base al tema
THEME_STYLES = {
    "title": "bold cyan",
    "header": "bold white on blue",
    "accent": "bold magenta",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    
    "price_up": "bold green",
    "price_down": "bold red",
    "neutral": "bold white",
    
    "bullish": "bold green",
    "bearish": "bold red",
    
    "fib_level": "cyan",
    "gann_angle": "magenta",
    "fvg_active": "yellow",
    
    "label": "dim white",
    "value": "bold white",
    
    "panel_border": "cyan",
    "dashboard_title": "bold white on dark_blue",
}


def get_style(name: str) -> str:
    """Retorna la cadena de estilo de Rich asociada."""
    return THEME_STYLES.get(name, "white")

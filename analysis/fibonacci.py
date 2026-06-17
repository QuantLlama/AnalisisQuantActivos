"""
analysis/fibonacci.py — Retracements, extensiones y zonas de confluencia Fibonacci.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Niveles estándar
FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
FIB_EXTENSIONS = [1.0, 1.272, 1.618, 2.0, 2.618]
FIB_NAMES = {
    0.0: "0% (Inicio)",
    0.236: "23.6%",
    0.382: "38.2%",
    0.5: "50%",
    0.618: "61.8% (Golden Ratio)",
    0.786: "78.6%",
    1.0: "100% (Fin swing)",
    1.272: "127.2% (Ext)",
    1.618: "161.8% (Ext)",
    2.0: "200% (Ext)",
    2.618: "261.8% (Ext)",
}


def calculate_retracements(
    swing_high: float,
    swing_low: float,
    direction: str = "up",
    custom_levels: Optional[list[float]] = None,
) -> dict:
    """
    Calcula niveles de retroceso Fibonacci.

    Parameters
    ----------
    swing_high  : Precio más alto del swing
    swing_low   : Precio más bajo del swing
    direction   : 'up' (retroceso de impulso alcista) o 'down'
    """
    levels_cfg = custom_levels or config.get("fibonacci.levels", FIB_LEVELS)
    rng = swing_high - swing_low

    levels = {}
    for level in levels_cfg:
        if direction == "up":
            price = swing_high - level * rng
        else:
            price = swing_low + level * rng
        levels[level] = round(price, 8)

    return {
        "type": "retracement",
        "direction": direction,
        "swing_high": swing_high,
        "swing_low": swing_low,
        "range": rng,
        "levels": levels,
    }


def calculate_extensions(
    swing_high: float,
    swing_low: float,
    direction: str = "up",
    custom_levels: Optional[list[float]] = None,
) -> dict:
    """Calcula niveles de extensión Fibonacci (objetivos de precio)."""
    levels_cfg = custom_levels or config.get("fibonacci.extensions", FIB_EXTENSIONS)
    rng = swing_high - swing_low

    levels = {}
    for level in levels_cfg:
        if direction == "up":
            price = swing_low + level * rng
        else:
            price = swing_high - level * rng
        levels[level] = round(price, 8)

    return {
        "type": "extension",
        "direction": direction,
        "swing_high": swing_high,
        "swing_low": swing_low,
        "range": rng,
        "levels": levels,
    }


def auto_detect_swings(df: pd.DataFrame, lookback: Optional[int] = None) -> tuple[float, float, str]:
    """
    Detecta automáticamente el último swing significativo.
    Retorna (swing_high, swing_low, direction).
    """
    lb = lookback or min(len(df), 50)
    subset = df.iloc[-lb:]

    high = float(subset["High"].max())
    low = float(subset["Low"].min())

    high_idx = subset["High"].idxmax()
    low_idx = subset["Low"].idxmin()

    # Dirección basada en qué ocurrió primero
    if subset.index.get_loc(high_idx) > subset.index.get_loc(low_idx):
        direction = "up"  # El high está después del low → impulso alcista
    else:
        direction = "down"

    return high, low, direction


def fibonacci_fan(
    pivot_price: float,
    pivot_date_idx: int,
    swing_price: float,
    swing_date_idx: int,
    current_idx: int,
) -> dict:
    """
    Calcula precios del Abanico de Fibonacci para un índice de barra dado.
    """
    dt = swing_date_idx - pivot_date_idx
    dp = swing_price - pivot_price
    slope = dp / dt if dt != 0 else 0

    proj_bars = current_idx - pivot_date_idx
    fan_levels = {}
    for level in [0.236, 0.382, 0.5, 0.618, 0.786]:
        fan_levels[level] = round(pivot_price + slope * level * proj_bars, 8)

    return {"type": "fan", "levels": fan_levels}


def confluence_zones(
    retracement: dict,
    other_levels: list[float],
    tolerance_pct: float = 0.5,
) -> list[dict]:
    """
    Detecta zonas donde niveles Fibonacci coinciden con otros niveles clave (S/R, POC, etc.).
    """
    confluences = []
    for fib_level, fib_price in retracement["levels"].items():
        for other_price in other_levels:
            if other_price == 0:
                continue
            diff_pct = abs(fib_price - other_price) / other_price * 100
            if diff_pct <= tolerance_pct:
                confluences.append({
                    "fib_level": fib_level,
                    "fib_price": fib_price,
                    "other_price": other_price,
                    "diff_pct": round(diff_pct, 3),
                    "label": FIB_NAMES.get(fib_level, f"{fib_level*100:.1f}%"),
                })

    return sorted(confluences, key=lambda x: x["fib_level"])


def full_fibonacci_analysis(
    df: pd.DataFrame,
    custom_high: Optional[float] = None,
    custom_low: Optional[float] = None,
    other_levels: Optional[list[float]] = None,
) -> dict:
    """Análisis completo de Fibonacci: retrocesos + extensiones + confluencias."""
    if custom_high and custom_low:
        swing_high = custom_high
        swing_low = custom_low
        direction = "up" if custom_high > custom_low else "down"
    else:
        swing_high, swing_low, direction = auto_detect_swings(df)

    retracements = calculate_retracements(swing_high, swing_low, direction)
    extensions = calculate_extensions(swing_high, swing_low, direction)

    confluences = []
    if other_levels:
        confluences = confluence_zones(retracements, other_levels)

    current_price = float(df["Close"].iloc[-1])
    rng = swing_high - swing_low

    # Detectar nivel Fibonacci más cercano al precio actual
    closest_level = None
    closest_diff = float("inf")
    for level, price in retracements["levels"].items():
        diff = abs(price - current_price)
        if diff < closest_diff:
            closest_diff = diff
            closest_level = {"level": level, "price": price, "name": FIB_NAMES.get(level, "")}

    return {
        "swing_high": swing_high,
        "swing_low": swing_low,
        "direction": direction,
        "range": rng,
        "retracements": retracements,
        "extensions": extensions,
        "confluences": confluences,
        "current_price": current_price,
        "closest_level": closest_level,
        "fib_names": FIB_NAMES,
    }

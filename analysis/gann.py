"""
analysis/gann.py — Ángulos de Gann, Cuadrado de 9 y ciclos temporales.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Definición de ángulos de Gann (en grados y ratios precio/tiempo)
GANN_ANGLES = {
    "8x1":  {"degrees": 82.5,  "ratio": 8.0},
    "4x1":  {"degrees": 75.0,  "ratio": 4.0},
    "3x1":  {"degrees": 71.25, "ratio": 3.0},
    "2x1":  {"degrees": 63.75, "ratio": 2.0},
    "1x1":  {"degrees": 45.0,  "ratio": 1.0},
    "1x2":  {"degrees": 26.25, "ratio": 0.5},
    "1x3":  {"degrees": 18.75, "ratio": 1/3},
    "1x4":  {"degrees": 15.0,  "ratio": 0.25},
    "1x8":  {"degrees": 7.5,   "ratio": 0.125},
}


def calculate_gann_fan(
    df: pd.DataFrame,
    pivot_idx: Optional[int] = None,
    scale: Optional[float] = None,
) -> dict:
    """
    Calcula el Abanico de Gann desde un punto pivote.

    Parameters
    ----------
    pivot_idx : Índice de la barra pivote (por defecto: el más bajo del período)
    scale     : Escala de precio por unidad de tiempo (auto-calculada si no se da)
    """
    # Encontrar pivote automáticamente si no se especifica
    if pivot_idx is None:
        pivot_pos = int(df["Low"].values.argmin() if len(df) > 0 else 0)
    else:
        pivot_pos = max(0, min(pivot_idx, len(df) - 1))

    pivot_price = float(df["Low"].iloc[pivot_pos])
    current_pos = len(df) - 1
    current_price = float(df["Close"].iloc[-1])
    bars_elapsed = current_pos - pivot_pos

    if bars_elapsed <= 0:
        bars_elapsed = 1

    # Escala automática: ATR como unidad de precio por barra
    if scale is None:
        atr_vals = (df["High"] - df["Low"]).rolling(14).mean()
        atr = float(atr_vals.iloc[-1]) if not pd.isna(atr_vals.iloc[-1]) else (current_price * 0.01)
        scale = atr

    # Calcular precio proyectado para cada ángulo en la barra actual
    fan_levels = {}
    for angle_name, angle_data in GANN_ANGLES.items():
        ratio = angle_data["ratio"]
        projected_price = pivot_price + (ratio * scale * bars_elapsed)
        fan_levels[angle_name] = {
            "degrees": angle_data["degrees"],
            "ratio": ratio,
            "price_now": round(projected_price, 8),
            "above_price": projected_price > current_price,
        }

    # Determinar el ángulo 1x1 (la línea principal)
    gann_1x1 = fan_levels.get("1x1", {}).get("price_now")

    return {
        "pivot_idx": pivot_pos,
        "pivot_price": pivot_price,
        "bars_elapsed": bars_elapsed,
        "scale": scale,
        "fan_levels": fan_levels,
        "current_price": current_price,
        "gann_1x1": gann_1x1,
        "above_1x1": current_price > gann_1x1 if gann_1x1 else None,
    }


def square_of_9(price: float, steps: int = 8) -> dict:
    """
    Calcula el Cuadrado de 9 de Gann para un precio dado.
    Retorna los niveles de soporte/resistencia cíclicos.

    El Cuadrado de 9 es una espiral de números.
    La raíz cuadrada del precio + incremento en 90° ciclos → nuevos niveles.
    """
    sqrt_price = math.sqrt(price)
    levels = []

    for i in range(-steps, steps + 1):
        angle_offset = i * 0.5  # cada 45°
        new_sqrt = sqrt_price + angle_offset
        if new_sqrt > 0:
            new_price = new_sqrt ** 2
            angle_deg = (i * 45) % 360
            levels.append({
                "step": i,
                "angle_deg": angle_deg,
                "price": round(new_price, 4),
                "distance_pct": round((new_price - price) / price * 100, 2) if price > 0 else 0,
            })

    # Niveles más importantes (90°, 180°, 270°, 360°)
    key_angles = [0, 90, 180, 270, 360]
    key_levels = {}
    for lvl in levels:
        for ka in key_angles:
            if lvl["angle_deg"] == ka and ka not in key_levels:
                key_levels[f"{ka}°"] = lvl["price"]

    return {
        "base_price": price,
        "sqrt_price": round(sqrt_price, 4),
        "all_levels": sorted(levels, key=lambda x: x["price"]),
        "key_levels": key_levels,
        "nearest_above": next((l["price"] for l in sorted(levels, key=lambda x: x["price"])
                               if l["price"] > price), None),
        "nearest_below": next((l["price"] for l in sorted(levels, key=lambda x: x["price"], reverse=True)
                               if l["price"] < price), None),
    }


def gann_time_cycles(df: pd.DataFrame) -> dict:
    """
    Detecta ciclos temporales de Gann basados en números naturales de Gann.
    Números clave: 7, 30, 45, 90, 120, 144, 180, 270, 360 barras.
    """
    gann_numbers = [7, 10, 14, 21, 30, 45, 60, 90, 120, 144, 180, 270, 360]
    current_bar = len(df) - 1
    current_price = float(df["Close"].iloc[-1])

    cycles = []
    for num in gann_numbers:
        if num <= current_bar:
            past_idx = current_bar - num
            past_price = float(df["Close"].iloc[past_idx])
            past_date = df.index[past_idx]
            pct_change = (current_price - past_price) / past_price * 100 if past_price else 0
            cycles.append({
                "bars": num,
                "past_date": str(past_date.date() if hasattr(past_date, "date") else past_date),
                "past_price": past_price,
                "pct_change": round(pct_change, 2),
            })

    # Próximos ciclos importantes hacia adelante
    future_cycles = [num for num in gann_numbers if num > current_bar]

    return {
        "current_bar": current_bar,
        "past_cycles": cycles,
        "next_cycle_bars": future_cycles[:3] if future_cycles else [],
    }


def full_gann_analysis(df: pd.DataFrame) -> dict:
    """Análisis completo de Gann: Fan + Cuadrado de 9 + Ciclos temporales."""
    current_price = float(df["Close"].iloc[-1])

    fan = calculate_gann_fan(df)
    sq9 = square_of_9(current_price)
    cycles = gann_time_cycles(df)

    # Niveles de soporte/resistencia de Gann combinados
    gann_levels = []

    # Del fan
    for angle_name, data in fan["fan_levels"].items():
        gann_levels.append({
            "source": f"Fan {angle_name}",
            "price": data["price_now"],
            "type": "resistencia" if data["price_now"] > current_price else "soporte",
        })

    # Del cuadrado de 9
    for label, price in sq9["key_levels"].items():
        gann_levels.append({
            "source": f"Sq9 {label}",
            "price": price,
            "type": "resistencia" if price > current_price else "soporte",
        })

    # Filtrar solo los más cercanos
    gann_levels.sort(key=lambda x: abs(x["price"] - current_price))
    nearest = gann_levels[:8]

    return {
        "fan": fan,
        "square_of_9": sq9,
        "time_cycles": cycles,
        "current_price": current_price,
        "nearest_levels": nearest,
        "supports": [l for l in nearest if l["type"] == "soporte"],
        "resistances": [l for l in nearest if l["type"] == "resistencia"],
    }

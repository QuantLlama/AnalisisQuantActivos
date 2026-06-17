"""
analysis/support_resistance.py — Cálculo de soportes y resistencias.
Métodos: Pivot Points (Clásico/Fibonacci/Camarilla/Woodie/DeMark),
         Fractales de Williams, zonas clusterizadas HH/HL/LH/LL.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────
# Motor principal
# ──────────────────────────────────────────────────────────────

def calculate_pivot_points(df: pd.DataFrame, method: Optional[str] = None) -> dict:
    """
    Calcula Pivot Points usando la última vela completa (H, L, C del período previo).
    Métodos soportados: classic, fibonacci, camarilla, woodie, demark.
    """
    method = method or config.get("sr.pivot_method", "classic")
    last = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
    H, L, C = float(last["High"]), float(last["Low"]), float(last["Close"])
    O = float(last["Open"])

    PP = (H + L + C) / 3
    rng = H - L

    if method == "fibonacci":
        levels = {
            "PP": PP,
            "R1": PP + 0.382 * rng,
            "R2": PP + 0.618 * rng,
            "R3": PP + 1.000 * rng,
            "S1": PP - 0.382 * rng,
            "S2": PP - 0.618 * rng,
            "S3": PP - 1.000 * rng,
        }
    elif method == "camarilla":
        levels = {
            "PP": PP,
            "R4": C + rng * 1.1 / 2,
            "R3": C + rng * 1.1 / 4,
            "R2": C + rng * 1.1 / 6,
            "R1": C + rng * 1.1 / 12,
            "S1": C - rng * 1.1 / 12,
            "S2": C - rng * 1.1 / 6,
            "S3": C - rng * 1.1 / 4,
            "S4": C - rng * 1.1 / 2,
        }
    elif method == "woodie":
        PP_w = (H + L + 2 * C) / 4
        levels = {
            "PP": PP_w,
            "R1": 2 * PP_w - L,
            "R2": PP_w + rng,
            "S1": 2 * PP_w - H,
            "S2": PP_w - rng,
        }
    elif method == "demark":
        if C < O:
            x = H + 2 * L + C
        elif C > O:
            x = 2 * H + L + C
        else:
            x = H + L + 2 * C
        PP_d = x / 4
        levels = {
            "PP": PP_d,
            "R1": x / 2 - L,
            "S1": x / 2 - H,
        }
    else:  # classic
        levels = {
            "PP": PP,
            "R1": 2 * PP - L,
            "R2": PP + rng,
            "R3": H + 2 * (PP - L),
            "S1": 2 * PP - H,
            "S2": PP - rng,
            "S3": L - 2 * (H - PP),
        }

    return {"method": method, "levels": levels, "H": H, "L": L, "C": C}


def calculate_fractals(df: pd.DataFrame, period: Optional[int] = None) -> dict:
    """
    Detecta fractales de Williams (máximos/mínimos locales).
    Un fractal alcista: vela central con High > que las N velas a cada lado.
    """
    n = period or config.get("sr.fractal_period", 5)
    half = n // 2

    highs = df["High"].values
    lows = df["Low"].values

    bull_fractals = []  # (índice, precio) — soporte potencial
    bear_fractals = []  # (índice, precio) — resistencia potencial

    for i in range(half, len(df) - half):
        # Fractal alcista (soporte): mínimo local
        if all(lows[i] <= lows[i - j] for j in range(1, half + 1)) and \
           all(lows[i] <= lows[i + j] for j in range(1, half + 1)):
            bull_fractals.append({
                "index": i,
                "date": df.index[i],
                "price": float(lows[i]),
                "type": "soporte",
            })
        # Fractal bajista (resistencia): máximo local
        if all(highs[i] >= highs[i - j] for j in range(1, half + 1)) and \
           all(highs[i] >= highs[i + j] for j in range(1, half + 1)):
            bear_fractals.append({
                "index": i,
                "date": df.index[i],
                "price": float(highs[i]),
                "type": "resistencia",
            })

    return {
        "period": n,
        "soportes": bull_fractals[-10:],   # últimos 10
        "resistencias": bear_fractals[-10:],
        "all": sorted(bull_fractals + bear_fractals, key=lambda x: x["price"]),
    }


def calculate_swing_levels(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Detecta HH (Higher Highs), HL (Higher Lows), LH (Lower Highs), LL (Lower Lows).
    Determina la estructura de precio y niveles clave.
    """
    high = df["High"].rolling(lookback).max()
    low = df["Low"].rolling(lookback).min()

    # Últimos swings
    recent_highs = []
    recent_lows = []

    window = min(len(df), lookback * 3)
    subset = df.iloc[-window:]

    for i in range(1, len(subset) - 1):
        h = float(subset["High"].iloc[i])
        l = float(subset["Low"].iloc[i])
        ph = float(subset["High"].iloc[i - 1])
        nh = float(subset["High"].iloc[i + 1])
        pl = float(subset["Low"].iloc[i - 1])
        nl = float(subset["Low"].iloc[i + 1])

        if h > ph and h > nh:
            recent_highs.append({"date": subset.index[i], "price": h})
        if l < pl and l < nl:
            recent_lows.append({"date": subset.index[i], "price": l})

    # Estructura de mercado
    structure = "indefinido"
    if len(recent_highs) >= 2 and len(recent_lows) >= 2:
        hh = recent_highs[-1]["price"] > recent_highs[-2]["price"]
        hl = recent_lows[-1]["price"] > recent_lows[-2]["price"]
        lh = recent_highs[-1]["price"] < recent_highs[-2]["price"]
        ll = recent_lows[-1]["price"] < recent_lows[-2]["price"]

        if hh and hl:
            structure = "ALCISTA (HH+HL)"
        elif lh and ll:
            structure = "BAJISTA (LH+LL)"
        elif hh and ll:
            structure = "EXPANSIÓN"
        else:
            structure = "LATERAL"

    return {
        "swing_highs": recent_highs[-5:],
        "swing_lows": recent_lows[-5:],
        "structure": structure,
        "last_high": recent_highs[-1]["price"] if recent_highs else None,
        "last_low": recent_lows[-1]["price"] if recent_lows else None,
        "period_high": float(high.iloc[-1]) if not pd.isna(high.iloc[-1]) else None,
        "period_low": float(low.iloc[-1]) if not pd.isna(low.iloc[-1]) else None,
    }


def cluster_levels(levels: list[float], tolerance_pct: Optional[float] = None) -> list[float]:
    """
    Agrupa niveles de precio cercanos en zonas (clusters).
    Retorna el nivel promedio de cada zona.
    """
    tol = tolerance_pct or config.get("sr.zone_tolerance_percent", 0.5)
    if not levels:
        return []

    levels_sorted = sorted(set(levels))
    clusters = [[levels_sorted[0]]]

    for level in levels_sorted[1:]:
        last_avg = sum(clusters[-1]) / len(clusters[-1])
        if abs(level - last_avg) / last_avg * 100 <= tol:
            clusters[-1].append(level)
        else:
            clusters.append([level])

    return [round(sum(c) / len(c), 6) for c in clusters]


def full_sr_analysis(df: pd.DataFrame) -> dict:
    """Análisis completo de S/R: pivots + fractales + swings + clusters."""
    pivot_method = config.get("sr.pivot_method", "classic")
    max_levels = config.get("sr.max_levels", 10)

    pivots = calculate_pivot_points(df, pivot_method)
    fractals = calculate_fractals(df)
    swings = calculate_swing_levels(df)

    # Recopilar todos los niveles para clustering
    all_prices: list[float] = []
    all_prices.extend(pivots["levels"].values())
    all_prices.extend([f["price"] for f in fractals["soportes"]])
    all_prices.extend([f["price"] for f in fractals["resistencias"]])

    clustered = cluster_levels(all_prices)
    current_price = float(df["Close"].iloc[-1])

    # Clasificar en soportes/resistencias relativas al precio actual
    supports = sorted([l for l in clustered if l < current_price], reverse=True)[:max_levels // 2]
    resistances = sorted([l for l in clustered if l > current_price])[:max_levels // 2]

    return {
        "pivots": pivots,
        "fractals": fractals,
        "swings": swings,
        "supports": supports,
        "resistances": resistances,
        "current_price": current_price,
        "all_levels": sorted(clustered),
    }

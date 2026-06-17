"""
analysis/imbalance.py — Fair Value Gaps (FVG), Order Blocks, Breaker Blocks
y Liquidity Pools. Basado en conceptos de Smart Money / ICT.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_fvg(df: pd.DataFrame) -> dict:
    """
    Detecta Fair Value Gaps (imbalances de 3 velas).

    Un FVG alcista ocurre cuando:
        High[i-1] < Low[i+1]  → hueco entre vela i-1 e i+1

    Un FVG bajista ocurre cuando:
        Low[i-1] > High[i+1]  → hueco entre vela i-1 e i+1
    """
    min_size_pct = config.get("imbalance.fvg_min_size_percent", 0.1) / 100
    show_filled = config.get("imbalance.show_filled", False)

    current_price = float(df["Close"].iloc[-1])
    fvgs_bull = []
    fvgs_bear = []

    for i in range(1, len(df) - 1):
        high_prev = float(df["High"].iloc[i - 1])
        low_prev = float(df["Low"].iloc[i - 1])
        high_next = float(df["High"].iloc[i + 1])
        low_next = float(df["Low"].iloc[i + 1])

        date = df.index[i]
        mid_price = (float(df["High"].iloc[i]) + float(df["Low"].iloc[i])) / 2

        # FVG Alcista: Low de vela i+1 > High de vela i-1
        if low_next > high_prev:
            gap_size = low_next - high_prev
            if gap_size / mid_price >= min_size_pct:
                is_filled = current_price <= high_prev + gap_size * 0.1  # 10% llenado
                if show_filled or not is_filled:
                    fvgs_bull.append({
                        "type": "alcista",
                        "date": str(date.date() if hasattr(date, "date") else date),
                        "top": round(low_next, 6),
                        "bottom": round(high_prev, 6),
                        "mid": round((low_next + high_prev) / 2, 6),
                        "size": round(gap_size, 6),
                        "size_pct": round(gap_size / mid_price * 100, 3),
                        "filled": current_price < high_prev,
                        "distance_pct": round((current_price - (high_prev + low_next) / 2) /
                                              current_price * 100, 2),
                    })

        # FVG Bajista: High de vela i+1 < Low de vela i-1
        if high_next < low_prev:
            gap_size = low_prev - high_next
            if gap_size / mid_price >= min_size_pct:
                is_filled = current_price >= low_prev - gap_size * 0.1
                if show_filled or not is_filled:
                    fvgs_bear.append({
                        "type": "bajista",
                        "date": str(date.date() if hasattr(date, "date") else date),
                        "top": round(low_prev, 6),
                        "bottom": round(high_next, 6),
                        "mid": round((low_prev + high_next) / 2, 6),
                        "size": round(gap_size, 6),
                        "size_pct": round(gap_size / mid_price * 100, 3),
                        "filled": current_price > low_prev,
                        "distance_pct": round((current_price - (high_next + low_prev) / 2) /
                                              current_price * 100, 2),
                    })

    # Ordenar por cercanía al precio actual
    fvgs_bull.sort(key=lambda x: abs(x["distance_pct"]))
    fvgs_bear.sort(key=lambda x: abs(x["distance_pct"]))

    return {
        "bullish": fvgs_bull[:10],
        "bearish": fvgs_bear[:10],
        "total_bull": len(fvgs_bull),
        "total_bear": len(fvgs_bear),
        "current_price": current_price,
    }


def detect_order_blocks(df: pd.DataFrame) -> dict:
    """
    Detecta Order Blocks (bloques de órdenes institucionales).

    Order Block Alcista: última vela bajista ANTES de un impulso alcista fuerte.
    Order Block Bajista: última vela alcista ANTES de un impulso bajista fuerte.

    Un impulso fuerte se define como movimiento > 1.5× ATR.
    """
    lookback = config.get("imbalance.order_block_lookback", 10)
    current_price = float(df["Close"].iloc[-1])

    atr = (df["High"] - df["Low"]).rolling(14).mean()
    impulse_threshold = 1.5

    bull_obs = []
    bear_obs = []

    for i in range(1, len(df) - 2):
        atr_val = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else 0
        if atr_val == 0:
            continue

        # Siguiente vela
        next_move = abs(float(df["Close"].iloc[i + 1]) - float(df["Open"].iloc[i + 1]))
        next_dir = float(df["Close"].iloc[i + 1]) - float(df["Open"].iloc[i + 1])

        if next_move < impulse_threshold * atr_val:
            continue

        open_c = float(df["Open"].iloc[i])
        close_c = float(df["Close"].iloc[i])
        high_c = float(df["High"].iloc[i])
        low_c = float(df["Low"].iloc[i])
        date = df.index[i]

        # Order Block Alcista: vela bajista seguida de impulso alcista
        if close_c < open_c and next_dir > 0:
            is_broken = current_price > high_c
            bull_obs.append({
                "type": "alcista",
                "date": str(date.date() if hasattr(date, "date") else date),
                "top": round(high_c, 6),
                "bottom": round(low_c, 6),
                "mid": round((high_c + low_c) / 2, 6),
                "broken": is_broken,
                "distance_pct": round((current_price - (high_c + low_c) / 2) / current_price * 100, 2),
            })

        # Order Block Bajista: vela alcista seguida de impulso bajista
        elif close_c > open_c and next_dir < 0:
            is_broken = current_price < low_c
            bear_obs.append({
                "type": "bajista",
                "date": str(date.date() if hasattr(date, "date") else date),
                "top": round(high_c, 6),
                "bottom": round(low_c, 6),
                "mid": round((high_c + low_c) / 2, 6),
                "broken": is_broken,
                "distance_pct": round((current_price - (high_c + low_c) / 2) / current_price * 100, 2),
            })

    # Filtrar broken y ordenar por cercanía
    active_bull = [ob for ob in bull_obs if not ob["broken"]]
    active_bear = [ob for ob in bear_obs if not ob["broken"]]

    active_bull.sort(key=lambda x: abs(x["distance_pct"]))
    active_bear.sort(key=lambda x: abs(x["distance_pct"]))

    return {
        "bullish": active_bull[:5],
        "bearish": active_bear[:5],
        "broken_bull": [ob for ob in bull_obs if ob["broken"]][-3:],
        "broken_bear": [ob for ob in bear_obs if ob["broken"]][-3:],
        "current_price": current_price,
    }


def detect_liquidity_pools(df: pd.DataFrame, tolerance_pct: float = 0.2) -> dict:
    """
    Detecta Liquidity Pools: niveles con múltiples máximos/mínimos iguales.
    Estos niveles son "imanes" para el precio (donde hay stops acumulados).
    """
    current_price = float(df["Close"].iloc[-1])
    tol = tolerance_pct / 100

    highs = df["High"].values
    lows = df["Low"].values
    dates = df.index

    equal_highs = []
    equal_lows = []

    # Buscar equal highs
    for i in range(len(highs)):
        matches = [i]
        for j in range(i + 1, len(highs)):
            if abs(highs[j] - highs[i]) / highs[i] <= tol:
                matches.append(j)
        if len(matches) >= 2:
            avg_price = sum(highs[k] for k in matches) / len(matches)
            if not any(abs(eh["price"] - avg_price) / avg_price < tol * 2 for eh in equal_highs):
                equal_highs.append({
                    "price": round(avg_price, 6),
                    "touches": len(matches),
                    "type": "resistencia (equal highs)",
                    "swept": current_price > avg_price,
                    "distance_pct": round((current_price - avg_price) / avg_price * 100, 2),
                })

    # Buscar equal lows
    for i in range(len(lows)):
        matches = [i]
        for j in range(i + 1, len(lows)):
            if lows[i] > 0 and abs(lows[j] - lows[i]) / lows[i] <= tol:
                matches.append(j)
        if len(matches) >= 2:
            avg_price = sum(lows[k] for k in matches) / len(matches)
            if not any(abs(el["price"] - avg_price) / avg_price < tol * 2 for el in equal_lows):
                equal_lows.append({
                    "price": round(avg_price, 6),
                    "touches": len(matches),
                    "type": "soporte (equal lows)",
                    "swept": current_price < avg_price,
                    "distance_pct": round((current_price - avg_price) / avg_price * 100, 2),
                })

    # Ordenar por cercanía
    equal_highs.sort(key=lambda x: abs(x["distance_pct"]))
    equal_lows.sort(key=lambda x: abs(x["distance_pct"]))

    return {
        "equal_highs": equal_highs[:5],
        "equal_lows": equal_lows[:5],
        "current_price": current_price,
    }


def full_imbalance_analysis(df: pd.DataFrame) -> dict:
    """Análisis completo: FVG + Order Blocks + Liquidity Pools."""
    fvg = detect_fvg(df)
    obs = detect_order_blocks(df)
    liquidity = detect_liquidity_pools(df)

    current_price = float(df["Close"].iloc[-1])

    # Señal combinada
    bull_signals = (
        len(fvg["bullish"]) +
        len(obs["bullish"]) +
        len([e for e in liquidity["equal_lows"] if not e["swept"]])
    )
    bear_signals = (
        len(fvg["bearish"]) +
        len(obs["bearish"]) +
        len([e for e in liquidity["equal_highs"] if not e["swept"]])
    )

    return {
        "fvg": fvg,
        "order_blocks": obs,
        "liquidity_pools": liquidity,
        "current_price": current_price,
        "bull_signal_count": bull_signals,
        "bear_signal_count": bear_signals,
        "bias": "ALCISTA" if bull_signals > bear_signals else "BAJISTA" if bear_signals > bull_signals else "NEUTRAL",
    }

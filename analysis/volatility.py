"""
analysis/volatility.py — ATR, Bollinger Bands, Keltner, Squeeze y
cálculo dinámico de stops, take-profits y rango intradía.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def calculate_atr(df: pd.DataFrame, period: Optional[int] = None) -> pd.Series:
    """Calcula ATR (Average True Range)."""
    p = period or config.get("volatility.atr_period", 14)
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(p).mean()
    return atr


def calculate_bollinger_bands(
    df: pd.DataFrame,
    period: Optional[int] = None,
    std: Optional[float] = None,
) -> dict:
    """Calcula Bandas de Bollinger."""
    p = period or config.get("volatility.bb_period", 20)
    s = std or config.get("volatility.bb_std", 2.0)

    ma = df["Close"].rolling(p).mean()
    std_dev = df["Close"].rolling(p).std()

    upper = ma + s * std_dev
    lower = ma - s * std_dev
    width = upper - lower
    pct_b = (df["Close"] - lower) / (width.replace(0, np.nan))

    current = float(df["Close"].iloc[-1])
    return {
        "upper": round(float(upper.iloc[-1]), 6) if not pd.isna(upper.iloc[-1]) else None,
        "middle": round(float(ma.iloc[-1]), 6) if not pd.isna(ma.iloc[-1]) else None,
        "lower": round(float(lower.iloc[-1]), 6) if not pd.isna(lower.iloc[-1]) else None,
        "width": round(float(width.iloc[-1]), 6) if not pd.isna(width.iloc[-1]) else None,
        "pct_b": round(float(pct_b.iloc[-1]), 3) if not pd.isna(pct_b.iloc[-1]) else None,
        "current": current,
        "position": (
            "sobre upper" if current > float(upper.iloc[-1] or 0) else
            "bajo lower" if current < float(lower.iloc[-1] or 0) else
            "dentro de bandas"
        ),
        "upper_series": upper.round(6).tolist(),
        "lower_series": lower.round(6).tolist(),
        "middle_series": ma.round(6).tolist(),
    }


def calculate_keltner(
    df: pd.DataFrame,
    period: Optional[int] = None,
    atr_mult: Optional[float] = None,
) -> dict:
    """Calcula Canal de Keltner."""
    p = period or config.get("volatility.keltner_period", 20)
    mult = atr_mult or config.get("volatility.keltner_atr_mult", 1.5)

    ema = df["Close"].ewm(span=p, adjust=False).mean()
    atr = calculate_atr(df, p)

    upper = ema + mult * atr
    lower = ema - mult * atr

    current = float(df["Close"].iloc[-1])
    return {
        "upper": round(float(upper.iloc[-1]), 6) if not pd.isna(upper.iloc[-1]) else None,
        "middle": round(float(ema.iloc[-1]), 6) if not pd.isna(ema.iloc[-1]) else None,
        "lower": round(float(lower.iloc[-1]), 6) if not pd.isna(lower.iloc[-1]) else None,
        "current": current,
    }


def detect_squeeze(bb: dict, kc: dict) -> dict:
    """
    Detecta Squeeze de volatilidad: BB dentro de Keltner → compresión.
    Salida del squeeze → expansión de volatilidad inminente.
    """
    if not all([bb.get("upper"), bb.get("lower"), kc.get("upper"), kc.get("lower")]):
        return {"in_squeeze": False, "description": "Datos insuficientes"}

    bb_upper = bb["upper"]
    bb_lower = bb["lower"]
    kc_upper = kc["upper"]
    kc_lower = kc["lower"]

    in_squeeze = bb_upper < kc_upper and bb_lower > kc_lower

    return {
        "in_squeeze": in_squeeze,
        "description": (
            "⚡ SQUEEZE ACTIVO — Volatilidad comprimida, expansión inminente" if in_squeeze
            else "✅ Sin squeeze — Volatilidad normal"
        ),
        "bb_width": round(bb_upper - bb_lower, 6) if bb_upper and bb_lower else None,
        "kc_width": round(kc_upper - kc_lower, 6) if kc_upper and kc_lower else None,
    }


def volatility_percentile(df: pd.DataFrame, period: int = 252) -> dict:
    """
    Calcula el percentil de volatilidad actual vs. el histórico.
    Ayuda a saber si estamos en un entorno de alta o baja volatilidad.
    """
    atr_series = calculate_atr(df)
    atr_pct = atr_series / df["Close"] * 100  # ATR como % del precio

    lookback = min(period, len(atr_pct.dropna()))
    recent = atr_pct.dropna().iloc[-lookback:]

    current_atr_pct = float(recent.iloc[-1])

    pct_rank = int(np.sum(recent.values < current_atr_pct) / len(recent) * 100)

    vol_regime = (
        "MUY BAJA" if pct_rank < 20 else
        "BAJA" if pct_rank < 40 else
        "NORMAL" if pct_rank < 60 else
        "ALTA" if pct_rank < 80 else
        "MUY ALTA"
    )

    return {
        "current_atr_pct": round(current_atr_pct, 3),
        "percentile_rank": pct_rank,
        "regime": vol_regime,
        "description": f"Volatilidad en percentil {pct_rank} — Régimen: {vol_regime}",
    }


def calculate_stops_targets(
    current_price: float,
    direction: str,
    df: pd.DataFrame,
    atr_period: Optional[int] = None,
    sl_mult: Optional[float] = None,
    tp1_mult: Optional[float] = None,
    tp2_mult: Optional[float] = None,
    capital: float = 10000.0,
    risk_pct: float = 1.0,
) -> dict:
    """
    Calcula Stops y Take-Profits dinámicos basados en ATR.

    Parameters
    ----------
    direction : 'long' o 'short'
    """
    atr_p = atr_period or config.get("volatility.atr_period", 14)
    sl_m = sl_mult or config.get("volatility.atr_sl_multiplier", 2.0)
    tp1_m = tp1_mult or config.get("volatility.atr_tp_multiplier_1", 3.0)
    tp2_m = tp2_mult or config.get("volatility.atr_tp_multiplier_2", 5.0)

    atr = calculate_atr(df, atr_p)
    atr_val = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else current_price * 0.01

    if direction == "long":
        sl = current_price - sl_m * atr_val
        tp1 = current_price + tp1_m * atr_val
        tp2 = current_price + tp2_m * atr_val
    else:  # short
        sl = current_price + sl_m * atr_val
        tp1 = current_price - tp1_m * atr_val
        tp2 = current_price - tp2_m * atr_val

    risk_amount = abs(current_price - sl)
    risk_pct_trade = risk_amount / current_price * 100
    rr1 = abs(tp1 - current_price) / risk_amount if risk_amount > 0 else 0
    rr2 = abs(tp2 - current_price) / risk_amount if risk_amount > 0 else 0

    # Tamaño de posición por riesgo
    max_loss = capital * risk_pct / 100
    position_size = max_loss / risk_amount if risk_amount > 0 else 0

    return {
        "direction": direction,
        "entry": round(current_price, 6),
        "stop_loss": round(sl, 6),
        "take_profit_1": round(tp1, 6),
        "take_profit_2": round(tp2, 6),
        "atr": round(atr_val, 6),
        "risk_amount": round(risk_amount, 6),
        "risk_pct": round(risk_pct_trade, 2),
        "rr_tp1": round(rr1, 2),
        "rr_tp2": round(rr2, 2),
        "position_size": round(position_size, 4),
        "max_loss_usd": round(max_loss, 2),
    }


def intraday_range_estimate(df: pd.DataFrame) -> dict:
    """
    Estima el rango intradía esperado para la jornada actual.
    Basado en ATR y apertura del día.
    """
    atr = calculate_atr(df)
    atr_val = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0

    last = df.iloc[-1]
    open_price = float(last["Open"])
    current_close = float(last["Close"])
    current_high = float(last["High"])
    current_low = float(last["Low"])

    expected_high = open_price + atr_val
    expected_low = open_price - atr_val

    # Rango actual vs esperado
    current_range = current_high - current_low
    range_completion = current_range / (atr_val * 2) * 100 if atr_val > 0 else 0

    return {
        "atr": round(atr_val, 6),
        "open": round(open_price, 6),
        "expected_high": round(expected_high, 6),
        "expected_low": round(expected_low, 6),
        "expected_range": round(atr_val * 2, 6),
        "current_range": round(current_range, 6),
        "range_completion_pct": round(min(range_completion, 100), 1),
        "remaining_range": round(max(0, atr_val * 2 - current_range), 6),
    }


def full_volatility_analysis(df: pd.DataFrame, capital: float = 10000.0, risk_pct: float = 1.0) -> dict:
    """Análisis completo de volatilidad y gestión de riesgo."""
    current_price = float(df["Close"].iloc[-1])

    atr_series = calculate_atr(df)
    atr_val = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else 0

    bb = calculate_bollinger_bands(df)
    kc = calculate_keltner(df)
    squeeze = detect_squeeze(bb, kc)
    vol_pct = volatility_percentile(df)
    intraday = intraday_range_estimate(df)

    stops_long = calculate_stops_targets(current_price, "long", df, capital=capital, risk_pct=risk_pct)
    stops_short = calculate_stops_targets(current_price, "short", df, capital=capital, risk_pct=risk_pct)

    return {
        "current_price": current_price,
        "atr": atr_val,
        "atr_pct": round(atr_val / current_price * 100, 3),
        "bollinger": bb,
        "keltner": kc,
        "squeeze": squeeze,
        "volatility_regime": vol_pct,
        "intraday_range": intraday,
        "stops_long": stops_long,
        "stops_short": stops_short,
    }

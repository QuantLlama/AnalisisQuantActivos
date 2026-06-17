"""
analysis/indicators.py — Cálculo de indicadores técnicos clásicos.
Implementa RSI, MACD, Medias Móviles (SMA, EMA), Estocástico y ADX de manera robusta.
"""
from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calcula Simple Moving Average (SMA)."""
    return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calcula Exponential Moving Average (EMA)."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: Optional[int] = None) -> pd.Series:
    """
    Calcula el Relative Strength Index (RSI) usando la media suavizada de Wilder.
    """
    p = period or config.get("indicators.rsi_period", 14)
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Wilder smoothing (EMA con alpha = 1/period)
    avg_gain = gain.ewm(alpha=1/p, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/p, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)  # valor neutral por defecto


def calculate_macd(
    series: pd.Series,
    fast: Optional[int] = None,
    slow: Optional[int] = None,
    signal: Optional[int] = None,
) -> dict[str, pd.Series]:
    """
    Calcula el MACD (Moving Average Convergence Divergence).
    """
    f = fast or config.get("indicators.macd_fast", 12)
    s = slow or config.get("indicators.macd_slow", 26)
    sig = signal or config.get("indicators.macd_signal", 9)

    ema_fast = calculate_ema(series, f)
    ema_slow = calculate_ema(series, s)

    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, sig)
    histogram = macd_line - signal_line

    return {
        "macd": macd_line,
        "signal": signal_line,
        "hist": histogram,
    }


def calculate_stochastic(
    df: pd.DataFrame,
    k_period: Optional[int] = None,
    d_period: Optional[int] = None,
) -> dict[str, pd.Series]:
    """
    Calcula el oscilador Estocástico (%K y %D).
    """
    kp = k_period or config.get("indicators.stoch_k", 14)
    dp = d_period or config.get("indicators.stoch_d", 3)

    low_min = df["Low"].rolling(window=kp).min()
    high_max = df["High"].rolling(window=kp).max()

    denom = high_max - low_min
    # Evitar división por cero
    stoch_k = 100 * ((df["Close"] - low_min) / denom.replace(0, np.nan))
    stoch_k = stoch_k.fillna(50.0)
    stoch_d = stoch_k.rolling(window=dp).mean().fillna(50.0)

    return {
        "k": stoch_k,
        "d": stoch_d,
    }


def calculate_adx(df: pd.DataFrame, period: Optional[int] = None) -> dict[str, pd.Series]:
    """
    Calcula el Average Directional Index (ADX) junto con +DI y -DI.
    """
    p = period or config.get("indicators.adx_period", 14)
    
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement (+DM y -DM)
    up_move = high.diff()
    down_move = low.shift(1) - low

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = pd.Series(plus_dm, index=df.index)
    minus_dm = pd.Series(minus_dm, index=df.index)

    # Suavizado de Wilder
    tr_smoothed = tr.ewm(alpha=1/p, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1/p, adjust=False).mean() / tr_smoothed.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1/p, adjust=False).mean() / tr_smoothed.replace(0, np.nan))

    # Reemplazar NaNs
    plus_di = plus_di.fillna(0.0)
    minus_di = minus_di.fillna(0.0)

    # ADX
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    dx = dx.fillna(0.0)
    adx = dx.ewm(alpha=1/p, adjust=False).mean().fillna(0.0)

    return {
        "adx": adx,
        "plus_di": plus_di,
        "minus_di": minus_di,
    }


def calculate_all_indicators(df: pd.DataFrame) -> dict:
    """
    Calcula todos los indicadores técnicos y devuelve sus últimos valores listos.
    """
    if df.empty or len(df) < 50:
        return {}

    close = df["Close"]
    
    # EMAs configuradas
    ema_periods = config.get("indicators.ema_periods", [9, 21, 50, 200])
    emas = {f"EMA_{p}": round(float(calculate_ema(close, p).iloc[-1]), 6) for p in ema_periods}

    # SMAs configuradas
    sma_periods = config.get("indicators.sma_periods", [20, 50, 200])
    smas = {f"SMA_{p}": round(float(calculate_sma(close, p).iloc[-1]), 6) for p in sma_periods}

    rsi_series = calculate_rsi(close)
    rsi_val = float(rsi_series.iloc[-1])
    
    macd_dict = calculate_macd(close)
    macd_val = float(macd_dict["macd"].iloc[-1])
    signal_val = float(macd_dict["signal"].iloc[-1])
    hist_val = float(macd_dict["hist"].iloc[-1])

    stoch_dict = calculate_stochastic(df)
    stoch_k = float(stoch_dict["k"].iloc[-1])
    stoch_d = float(stoch_dict["d"].iloc[-1])

    adx_dict = calculate_adx(df)
    adx_val = float(adx_dict["adx"].iloc[-1])
    plus_di = float(adx_dict["plus_di"].iloc[-1])
    minus_di = float(adx_dict["minus_di"].iloc[-1])

    current_price = float(close.iloc[-1])

    # Determinar momentum del RSI
    rsi_desc = "neutral"
    if rsi_val > 70:
        rsi_desc = "sobrecompra"
    elif rsi_val < 30:
        rsi_desc = "sobreventa"

    # Determinar cruce de MACD
    macd_desc = "neutral"
    if hist_val > 0 and macd_dict["hist"].iloc[-2] <= 0:
        macd_desc = "cruce alcista"
    elif hist_val < 0 and macd_dict["hist"].iloc[-2] >= 0:
        macd_desc = "cruce bajista"
    elif hist_val > 0:
        macd_desc = "alcista"
    else:
        macd_desc = "bajista"

    # Determinar fuerza de tendencia con ADX
    trend_strength = "débil"
    if adx_val > 25:
        trend_strength = "fuerte" if adx_val < 50 else "muy fuerte"
    
    trend_dir = "lateral/indeciso"
    if plus_di > minus_di and adx_val > 20:
        trend_dir = "alcista"
    elif minus_di > plus_di and adx_val > 20:
        trend_dir = "bajista"

    return {
        "price": current_price,
        "emas": emas,
        "smas": smas,
        "rsi": {
            "value": round(rsi_val, 2),
            "state": rsi_desc,
        },
        "macd": {
            "macd": round(macd_val, 6),
            "signal": round(signal_val, 6),
            "hist": round(hist_val, 6),
            "state": macd_desc,
        },
        "stochastic": {
            "k": round(stoch_k, 2),
            "d": round(stoch_d, 2),
            "state": "sobrecompra" if stoch_k > 80 else ("sobreventa" if stoch_k < 20 else "neutral"),
        },
        "adx": {
            "adx": round(adx_val, 2),
            "plus_di": round(plus_di, 2),
            "minus_di": round(minus_di, 2),
            "strength": trend_strength,
            "direction": trend_dir,
        },
    }

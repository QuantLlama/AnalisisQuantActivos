"""
analysis/volume_analysis.py — Volume Profile, VWAP, POC, VAH/VAL y absorción.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def calculate_volume_profile(
    df: pd.DataFrame,
    bins: Optional[int] = None,
    value_area_pct: Optional[float] = None,
) -> dict:
    """
    Calcula el Volume Profile (VPVR).
    Distribuye el volumen total entre rangos de precio (bins).

    Returns POC, VAH, VAL y el histograma completo.
    """
    n_bins = bins or config.get("volume.vpvr_bins", 50)
    va_pct = (value_area_pct or config.get("volume.value_area_percent", 70)) / 100

    if df.empty or "Volume" not in df.columns:
        return {}

    price_min = float(df["Low"].min())
    price_max = float(df["High"].max())
    price_range = price_max - price_min

    if price_range == 0:
        return {}

    bin_size = price_range / n_bins
    bins_edges = np.linspace(price_min, price_max, n_bins + 1)
    volume_per_bin = np.zeros(n_bins)

    for _, row in df.iterrows():
        vol = float(row["Volume"])
        lo = float(row["Low"])
        hi = float(row["High"])
        if hi == lo:
            # Asignar todo el volumen al bin del precio de cierre
            c = float(row["Close"])
            bin_idx = min(int((c - price_min) / bin_size), n_bins - 1)
            volume_per_bin[bin_idx] += vol
        else:
            # Distribuir volumen proporcionalmente entre los bins que cubre la vela
            for i in range(n_bins):
                bin_lo = bins_edges[i]
                bin_hi = bins_edges[i + 1]
                overlap_lo = max(lo, bin_lo)
                overlap_hi = min(hi, bin_hi)
                if overlap_hi > overlap_lo:
                    overlap_pct = (overlap_hi - overlap_lo) / (hi - lo)
                    volume_per_bin[i] += vol * overlap_pct

    # POC = bin con mayor volumen
    poc_idx = int(np.argmax(volume_per_bin))
    poc_price = float(bins_edges[poc_idx] + bin_size / 2)

    # Value Area: acumular bins desde POC hacia afuera hasta alcanzar va_pct del volumen total
    total_vol = float(np.sum(volume_per_bin))
    target_vol = total_vol * va_pct

    va_vol = volume_per_bin[poc_idx]
    lower_i = poc_idx
    upper_i = poc_idx

    while va_vol < target_vol and (lower_i > 0 or upper_i < n_bins - 1):
        add_up = volume_per_bin[upper_i + 1] if upper_i < n_bins - 1 else 0
        add_dn = volume_per_bin[lower_i - 1] if lower_i > 0 else 0

        if add_up >= add_dn and upper_i < n_bins - 1:
            upper_i += 1
            va_vol += volume_per_bin[upper_i]
        elif lower_i > 0:
            lower_i -= 1
            va_vol += volume_per_bin[lower_i]
        else:
            upper_i += 1
            va_vol += volume_per_bin[upper_i]

    vah = float(bins_edges[upper_i + 1])
    val = float(bins_edges[lower_i])

    # Preparar histograma para visualización
    histogram = []
    max_vol = float(np.max(volume_per_bin))
    for i in range(n_bins):
        histogram.append({
            "price": round(float(bins_edges[i] + bin_size / 2), 4),
            "volume": float(volume_per_bin[i]),
            "pct_of_max": round(float(volume_per_bin[i]) / max_vol * 100, 1) if max_vol > 0 else 0,
            "is_poc": i == poc_idx,
            "in_va": lower_i <= i <= upper_i,
        })

    return {
        "poc": round(poc_price, 6),
        "vah": round(vah, 6),
        "val": round(val, 6),
        "value_area_pct": va_pct * 100,
        "total_volume": total_vol,
        "histogram": histogram,
        "bins": n_bins,
        "price_min": price_min,
        "price_max": price_max,
    }


def calculate_vwap(df: pd.DataFrame) -> dict:
    """
    Calcula VWAP y sus bandas de desviación estándar (1σ, 2σ, 3σ).
    """
    typical_price = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = df["Volume"]

    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()

    vwap = cum_tp_vol / cum_vol.replace(0, np.nan)

    # Desviación estándar acumulada
    variance = ((typical_price - vwap) ** 2 * volume).cumsum() / cum_vol.replace(0, np.nan)
    std = np.sqrt(variance)

    current_vwap = float(vwap.iloc[-1]) if not pd.isna(vwap.iloc[-1]) else None
    current_std = float(std.iloc[-1]) if not pd.isna(std.iloc[-1]) else 0

    current_price = float(df["Close"].iloc[-1])

    bands = {}
    if current_vwap:
        for mult in [1, 2, 3]:
            bands[f"+{mult}σ"] = round(current_vwap + mult * current_std, 6)
            bands[f"-{mult}σ"] = round(current_vwap - mult * current_std, 6)

    return {
        "vwap": round(current_vwap, 6) if current_vwap else None,
        "std": round(current_std, 6),
        "bands": bands,
        "current_price": current_price,
        "price_vs_vwap": "above" if current_vwap and current_price > current_vwap else "below",
        "distance_pct": round((current_price - current_vwap) / current_vwap * 100, 2) if current_vwap else 0,
        "vwap_series": vwap.round(6).tolist(),
    }


def detect_absorption(df: pd.DataFrame) -> list[dict]:
    """
    Detecta velas de absorción: alto volumen con rango precio reducido.
    Indica posible acumulación (bullish) o distribución (bearish).
    """
    threshold = config.get("volume.absorption_threshold", 2.0)

    avg_vol = df["Volume"].rolling(20).mean()
    avg_range = (df["High"] - df["Low"]).rolling(20).mean()

    absorptions = []
    for i in range(20, len(df)):
        vol = float(df["Volume"].iloc[i])
        rng = float(df["High"].iloc[i] - df["Low"].iloc[i])
        avg_v = float(avg_vol.iloc[i])
        avg_r = float(avg_range.iloc[i])

        if avg_v == 0 or avg_r == 0:
            continue

        vol_ratio = vol / avg_v
        range_ratio = rng / avg_r

        # Absorción: volumen > threshold × promedio Y rango < promedio
        if vol_ratio >= threshold and range_ratio < 0.7:
            close = float(df["Close"].iloc[i])
            open_ = float(df["Open"].iloc[i])
            body_pct = abs(close - open_) / rng * 100 if rng > 0 else 0

            absorption_type = "alcista" if close > open_ else "bajista"
            absorptions.append({
                "date": str(df.index[i].date() if hasattr(df.index[i], "date") else df.index[i]),
                "price": round((float(df["High"].iloc[i]) + float(df["Low"].iloc[i])) / 2, 4),
                "close": round(close, 4),
                "volume": vol,
                "vol_ratio": round(vol_ratio, 2),
                "range_ratio": round(range_ratio, 2),
                "body_pct": round(body_pct, 1),
                "type": absorption_type,
            })

    return absorptions[-10:]  # últimas 10


def calculate_obv(df: pd.DataFrame) -> dict:
    """
    Calcula OBV (On-Balance Volume) y detecta divergencias.
    """
    closes = df["Close"].values
    volumes = df["Volume"].values

    obv = np.zeros(len(closes))
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv[i] = obv[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv[i] = obv[i - 1] - volumes[i]
        else:
            obv[i] = obv[i - 1]

    # Tendencia OBV (últimas 20 barras)
    lookback = min(20, len(obv))
    obv_recent = obv[-lookback:]
    price_recent = closes[-lookback:]

    obv_trend = "alcista" if obv_recent[-1] > obv_recent[0] else "bajista"
    price_trend = "alcista" if price_recent[-1] > price_recent[0] else "bajista"

    divergence = None
    if obv_trend == "alcista" and price_trend == "bajista":
        divergence = "DIVERGENCIA ALCISTA (OBV sube, precio baja) → posible reversión al alza"
    elif obv_trend == "bajista" and price_trend == "alcista":
        divergence = "DIVERGENCIA BAJISTA (OBV baja, precio sube) → posible reversión a la baja"

    return {
        "current_obv": round(float(obv[-1]), 0),
        "obv_trend": obv_trend,
        "price_trend": price_trend,
        "divergence": divergence,
        "obv_series": obv.tolist(),
    }


def full_volume_analysis(df: pd.DataFrame) -> dict:
    """Análisis completo de volumen: Volume Profile + VWAP + Absorción + OBV."""
    profile = calculate_volume_profile(df)
    vwap = calculate_vwap(df)
    absorptions = detect_absorption(df)
    obv = calculate_obv(df)

    current_price = float(df["Close"].iloc[-1])
    poc = profile.get("poc")
    vah = profile.get("vah")
    val = profile.get("val")

    # Señal de posición relativa al Value Area
    position = "dentro del Value Area"
    if vah and current_price > vah:
        position = "SOBRE Value Area (posible extensión alcista)"
    elif val and current_price < val:
        position = "BAJO Value Area (posible extensión bajista)"

    return {
        "profile": profile,
        "vwap": vwap,
        "absorptions": absorptions,
        "obv": obv,
        "current_price": current_price,
        "va_position": position,
        "poc_distance_pct": round((current_price - poc) / poc * 100, 2) if poc else 0,
    }

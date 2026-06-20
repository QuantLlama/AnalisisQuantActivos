"""
analysis/mean_reversion.py — Análisis de Reversión a la Media Institucional
Implementa cálculo de vida media (Half-Life) basado en el proceso Ornstein-Uhlenbeck,
y Z-Scores utilizando VWAP y desviación estándar para detectar sobre-extensiones extremas.
"""
import numpy as np
import pandas as pd
from scipy.stats import linregress
from typing import Dict, Any

def calculate_half_life(prices: pd.Series) -> float:
    """
    Calcula la 'vida media' de reversión a la media basándose en un proceso Ornstein-Uhlenbeck.
    Si la vida media es muy grande o negativa, la serie no revierte a la media.
    """
    price_lag = prices.shift(1)
    price_diff = prices - price_lag
    
    df = pd.DataFrame({'lag': price_lag, 'diff': price_diff}).dropna()
    
    if len(df) < 30:
        return np.inf

    # Regresión lineal: diff = lambda * lag + mu + ruido
    slope, intercept, r_value, p_value, std_err = linregress(df['lag'], df['diff'])
    
    # Si la pendiente es >= 0, es divergente/tendencial, no hay reversión
    if slope >= 0:
        return np.inf
        
    # Half-life = -ln(2) / lambda
    half_life = -np.log(2) / slope
    return half_life

def vwap_z_score(df: pd.DataFrame, window: int = 20) -> tuple[pd.Series, pd.Series]:
    """
    Calcula el Z-Score del precio con respecto a un Rolling VWAP (Volume Weighted Average Price).
    """
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    volume = df['Volume']
    
    # Rolling VWAP
    rolling_pv = (typical_price * volume).rolling(window=window).sum()
    rolling_v = volume.rolling(window=window).sum()
    vwap = rolling_pv / rolling_v.replace(0, np.nan)
    
    # Desviación estándar
    std = typical_price.rolling(window=window).std()
    
    # Z-Score
    z_score = (typical_price - vwap) / std.replace(0, np.nan)
    return z_score, vwap

def full_mean_reversion_analysis(df: pd.DataFrame, window: int = 20) -> Dict[str, Any]:
    """
    Análisis completo de reversión a la media institucional.
    Combina la validación estadística (Half-Life) con puntos de entrada tácticos (Z-Score VWAP).
    """
    if df.empty or len(df) < window + 10:
        return {"error": "Datos insuficientes para reversión a la media.", "signal_score": 0, "signal_type": "NEUTRAL"}

    close_prices = df['Close']
    current_price = close_prices.iloc[-1]
    
    # 1. Validación Estadística: Vida Media
    # Utilizamos las últimas 100 barras o la longitud completa
    hl_window = min(len(close_prices), 100)
    half_life = calculate_half_life(close_prices.iloc[-hl_window:])
    
    # Evaluar la viabilidad (si tarda más de 50 barras, es tendencial)
    is_mean_reverting = 0 < half_life < 50
    
    # 2. Señales Tácticas: Z-Score sobre VWAP
    z_scores, vwap_series = vwap_z_score(df, window=window)
    current_z = z_scores.iloc[-1]
    current_vwap = vwap_series.iloc[-1]
    
    if pd.isna(current_z) or pd.isna(current_vwap):
        return {"error": "No se pudo calcular Z-Score o VWAP.", "signal_score": 0, "signal_type": "NEUTRAL"}
    
    # Establecer umbrales institucionales (+2.5 y -2.5 sigma) y extremos (+3.0 y -3.0 sigma)
    score = 0
    signal_type = "NEUTRAL"
    
    if current_z > 2.5:
        # Sobrecomprado extremo, posible corto (venta) hacia VWAP
        score = -0.8 if is_mean_reverting else -0.4
        signal_type = "SOBRE-EXTENSIÓN ALCISTA (Posible Corto)"
        if current_z > 3.0:
            score = -1.0 if is_mean_reverting else -0.6
            signal_type = "EXTREMO ALCISTA (Alta Probabilidad de Reversión)"
            
    elif current_z < -2.5:
        # Sobrevendido extremo, posible largo (compra) hacia VWAP
        score = 0.8 if is_mean_reverting else 0.4
        signal_type = "SOBRE-EXTENSIÓN BAJISTA (Posible Largo)"
        if current_z < -3.0:
            score = 1.0 if is_mean_reverting else 0.6
            signal_type = "EXTREMO BAJISTA (Alta Probabilidad de Reversión)"

    # Calculo del Stop Loss sugerido (ej. 1.5 dev. est.)
    std = close_prices.rolling(window=window).std().iloc[-1]
    
    return {
        "z_score": float(current_z),
        "vwap": float(current_vwap),
        "half_life_bars": float(half_life) if half_life != np.inf else "Infinito",
        "is_mean_reverting_regime": bool(is_mean_reverting),
        "signal_score": float(score),
        "signal_type": signal_type,
        "target_price": float(current_vwap),
        "estimated_stop_distance": float(std * 1.5) if not pd.isna(std) else 0.0
    }

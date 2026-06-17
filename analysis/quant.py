"""
analysis/quant.py — Motor de Análisis Cuantitativo Institucional
Implementa Transformada de Fourier (FFT) para ciclos, aproximación de Order Flow 
vía divergencias de volumen, y un algoritmo de ensamble adaptativo (simulación evolutiva).
"""
import numpy as np
import pandas as pd
from typing import Dict, Any

def fourier_cycle_analysis(prices: pd.Series, top_cycles: int = 3) -> dict:
    """Aplica Fast Fourier Transform (FFT) para aislar ciclos dominantes en el precio."""
    detrended = prices - prices.rolling(window=20).mean().bfill()
    fft_vals = np.fft.fft(detrended.values)
    fft_freq = np.fft.fftfreq(len(detrended))
    
    # Ignorar frecuencias cero o negativas
    pos_mask = fft_freq > 0
    fft_vals = np.abs(fft_vals[pos_mask])
    fft_freq = fft_freq[pos_mask]
    
    # Encontrar picos principales
    indices = np.argsort(fft_vals)[::-1][:top_cycles]
    dominant_periods = [int(1 / fft_freq[i]) for i in indices if fft_freq[i] > 0]
    
    # Predecir siguiente fase basados en el ciclo principal
    if dominant_periods:
        main_cycle = dominant_periods[0]
        current_phase = len(prices) % main_cycle
        phase_status = "Expansión (Alcista)" if current_phase < main_cycle / 2 else "Contracción (Bajista)"
    else:
        main_cycle = 0
        phase_status = "Neutral"

    return {
        "main_cycle_bars": main_cycle,
        "phase": phase_status,
        "secondary_cycles": dominant_periods[1:]
    }

def order_flow_approximation(df: pd.DataFrame) -> dict:
    """
    Aproxima el Order Flow Institucional evaluando cómo se desplaza el precio 
    en relación al volumen (CVD - Cumulative Volume Delta sintético).
    """
    close = df['Close']
    open_p = df['Open']
    high = df['High']
    low = df['Low']
    vol = df['Volume']
    
    # Presión de compra/venta aproximada por la posición del cierre en la vela
    range_total = high - low
    range_total = range_total.replace(0, 1e-5) # evitar div by 0
    buy_pressure = (close - low) / range_total
    sell_pressure = (high - close) / range_total
    
    # Volumen dirigido
    buy_vol = vol * buy_pressure
    sell_vol = vol * sell_pressure
    
    cvd = (buy_vol - sell_vol).cumsum()
    
    # Divergencia: El precio sube pero el CVD baja (venta encubierta), o viceversa.
    price_trend = close.diff(5).iloc[-1]
    cvd_trend = cvd.diff(5).iloc[-1]
    
    if price_trend > 0 and cvd_trend < 0:
        of_state = "Divergencia Bajista (Absorción)"
        score = -1
    elif price_trend < 0 and cvd_trend > 0:
        of_state = "Divergencia Alcista (Acumulación)"
        score = 1
    elif price_trend > 0 and cvd_trend > 0:
        of_state = "Agresión de Compra Confirmada"
        score = 0.8
    else:
        of_state = "Agresión de Venta Confirmada"
        score = -0.8
        
    return {
        "state": of_state,
        "score": score,
        "buy_vol_ratio": (buy_vol.iloc[-10:].sum() / vol.iloc[-10:].sum()) if vol.iloc[-10:].sum() > 0 else 0.5
    }

def full_quant_analysis(df: pd.DataFrame, capital: float, risk_pct: float) -> Dict[str, Any]:
    """Genera una señal cuantitativa basada en Fourier, Order Flow y Volatilidad."""
    if len(df) < 50:
        return {"error": "Datos insuficientes para análisis Quant"}

    close_prices = df['Close']
    current_price = close_prices.iloc[-1]
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

    # Ejecutar motores
    fourier = fourier_cycle_analysis(close_prices)
    order_flow = order_flow_approximation(df)
    
    # Sistema de ensamble adaptativo
    # Pesos dinámicos: si el Order Flow es extremo, se le da más peso.
    of_weight = 0.6 if abs(order_flow['score']) > 0.8 else 0.4
    fourier_weight = 1.0 - of_weight
    
    fourier_score = 1 if "Alcista" in fourier['phase'] else -1
    final_score = (fourier_score * fourier_weight) + (order_flow['score'] * of_weight)
    
    # Determinar Setup
    if final_score > 0.3:
        direction = "COMPRA (LONG)"
        entry = current_price
        stop_loss = entry - (atr * 1.5)
        tp1 = entry + (atr * 2.0)
        tp2 = entry + (atr * 3.5)
        win_prob = min(95.0, 50 + (final_score * 40))
    elif final_score < -0.3:
        direction = "VENTA (SHORT)"
        entry = current_price
        stop_loss = entry + (atr * 1.5)
        tp1 = entry - (atr * 2.0)
        tp2 = entry - (atr * 3.5)
        win_prob = min(95.0, 50 + (abs(final_score) * 40))
    else:
        direction = "NEUTRAL"
        entry = current_price
        stop_loss = 0
        tp1 = 0
        tp2 = 0
        win_prob = 50.0

    # Riesgo
    risk_amount = capital * (risk_pct / 100)
    if stop_loss != 0 and entry != 0:
        price_risk = abs(entry - stop_loss)
        position_size = risk_amount / price_risk if price_risk > 0 else 0
    else:
        position_size = 0

    return {
        "direction": direction,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "win_probability": win_prob,
        "fourier": fourier,
        "order_flow": order_flow,
        "position_size": position_size,
        "final_score_raw": final_score
    }

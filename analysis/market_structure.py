"""
analysis/market_structure.py — Estructura de mercado: BOS, CHoCH y swings.
Implementa conceptos de Smart Money Concepts (SMC) para detectar tendencias
y rupturas estructurales en el gráfico.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd
import numpy as np

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_swings(df: pd.DataFrame, period: int = 5) -> tuple[pd.Series, pd.Series]:
    """
    Detecta Swing Highs y Swing Lows en un DataFrame.
    Un Swing High es un máximo local en un rango de +/- period velas.
    """
    highs = df["High"]
    lows = df["Low"]
    
    swing_highs = pd.Series(np.nan, index=df.index)
    swing_lows = pd.Series(np.nan, index=df.index)
    
    for i in range(period, len(df) - period):
        # Evaluar High
        cond_high = True
        for j in range(1, period + 1):
            if highs.iloc[i] < highs.iloc[i - j] or highs.iloc[i] < highs.iloc[i + j]:
                cond_high = False
                break
        if cond_high:
            swing_highs.iloc[i] = highs.iloc[i]
            
        # Evaluar Low
        cond_low = True
        for j in range(1, period + 1):
            if lows.iloc[i] > lows.iloc[i - j] or lows.iloc[i] > lows.iloc[i + j]:
                cond_low = False
                break
        if cond_low:
            swing_lows.iloc[i] = lows.iloc[i]
            
    return swing_highs, swing_lows


def analyze_market_structure(df: pd.DataFrame, period: Optional[int] = None) -> dict:
    """
    Analiza la estructura de mercado buscando:
    - Swing Highs y Swing Lows activos.
    - BOS (Break of Structure): ruptura en la dirección de la tendencia previa.
    - CHoCH (Change of Character): ruptura del swing opuesto que cambia la tendencia.
    - Tendencia actual.
    """
    p = period or config.get("sr.fractal_period", 5)
    
    if len(df) < (p * 2 + 10):
        return {
            "trend": "indeterminado",
            "last_bos": None,
            "last_choch": None,
            "swing_highs": [],
            "swing_lows": [],
        }

    # Detectar swings históricos
    swing_highs_series, swing_lows_series = detect_swings(df, period=p)
    
    # Listas de swings confirmados con sus índices y precios
    sw_highs = []
    sw_lows = []
    for idx, val in swing_highs_series.dropna().items():
        sw_highs.append({"index": df.index.get_loc(idx), "date": idx, "price": float(val)})
    for idx, val in swing_lows_series.dropna().items():
        sw_lows.append({"index": df.index.get_loc(idx), "date": idx, "price": float(val)})

    # Variables de estado para recorrer el histórico y encontrar BOS/CHoCH
    # Comenzamos asumiendo una tendencia neutral/indeterminada
    trend = "neutral" 
    last_confirmed_high = None
    last_confirmed_low = None
    
    bos_events = []
    choch_events = []
    
    # Recorremos el DataFrame cronológicamente desde donde se pueden tener swings
    for i in range(p, len(df)):
        close_price = float(df["Close"].iloc[i])
        date_str = str(df.index[i].date() if hasattr(df.index[i], "date") else df.index[i])
        
        # Actualizar último swing si se confirmó una vela atrás
        # Un swing en i-p se confirma en i
        check_idx = i - p
        if check_idx >= 0:
            if not pd.isna(swing_highs_series.iloc[check_idx]):
                last_confirmed_high = float(swing_highs_series.iloc[check_idx])
            if not pd.isna(swing_lows_series.iloc[check_idx]):
                last_confirmed_low = float(swing_lows_series.iloc[check_idx])
                
        # Evaluar rupturas si tenemos swings previos
        if trend == "neutral":
            # Si no hay tendencia, el primer cruce establece la tendencia inicial
            if last_confirmed_high and close_price > last_confirmed_high:
                trend = "alcista"
                choch_events.append({
                    "type": "alcista",
                    "price": last_confirmed_high,
                    "date": date_str,
                    "bar_index": i
                })
            elif last_confirmed_low and close_price < last_confirmed_low:
                trend = "bajista"
                choch_events.append({
                    "type": "bajista",
                    "price": last_confirmed_low,
                    "date": date_str,
                    "bar_index": i
                })
        elif trend == "alcista":
            # En tendencia alcista, romper el máximo previo es BOS (continuación)
            if last_confirmed_high and close_price > last_confirmed_high:
                bos_events.append({
                    "type": "alcista",
                    "price": last_confirmed_high,
                    "date": date_str,
                    "bar_index": i
                })
                # El swing high se rompe, el precio sigue subiendo
            # Romper el mínimo previo es CHoCH (cambio de tendencia a bajista)
            elif last_confirmed_low and close_price < last_confirmed_low:
                trend = "bajista"
                choch_events.append({
                    "type": "bajista",
                    "price": last_confirmed_low,
                    "date": date_str,
                    "bar_index": i
                })
        elif trend == "bajista":
            # En tendencia bajista, romper el mínimo previo es BOS (continuación)
            if last_confirmed_low and close_price < last_confirmed_low:
                bos_events.append({
                    "type": "bajista",
                    "price": last_confirmed_low,
                    "date": date_str,
                    "bar_index": i
                })
            # Romper el máximo previo es CHoCH (cambio de tendencia a alcista)
            elif last_confirmed_high and close_price > last_confirmed_high:
                trend = "alcista"
                choch_events.append({
                    "type": "alcista",
                    "price": last_confirmed_high,
                    "date": date_str,
                    "bar_index": i
                })

    # Ultimo BOS y CHoCH
    last_bos = bos_events[-1] if bos_events else None
    last_choch = choch_events[-1] if choch_events else None

    # Zonas de soporte/resistencia basadas en los swings más recientes
    recent_swings_high = [s["price"] for s in sw_highs[-5:]] if sw_highs else []
    recent_swings_low = [s["price"] for s in sw_lows[-5:]] if sw_lows else []

    current_price = float(df["Close"].iloc[-1])

    return {
        "trend": trend,
        "last_bos": last_bos,
        "last_choch": last_choch,
        "recent_highs": sorted(recent_swings_high, reverse=True),
        "recent_lows": sorted(recent_swings_low),
        "current_price": current_price,
        "bos_count": len(bos_events),
        "choch_count": len(choch_events),
    }

"""
analysis/report_engine.py — Motor de consolidación de reportes y generación de señales.
Recopila los datos de todos los motores de análisis y calcula una señal final
basada en confluencias técnicas de alta probabilidad.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from core.config import config
from utils.logger import get_logger

# Importar motores de análisis
from analysis.support_resistance import full_sr_analysis
from analysis.fibonacci import full_fibonacci_analysis
from analysis.gann import full_gann_analysis
from analysis.imbalance import full_imbalance_analysis
from analysis.volatility import full_volatility_analysis
from analysis.volume_analysis import full_volume_analysis
from analysis.indicators import calculate_all_indicators
from analysis.market_structure import analyze_market_structure
from analysis.quant import full_quant_analysis
from analysis.mean_reversion import full_mean_reversion_analysis

logger = get_logger(__name__)


def generate_market_report(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    capital: float = 10000.0,
    risk_percent: float = 1.0,
) -> dict:
    """
    Ejecuta todos los motores de análisis y consolida un reporte final
    con scoring de confluencias y setups de trading sugeridos (Entrada/SL/TP).
    """
    if df.empty or len(df) < 50:
        logger.warning(f"Insuficientes datos para analizar {symbol} (mínimo 50 barras).")
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "error",
            "message": "Datos insuficientes (se requieren al menos 50 filas)",
        }

    logger.info(f"Iniciando análisis consolidado para {symbol} [{timeframe}]...")

    # 1. Ejecutar cada motor de análisis
    sr_res = full_sr_analysis(df)
    fib_res = full_fibonacci_analysis(df)
    gann_res = full_gann_analysis(df)
    imb_res = full_imbalance_analysis(df)
    vol_res = full_volatility_analysis(df, capital=capital, risk_pct=risk_percent)
    volume_res = full_volume_analysis(df)
    ind_res = calculate_all_indicators(df)
    struct_res = analyze_market_structure(df)
    quant_res = full_quant_analysis(df, capital, risk_percent)
    mean_rev_res = full_mean_reversion_analysis(df)
    
    current_price = float(df["Close"].iloc[-1])
    date_now = str(df.index[-1])

    # 2. Algoritmo de Scoring y Confluencias (Escala 0-100)
    score_buy = 0
    score_sell = 0
    confluences_buy = []
    confluences_sell = []

    # --- A. Estructura de Mercado (SMC) (Max 25 pts) ---
    trend = struct_res.get("trend", "neutral")
    if trend == "alcista":
        score_buy += 25
        confluences_buy.append("Estructura de mercado alcista (BOS/CHoCH confirmados)")
    elif trend == "bajista":
        score_sell += 25
        confluences_sell.append("Estructura de mercado bajista (BOS/CHoCH confirmados)")
    else:
        score_buy += 10
        score_sell += 10

    # --- B. Medias Móviles e Indicadores de Momentum (Max 25 pts) ---
    # Alineación de EMAs
    emas = ind_res.get("emas", {})
    ema_9 = emas.get("EMA_9", 0)
    ema_21 = emas.get("EMA_21", 0)
    ema_50 = emas.get("EMA_50", 0)
    ema_200 = emas.get("EMA_200", 0)

    if ema_9 > ema_21 > ema_50:
        if current_price > ema_50:
            score_buy += 10
            confluences_buy.append("Alineación alcista de medias móviles rápidas (EMA 9 > 21 > 50)")
    elif ema_9 < ema_21 < ema_50:
        if current_price < ema_50:
            score_sell += 10
            confluences_sell.append("Alineación bajista de medias móviles rápidas (EMA 9 < 21 < 50)")

    # RSI
    rsi_val = ind_res.get("rsi", {}).get("value", 50)
    rsi_state = ind_res.get("rsi", {}).get("state", "neutral")
    if rsi_state == "sobreventa":
        score_buy += 10
        confluences_buy.append(f"RSI en sobreventa ({rsi_val})")
    elif rsi_state == "sobrecompra":
        score_sell += 10
        confluences_sell.append(f"RSI en sobrecompra ({rsi_val})")
    elif 30 <= rsi_val <= 45:
        score_buy += 5  # soporte en momentum
    elif 55 <= rsi_val <= 70:
        score_sell += 5

    # MACD
    macd_state = ind_res.get("macd", {}).get("state", "neutral")
    if "alcista" in macd_state or "cruce alcista" in macd_state:
        score_buy += 5
        if "cruce" in macd_state:
            confluences_buy.append("Cruce alcista reciente de MACD")
    if "bajista" in macd_state or "cruce bajista" in macd_state:
        score_sell += 5
        if "cruce" in macd_state:
            confluences_sell.append("Cruce bajista reciente de MACD")

    # --- C. Volumen e Imbalances (SMC/Order Flow) (Max 25 pts) ---
    # OBV
    obv_trend = volume_res.get("obv", {}).get("obv_trend", "neutral")
    obv_div = volume_res.get("obv", {}).get("divergence")
    if obv_trend == "alcista":
        score_buy += 5
    else:
        score_sell += 5

    if obv_div:
        if "ALCISTA" in obv_div:
            score_buy += 10
            confluences_buy.append("Divergencia alcista de acumulación en OBV")
        elif "BAJISTA" in obv_div:
            score_sell += 10
            confluences_sell.append("Divergencia bajista de distribución en OBV")

    # Velas de Absorción
    absorptions = volume_res.get("absorptions", [])
    if absorptions:
        last_abs = absorptions[-1]
        if last_abs["type"] == "alcista" and last_abs["range_ratio"] < 0.5:
            score_buy += 5
            confluences_buy.append(f"Absorción alcista detectada cerca de {last_abs['price']}")
        elif last_abs["type"] == "bajista" and last_abs["range_ratio"] < 0.5:
            score_sell += 5
            confluences_sell.append(f"Absorción bajista detectada cerca de {last_abs['price']}")

    # Imbalances / Order Blocks
    obs = imb_res.get("order_blocks", {}).get("bullish", [])
    fvgs_bull = imb_res.get("fvgs", {}).get("bullish", [])
    
    # Revisar si el precio actual está cerca (< 1%) de un Order Block alcista
    for ob in obs[:2]:
        ob_mid = ob["mid"]
        if 0.985 <= current_price / ob_mid <= 1.015:
            score_buy += 10
            confluences_buy.append(f"Precio testeando Order Block Alcista institucional en {ob_mid}")
            break

    for fvg in fvgs_bull[:2]:
        fvg_mid = fvg["mid"]
        if 0.99 <= current_price / fvg_mid <= 1.01:
            score_buy += 5
            confluences_buy.append(f"Precio testeando Fair Value Gap alcista activo en {fvg_mid}")
            break

    # Lado bajista
    obs_bear = imb_res.get("order_blocks", {}).get("bearish", [])
    fvgs_bear = imb_res.get("fvgs", {}).get("bearish", [])
    for ob in obs_bear[:2]:
        ob_mid = ob["mid"]
        if 0.985 <= ob_mid / current_price <= 1.015:
            score_sell += 10
            confluences_sell.append(f"Precio testeando Order Block Bajista institucional en {ob_mid}")
            break

    for fvg in fvgs_bear[:2]:
        fvg_mid = fvg["mid"]
        if 0.99 <= fvg_mid / current_price <= 1.01:
            score_sell += 5
            confluences_sell.append(f"Precio testeando Fair Value Gap bajista activo en {fvg_mid}")
            break

    # --- D. Soportes/Resistencias y Fibonacci (Max 25 pts) ---
    # Pivots y clusters
    sr_clusters = sr_res.get("clusters", [])
    pivots_raw = sr_res.get("pivots", {})
    pivots = pivots_raw.get("levels", {}) if isinstance(pivots_raw, dict) and "levels" in pivots_raw else pivots_raw
    
    # Soporte clásico cercano
    supports_dict = {key: val for key, val in pivots.items() if "S" in key}
    resistances_dict = {key: val for key, val in pivots.items() if "R" in key}
    
    for key, sup in supports_dict.items():
        if 0.99 <= current_price / sup <= 1.005:  # justo encima o sobre soporte
            score_buy += 10
            confluences_buy.append(f"Cercanía a nivel de soporte Pivote ({key}) en {sup}")
            break
            
    for key, res in resistances_dict.items():
        if 0.995 <= res / current_price <= 1.01:  # justo debajo o sobre resistencia
            score_sell += 10
            confluences_sell.append(f"Cercanía a nivel de resistencia Pivote ({key}) en {res}")
            break

    # Cluster de soportes / swings
    recent_lows = struct_res.get("recent_lows", [])
    for low in recent_lows[:2]:
        if 0.99 <= current_price / low <= 1.01:
            score_buy += 5
            confluences_buy.append(f"Precio en zona de mínimos previos (Soporte horizontal) en {low}")
            break

    recent_highs = struct_res.get("recent_highs", [])
    for high in recent_highs[:2]:
        if 0.99 <= high / current_price <= 1.01:
            score_sell += 5
            confluences_sell.append(f"Precio en zona de máximos previos (Resistencia horizontal) en {high}")
            break

    # Fibonacci Golden Ratio confluencia
    fib_levels = fib_res.get("levels", {})
    fib_618 = fib_levels.get(0.618)
    fib_500 = fib_levels.get(0.500)
    
    if fib_618 and fib_500:
        fib_zone_low = min(fib_618, fib_500)
        fib_zone_high = max(fib_618, fib_500)
        if fib_zone_low <= current_price <= fib_zone_high:
            score_buy += 10
            confluences_buy.append(f"Precio dentro de la zona de oro Fibonacci (50%-61.8%) en {fib_zone_low}-{fib_zone_high}")

    # --- E. Reversión a la Media Institucional (Max 20 pts extra) ---
    mr_score = mean_rev_res.get("signal_score", 0)
    mr_type = mean_rev_res.get("signal_type", "NEUTRAL")
    
    if mr_score > 0.3:
        pts = int(mr_score * 20)
        score_buy += pts
        confluences_buy.append(f"Señal Cuantitativa Institucional: {mr_type} (Z-Score {mean_rev_res.get('z_score')})")
    elif mr_score < -0.3:
        pts = int(abs(mr_score) * 20)
        score_sell += pts
        confluences_sell.append(f"Señal Cuantitativa Institucional: {mr_type} (Z-Score {mean_rev_res.get('z_score')})")

    # Normalizar scores a un máximo de 100
    score_buy = min(100, score_buy)
    score_sell = min(100, score_sell)

    # 3. Determinar recomendación final
    direction = "NEUTRAL"
    min_score = 55
    if score_buy >= min_score and score_buy > score_sell:
        direction = "COMPRA"
    elif score_sell >= min_score and score_sell > score_buy:
        direction = "VENTA"

    # 4. Generar Setup de Trading (Entrada / SL / TP) usando ATR
    atr = vol_res.get("atr", 0.0)
    stop_dist = vol_res.get("stop_loss_distance", atr * 2)
    targets = vol_res.get("targets", {})
    
    # Valores por defecto para el setup de riesgo
    setup = {}
    if direction == "COMPRA":
        entry = current_price
        sl = entry - stop_dist
        tp1 = entry + stop_dist * 1.5
        tp2 = entry + stop_dist * 3.0
        
        # Ajustar stop loss si hay un swing low cercano y mejor posicionado
        if recent_lows:
            for l in recent_lows:
                if entry > l > entry - stop_dist * 1.5:  # swing low lógico
                    sl = l * 0.995  # un poco abajo del swing low
                    break
        
        risk_dist = entry - sl
        reward_dist_1 = tp1 - entry
        reward_dist_2 = tp2 - entry
        
        # Calcular tamaño de la posición
        risk_cash = capital * (risk_percent / 100)
        position_size = risk_cash / risk_dist if risk_dist > 0 else 0
        
        setup = {
            "direccion": "COMPRA (Largo)",
            "entrada": round(entry, 4),
            "stop_loss": round(sl, 4),
            "take_profit_1": round(tp1, 4),
            "take_profit_2": round(tp2, 4),
            "rr_tp1": round(reward_dist_1 / risk_dist, 2) if risk_dist > 0 else 0,
            "rr_tp2": round(reward_dist_2 / risk_dist, 2) if risk_dist > 0 else 0,
            "riesgo_dinero": round(risk_cash, 2),
            "tamano_posicion": round(position_size, 4),
            "valor_nominal": round(position_size * entry, 2),
            "justificacion": confluences_buy[:4],
        }
    elif direction == "VENTA":
        entry = current_price
        sl = entry + stop_dist
        tp1 = entry - stop_dist * 1.5
        tp2 = entry - stop_dist * 3.0
        
        # Ajustar stop loss si hay un swing high cercano
        if recent_highs:
            for h in recent_highs:
                if entry < h < entry + stop_dist * 1.5:
                    sl = h * 1.005  # un poco arriba del swing high
                    break
                    
        risk_dist = sl - entry
        reward_dist_1 = entry - tp1
        reward_dist_2 = entry - tp2
        
        risk_cash = capital * (risk_percent / 100)
        position_size = risk_cash / risk_dist if risk_dist > 0 else 0

        setup = {
            "direccion": "VENTA (Corto)",
            "entrada": round(entry, 4),
            "stop_loss": round(sl, 4),
            "take_profit_1": round(tp1, 4),
            "take_profit_2": round(tp2, 4),
            "rr_tp1": round(reward_dist_1 / risk_dist, 2) if risk_dist > 0 else 0,
            "rr_tp2": round(reward_dist_2 / risk_dist, 2) if risk_dist > 0 else 0,
            "riesgo_dinero": round(risk_cash, 2),
            "tamano_posicion": round(position_size, 4),
            "valor_nominal": round(position_size * entry, 2),
            "justificacion": confluences_sell[:4],
        }
    else:
        setup = {
            "direccion": "NEUTRAL (Fuera del Mercado)",
            "entrada": round(current_price, 4),
            "stop_loss": 0.0,
            "take_profit_1": 0.0,
            "take_profit_2": 0.0,
            "rr_tp1": 0.0,
            "rr_tp2": 0.0,
            "riesgo_dinero": 0.0,
            "tamano_posicion": 0.0,
            "valor_nominal": 0.0,
            "justificacion": ["Momentum indeciso", "Falta de confluencias de soporte o resistencia robustos"],
        }

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": date_now,
        "price": current_price,
        "direction": direction,
        "score_buy": score_buy,
        "score_sell": score_sell,
        "setup": setup,
        "results": {
            "sr": sr_res,
            "fibonacci": fib_res,
            "gann": gann_res,
            "imbalance": imb_res,
            "volatility": vol_res,
            "volume": volume_res,
            "indicators": ind_res,
            "market_structure": struct_res,
            "quant": quant_res,
            "mean_reversion": mean_rev_res,
        },
    }

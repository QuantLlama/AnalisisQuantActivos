"""
analysis/quant.py — Motor de Análisis Cuantitativo Institucional
Implementa Transformada de Fourier (FFT), Order Flow Sintético y
Machine Learning (Random Forest) para un sistema evolutivo.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

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
    
    if "Taker_Buy_Volume" in df.columns and "Taker_Sell_Volume" in df.columns:
        # 1. ORDEN FLOW REAL (Ej: Binance)
        buy_vol = df["Taker_Buy_Volume"]
        sell_vol = df["Taker_Sell_Volume"]
    else:
        # 2. VSA APROXIMADO (Volume Spread Analysis para yfinance/futuros)
        # Usamos la relación entre (Cierre - Apertura) respecto al (High - Low)
        # Esto capta el "esfuerzo vs resultado" real de la vela, mucho mejor que solo Close vs Low.
        range_total = high - low
        range_total = range_total.replace(0, 1e-5) # evitar div by 0
        
        # normalized_body va de -1 a 1
        normalized_body = (close - open_p) / range_total
        
        # Transforma a porcentajes de 0 a 1 para compra y venta
        buy_pressure = (normalized_body + 1) / 2.0
        sell_pressure = 1.0 - buy_pressure
        
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

def machine_learning_prediction(df: pd.DataFrame) -> dict:
    """
    Autoaprendizaje Profundo: Entrena un modelo Random Forest al vuelo
    con features técnicas para predecir si el precio subirá o bajará
    en los próximos períodos, actuando como un sistema adaptativo.
    """
    if not ML_AVAILABLE or len(df) < 100:
        return {"ml_score": 0, "status": "No disponible / Datos Insuficientes"}

    try:
        # 1. Feature Engineering
        data = pd.DataFrame(index=df.index)
        data['Returns'] = df['Close'].pct_change()
        data['Volatility'] = (df['High'] - df['Low']) / df['Close']
        data['SMA_20'] = df['Close'].rolling(20).mean()
        data['Dist_SMA'] = (df['Close'] - data['SMA_20']) / data['SMA_20']
        
        # Momentum (RSI simple)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-9)
        data['RSI'] = 100 - (100 / (1 + rs))

        # 2. Variable Objetivo (Target): ¿Sube en las próximas 3 velas?
        data['Target'] = (df['Close'].shift(-3) > df['Close']).astype(int)

        # Limpiar NaNs
        data = data.dropna()
        if len(data) < 50:
            return {"ml_score": 0, "status": "Faltan datos tras limpieza"}

        # Separar X e y
        X = data[['Returns', 'Volatility', 'Dist_SMA', 'RSI']]
        y = data['Target']

        # Entrenar en todo el set menos la última vela (que es la que queremos predecir)
        X_train = X.iloc[:-1]
        y_train = y.iloc[:-1]
        X_test = X.iloc[-1:]

        # Estandarizar
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Entrenar Random Forest (Ensamble evolutivo)
        rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        rf.fit(X_train_scaled, y_train)

        # Predicción y Probabilidad
        prob = rf.predict_proba(X_test_scaled)[0] # [Prob Bajar, Prob Subir]
        
        # Escalar el ml_score de -1 (Venta Fuerte) a 1 (Compra Fuerte)
        prob_up = prob[1]
        ml_score = (prob_up * 2) - 1  

        status = "Fuerte Compra Predicha" if ml_score > 0.4 else "Fuerte Venta Predicha" if ml_score < -0.4 else "Incertidumbre (Rango)"

        return {
            "ml_score": ml_score,
            "status": status,
            "prob_up": prob_up * 100
        }
    except Exception as e:
        return {"ml_score": 0, "status": f"Error ML: {e}"}


def full_quant_analysis(df: pd.DataFrame, capital: float, risk_pct: float) -> Dict[str, Any]:
    """Genera una señal cuantitativa basada en Fourier, Order Flow, Volatilidad y ML."""
    if len(df) < 50:
        return {"error": "Datos insuficientes para análisis Quant"}

    close_prices = df['Close']
    current_price = close_prices.iloc[-1]
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

    # Ejecutar motores
    fourier = fourier_cycle_analysis(close_prices)
    order_flow = order_flow_approximation(df)
    ml_data = machine_learning_prediction(df)
    
    # Sistema de ensamble adaptativo
    of_weight = 0.35
    fourier_weight = 0.25
    ml_weight = 0.40
    
    fourier_score = 1 if "Alcista" in fourier['phase'] else -1
    of_score = order_flow['score']
    ml_score = ml_data.get('ml_score', 0)
    
    # Puntuación final balanceada
    final_score = (fourier_score * fourier_weight) + (of_score * of_weight) + (ml_score * ml_weight)
    
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
        "ml_data": ml_data,
        "position_size": position_size,
        "final_score_raw": final_score
    }

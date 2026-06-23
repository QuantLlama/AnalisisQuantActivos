import pandas as pd
import numpy as np
import talib

class MarketFilter:
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        """Calculates necessary indicators for filtering."""
        # Ensure we have enough data
        if len(df) < 30:
            return df
        
        # ADX (Trend Strength)
        df['ADX'] = talib.ADX(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        # RSI (Momentum)
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        
        # ATR (Volatility)
        df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=14)
        
        # EMA (Trend) - Added for v2 Validator
        df['EMA'] = talib.EMA(df['Close'], timeperiod=50)
        
        return df

    def check_conditions(self, df, signal, config):
        """
        Checks if market conditions are suitable for the signal.
        Returns: (bool, str) -> (is_valid, reason)
        """
        if df.empty or len(df) < 50: # Need 50 for EMA
            return False, "Not enough data"
            
        last_row = df.iloc[-1]
        
        # 1. Trend Filter (ADX)
        # Only trade if ADX is above a threshold (e.g., 20 or 25) to avoid ranging markets
        min_adx = config.get("min_adx", 20)
        if last_row['ADX'] < min_adx:
            return False, f"Low ADX ({last_row['ADX']:.2f} < {min_adx})"
            
        # 2. Momentum Filter (RSI)
        # Avoid buying at overbought or selling at oversold
        rsi_upper = config.get("rsi_upper", 70)
        rsi_lower = config.get("rsi_lower", 30)
        
        if signal == "BUY" and last_row['RSI'] > rsi_upper:
            return False, f"RSI Overbought ({last_row['RSI']:.2f} > {rsi_upper})"
            
        if signal == "SELL" and last_row['RSI'] < rsi_lower:
            return False, f"RSI Oversold ({last_row['RSI']:.2f} < {rsi_lower})"
            
        # 3. EMA Trend Filter (Added v2)
        # Trade only with the trend
        use_ema_filter = config.get("use_ema_filter", True)
        if use_ema_filter and 'EMA' in last_row:
            if signal == "BUY" and last_row['Close'] < last_row['EMA']:
                 return False, f"Counter Trend (Price {last_row['Close']:.2f} < EMA {last_row['EMA']:.2f})"
            if signal == "SELL" and last_row['Close'] > last_row['EMA']:
                 return False, f"Counter Trend (Price {last_row['Close']:.2f} > EMA {last_row['EMA']:.2f})"
                 
        # 4. Candle Color Confirmation (Added v2)
        # Ensure the signal candle matches direction
        require_candle_confirmation = config.get("require_candle_confirmation", True)
        if require_candle_confirmation:
            is_green = last_row['Close'] > last_row['Open']
            is_red = last_row['Close'] < last_row['Open']
            
            if signal == "BUY" and not is_green:
                return False, "Candle Color Mismatch (Red Candle for BUY)"
            if signal == "SELL" and not is_red:
                return False, "Candle Color Mismatch (Green Candle for SELL)"
            
        return True, "OK"

    def get_dynamic_threshold(self, df, multiplier=1.0):
        """Calculates a dynamic threshold based on ATR."""
        if 'ATR' not in df.columns or df.empty:
            return 0.0001 # Fallback
            
        last_atr = df['ATR'].iloc[-1]
        # Example: Threshold is 50% of ATR
        return last_atr * multiplier

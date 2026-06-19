import requests
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)

# Mapeo de timeframes de yfinance a binance
BINANCE_TF_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
    "30m": "30m", "60m": "1h", "1h": "1h",
    "2h": "2h", "4h": "4h", "6h": "6h", "8h": "8h",
    "12h": "12h", "1d": "1d", "3d": "3d", "1wk": "1w", "1mo": "1M"
}

def fetch_binance_klines(symbol: str, timeframe: str, period: str) -> pd.DataFrame:
    """
    Descarga OHLCV de Binance incluyendo el Taker Buy Volume real.
    symbol: Formato 'BTC-USD' o 'BTCUSDT'.
    """
    if "-" in symbol:
        base = symbol.split("-")[0]
        # Por defecto usar USDT para el par en Binance si el usuario pidió USD
        quote = symbol.split("-")[1].replace("USD", "USDT")
        binance_symbol = f"{base}{quote}"
    else:
        binance_symbol = symbol

    binance_tf = BINANCE_TF_MAP.get(timeframe, "1d")
    
    # Calcular startTime basado en el period ("1y", "1mo", "5d", etc)
    now = datetime.utcnow()
    delta = timedelta(days=365) # fallback
    if period.endswith("d"):
        delta = timedelta(days=int(period[:-1]))
    elif period.endswith("mo"):
        delta = timedelta(days=int(period[:-2]) * 30)
    elif period.endswith("y"):
        delta = timedelta(days=int(period[:-1]) * 365)
    elif period == "max":
        delta = timedelta(days=365*10)

    start_time = int((now - delta).timestamp() * 1000)
    
    url = "https://api.binance.com/api/v3/klines"
    limit = 1000
    all_klines = []
    
    current_start = start_time
    while True:
        params = {
            "symbol": binance_symbol.upper(),
            "interval": binance_tf,
            "startTime": current_start,
            "limit": limit
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(f"Binance API error: {resp.status_code} - {resp.text}")
                break
                
            data = resp.json()
            if not data:
                break
                
            all_klines.extend(data)
            
            # El último timestamp de los datos recibidos + 1ms
            last_time = data[-1][0]
            if len(data) < limit:
                break # Ya no hay más datos
            current_start = last_time + 1
            
            if current_start > int(now.timestamp() * 1000):
                break
                
        except Exception as e:
            logger.error(f"Error fetching from Binance: {e}")
            break

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(all_klines, columns=[
        "Open_time", "Open", "High", "Low", "Close", "Volume",
        "Close_time", "Quote_asset_volume", "Number_of_trades",
        "Taker_buy_base_asset_volume", "Taker_buy_quote_asset_volume", "Ignore"
    ])
    
    # Convertir tipos
    cols_to_float = ["Open", "High", "Low", "Close", "Volume", "Taker_buy_base_asset_volume"]
    for col in cols_to_float:
        df[col] = df[col].astype(float)
        
    # Taker_buy_base_asset_volume = Compras reales a mercado (Ask)
    df["Taker_Buy_Volume"] = df["Taker_buy_base_asset_volume"]
    # Ventas reales a mercado (Bid) = Total Volume - Taker Buy Volume
    df["Taker_Sell_Volume"] = df["Volume"] - df["Taker_Buy_Volume"]
    
    # Set index
    df["Date"] = pd.to_datetime(df["Open_time"], unit="ms")
    df.set_index("Date", inplace=True)
    
    return df[["Open", "High", "Low", "Close", "Volume", "Taker_Buy_Volume", "Taker_Sell_Volume"]]

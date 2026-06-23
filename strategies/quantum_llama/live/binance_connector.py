import os
import sys
from rich.console import Console

console = Console()

# Evitar colisión del módulo "utils" entre FLUX y la estrategia
original_path = sys.path[0]
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from core.binance_trader import send_binance_order
from core.order_builder import OrderSpec
from core.binance_provider import fetch_binance_klines

# Restaurar el path original
sys.path.pop(0)

class BinanceConnector:
    def __init__(self):
        self.connected = False

    def connect(self):
        console.print("[green]Conectado a Binance (vía FLUX)[/green]")
        self.connected = True
        return True

    def shutdown(self):
        self.connected = False

    def get_balance(self):
        return 0.0

    def get_equity(self):
        return 0.0

    def get_latest_candles(self, symbol, timeframe="1m", n=100):
        # Fetch directly from Binance Provider
        df = fetch_binance_klines(symbol, timeframe, "5d")
        if df is not None and not df.empty:
            df = df.tail(n).copy()
            df.reset_index(inplace=True)
            df.rename(columns={'Date': 'time'}, inplace=True)
            return df
        return None

    def get_current_price(self, symbol):
        return None

    def get_positions(self, symbol=None):
        return []

    def place_order(self, symbol, order_type, volume, sl=None, tp=None):
        if not self.connected:
            return None
        
        spec = OrderSpec(
            symbol=symbol,
            side=order_type,
            order_type="MARKET",
            size_usd=1000, 
            entry_price=None,
            sl=sl or 0.0,
            tp1=tp or 0.0,
            tp2=0.0
        )
        spec.lots = float(volume)
        
        result = send_binance_order(spec, paper=False)
        
        if result.get("ok"):
            console.print(f"[green]Orden {order_type} ejecutada en Binance[/green]")
            return result
        else:
            console.print(f"[red]Error enviando orden Binance: {result.get('error')}[/red]")
            return None

    def close_position(self, ticket, symbol=None):
        return False

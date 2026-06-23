import os
import sys
from rich.console import Console

console = Console()

# Evitar colisión del módulo "utils" entre FLUX y la estrategia
original_path = sys.path[0]
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from core.ninjatrader_trader import send_ninjatrader_order
from core.order_builder import OrderSpec

# Restaurar el path original
sys.path.pop(0)

class NinjaTraderConnector:
    def __init__(self):
        self.connected = False

    def connect(self):
        console.print("[green]Conectado a NinjaTrader 8 (Bridge)[/green]")
        self.connected = True
        return True

    def shutdown(self):
        self.connected = False

    def get_balance(self):
        return 0.0

    def get_equity(self):
        return 0.0

    def get_latest_candles(self, symbol, timeframe="1m", n=100):
        # Para NT8, la data real puede venir de MT5 o Yahoo, pero la estrategia de live_trade.py 
        # asume que el conector provee las velas. En QuantumLlama original quizás NT8 no proveía datos.
        console.print("[yellow]NT8 Connector: Obtención de datos no implementada directamente. Usando fallback de datos si está disponible.[/yellow]")
        return None

    def get_current_price(self, symbol):
        return None

    def get_positions(self, symbol=None):
        return []

    def place_order(self, symbol, order_type, volume, sl=None, tp=None):
        if not self.connected:
            return None
        
        # order_type is "BUY" or "SELL"
        spec = OrderSpec(
            symbol=symbol,
            side=order_type,
            order_type="MARKET",
            size_usd=1000, # Fake, lots is used
            entry_price=None,
            sl=sl or 0.0,
            tp1=tp or 0.0,
            tp2=0.0
        )
        spec.lots = float(volume)
        
        result = send_ninjatrader_order(spec, paper=False)
        
        if result.get("ok"):
            console.print(f"[green]Orden {order_type} enviada a NinjaTrader 8[/green]")
            return result
        else:
            console.print(f"[red]Error enviando orden a NinjaTrader: {result.get('error')}[/red]")
            return None

    def close_position(self, ticket, symbol=None):
        return False

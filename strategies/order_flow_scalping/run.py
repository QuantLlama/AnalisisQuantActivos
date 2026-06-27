import sys
import os
import collections
import time
import numpy as np
import pandas as pd
from collections import deque

# Add project root to sys.path to allow root-level imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.order_executor import order_executor
from core.order_builder import OrderSpec
from analysis.imbalance import calculate_l2_ofi, calculate_tick_volume_ofi

class OrderFlowScalpingStrategy:
    def __init__(self, config_dict=None):
        self.config = config_dict or {
            "ofi_threshold": 2.5,
            "max_slippage_pips": 2.0,
            "atr_period": 14,
            "sl_offset_multiplier": 0.5,
            "sweep_lookback_ticks": 50
        }
        self.swing_highs = deque(maxlen=20)
        self.swing_lows = deque(maxlen=20)
        self.active_fvgs = []
        self.ofi_z_scores = deque(maxlen=100)
        self.tick_history = deque(maxlen=200)
        self.bar_history = deque(maxlen=50)

    def is_slippage_acceptable(self, projected_slippage: float) -> bool:
        return projected_slippage <= self.config.get("max_slippage_pips", 2.0)

    def process_tick(self, tick: dict, projected_slippage: float = 0.0):
        self.tick_history.append(tick)
        price = tick.get("close", tick.get("low", 0.0))
        
        # Track swing high/low points based on tick history window
        if len(self.tick_history) >= 3:
            lows = [t.get("low") for t in list(self.tick_history)[-5:]]
            highs = [t.get("high") for t in list(self.tick_history)[-5:]]
            # Simple local extrema
            for i in range(1, len(lows) - 1):
                if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                    self.swing_lows.append(lows[i])
            for i in range(1, len(highs) - 1):
                if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                    self.swing_highs.append(highs[i])
                    
        # Check sweep and entry triggers
        is_sweep, sweep_type = self.detect_sweep(tick)
        if is_sweep and self.ofi_z_scores and self.is_slippage_acceptable(projected_slippage):
            z_score = self.ofi_z_scores[-1]
            fvg_present = len(self.active_fvgs) > 0
            
            if sweep_type == "BULLISH" and z_score >= self.config.get("ofi_threshold", 2.5) and fvg_present:
                # Trigger Entry BUY
                atr = self.calculate_atr()
                sl = tick.get("low") - self.config.get("sl_offset_multiplier", 0.5) * atr
                tp1 = price + (price - sl)
                tp2 = self.swing_highs[-1] if self.swing_highs else price + 2 * (price - sl)
                
                spec = OrderSpec(
                    symbol=tick.get("symbol", "BTCUSDT"),
                    side="BUY",
                    order_type="MARKET",
                    entry_price=price,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    size_usd=100.0,
                    lots=None,
                    source="order_flow_scalping",
                    confidence=0.8,
                    rr=(tp1 - price)/(price - sl),
                    notes="OFI + Sweep + FVG Entry"
                )
                order_executor.send(spec, broker="binance_futures")

    def detect_sweep(self, tick: dict) -> tuple[bool, str]:
        # Bullish Sweep: Low sweeps a previous Swing Low, but current price closes above that swing low level.
        price = tick.get("close")
        low = tick.get("low")
        high = tick.get("high")
        
        if not self.swing_lows and not self.swing_highs:
            return False, "NEUTRAL"
            
        if self.swing_lows:
            recent_low = self.swing_lows[-1]
            if low < recent_low and price > recent_low:
                return True, "BULLISH"
                
        if self.swing_highs:
            recent_high = self.swing_highs[-1]
            if high > recent_high and price < recent_high:
                return True, "BEARISH"
                
        return False, "NEUTRAL"

    def process_bar(self, bar: dict):
        self.bar_history.append(bar)
        # FVG Detection on last 3 bars
        if len(self.bar_history) >= 3:
            bars = list(self.bar_history)[-3:]
            # Bullish FVG: Low of bar 3 > High of bar 1
            if bars[2]["low"] > bars[0]["high"]:
                self.active_fvgs.append({
                    "type": "alcista",
                    "bottom": bars[0]["high"],
                    "top": bars[2]["low"],
                    "mid": (bars[0]["high"] + bars[2]["low"]) / 2.0
                })
            # Bearish FVG: High of bar 3 < Low of bar 1
            elif bars[2]["high"] < bars[0]["low"]:
                self.active_fvgs.append({
                    "type": "bajista",
                    "bottom": bars[2]["high"],
                    "top": bars[0]["low"],
                    "mid": (bars[2]["high"] + bars[0]["low"]) / 2.0
                })

    def calculate_atr(self) -> float:
        # Simple fallback ATR calculation
        if not self.bar_history:
            return 1.0
        ranges = [b["high"] - b["low"] for b in self.bar_history]
        return sum(ranges) / len(ranges)

def main():
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, FloatPrompt, IntPrompt
    from core.data_provider import DataProvider
    from core.order_executor import order_executor
    from core.config import config
    import random
    
    console = Console()
    mode = order_executor.mode.upper() # "LIVE" or "PAPER"
    
    console.print(Panel(
        "[bold cyan]ORDER FLOW SCALPING ENGINE v1.0.0[/bold cyan]\n"
        "[white]Estrategia Institucional basada en Microestructura y Flujo de Órdenes[/white]\n\n"
        f"Modo de Operación: " + ("[bold green]REAL (LIVE)[/bold green]" if mode == "LIVE" else "[bold yellow]SIMULADO (PAPER)[/bold yellow]"),
        border_style="cyan"
    ))
    
    symbol = Prompt.ask("Seleccioná el símbolo a operar", choices=["BTC-USDT", "MES", "MNQ", "GC", "CL"], default="BTC-USDT")
    threshold = FloatPrompt.ask("Umbral de OFI (Z-Score)", default=2.5)
    
    # Normalize input
    symbol = symbol.upper().strip()
    if symbol == "BTCUSDT":
        symbol = "BTC-USDT"
    
    # Prompt for leverage and lot size
    leverage = 1
    if symbol == "BTC-USDT":
        leverage = IntPrompt.ask("Apalancamiento (1-125)", default=10)
        lot_size = FloatPrompt.ask("Lotaje / Tamaño en BTC", default=0.01)
        config.set("trading.binance.futures_leverage", leverage)
    else:
        lot_size = FloatPrompt.ask("Lotaje / Cantidad de contratos", default=1.0)
        
    console.print(f"\n[green]Conectando con el proveedor de datos y cargando feed para [bold]{symbol}[/bold]...[/green]")
    console.print(f"[dim]Apalancamiento: {leverage}x | Lotaje: {lot_size} | Presioná Ctrl+C para detener la estrategia y volver a la consola.[/dim]\n")
    
    # Initialize strategy and provider with custom lot size
    strat = OrderFlowScalpingStrategy({
        "ofi_threshold": threshold,
        "lot_size": lot_size
    })
    provider = DataProvider()
    
    tick_count = 0
    
    try:
        while True:
            # Fetch real-time market data
            df, info = provider.fetch(symbol, timeframe="1m", period="1d", force_refresh=True, futures=(symbol == "BTC-USDT"))
            
            if df is not None and not df.empty:
                last_row = df.iloc[-1]
                price = float(last_row["Close"])
                tick = {
                    "symbol": symbol,
                    "close": price,
                    "low": float(last_row["Low"]),
                    "high": float(last_row["High"]),
                    "volume": float(last_row["Volume"])
                }
                
                # Update pivots and indicators
                strat.process_bar(tick) # Add bar to history
                
                # For real calculation, calculate OFI
                if len(df) >= 2:
                    mock_ofi = calculate_tick_volume_ofi(df.tail(2), source="binance" if symbol == "BTC-USDT" else "mt5")
                    z_score = float(mock_ofi.iloc[-1]) / (df["Volume"].tail(10).std() + 1e-9)
                    strat.ofi_z_scores.append(z_score)
                else:
                    z_score = 0.0
                
                # Process tick
                strat.process_tick(tick)
                
                # Display status line
                console.print(f"[dim]{time.strftime('%H:%M:%S')}[/dim] | Modo: [bold]{mode}[/bold] | Precio: [bold]{price:.2f}[/bold] | OFI Z-Score: {z_score:+.2f} | Pivots: {len(strat.swing_lows)}L/{len(strat.swing_highs)}H | FVGs: {len(strat.active_fvgs)}", end="\r")
            else:
                err_msg = info.get("error", "Esperando respuesta del servidor")
                console.print(f"[yellow]Esperando datos del proveedor de mercado ({err_msg})...[/yellow]      ", end="\r")
                
            time.sleep(1.0)
            tick_count += 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Estrategia detenida por el usuario.[/yellow]")

if __name__ == "__main__":
    main()

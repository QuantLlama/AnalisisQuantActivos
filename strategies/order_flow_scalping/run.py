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
    from rich.prompt import Prompt, FloatPrompt
    import random
    
    console = Console()
    console.print(Panel(
        "[bold cyan]ORDER FLOW SCALPING ENGINE v1.0.0[/bold cyan]\n"
        "[white]Estrategia Institucional basada en Microestructura y Flujo de Órdenes[/white]",
        border_style="cyan"
    ))
    
    symbol = Prompt.ask("Seleccioná el símbolo a operar", choices=["BTCUSDT", "MES", "MNQ", "GC", "CL"], default="BTCUSDT")
    threshold = FloatPrompt.ask("Umbral de OFI (Z-Score)", default=2.5)
    
    console.print(f"\n[green]Iniciando simulación de monitoreo en tiempo real para [bold]{symbol}[/bold]...[/green]")
    console.print("[dim]Presioná Ctrl+C para detener la estrategia y volver a la consola.[/dim]\n")
    
    # Initialize strategy
    strat = OrderFlowScalpingStrategy({"ofi_threshold": threshold})
    
    # Simulated realtime loop to showcase execution
    try:
        base_price = 95000.0 if symbol == "BTCUSDT" else 6000.0 if symbol == "MES" else 2000.0 if symbol == "GC" else 75.0
        tick_count = 0
        
        while True:
            # Generate dummy tick
            change = random.uniform(-10.0, 10.0) if symbol == "BTCUSDT" else random.uniform(-1.0, 1.0)
            price = base_price + change
            tick = {
                "symbol": symbol,
                "close": price,
                "low": price - random.uniform(0, 2),
                "high": price + random.uniform(0, 2),
                "volume": random.randint(1, 10)
            }
            
            # Calculate a mock Z-score for demonstration
            mock_z = random.uniform(-3.5, 3.5)
            strat.ofi_z_scores.append(mock_z)
            
            # Add some dummy swing pivots
            if tick_count % 10 == 0:
                strat.swing_lows.append(price - random.uniform(5, 10))
                strat.swing_highs.append(price + random.uniform(5, 10))
                
            # Add some dummy FVG
            if tick_count % 15 == 0:
                strat.active_fvgs.append({
                    "type": "alcista",
                    "bottom": price - 5,
                    "top": price + 5,
                    "mid": price
                })
                
            # Process tick
            strat.process_tick(tick)
            
            # Display status line
            console.print(f"[dim]{time.strftime('%H:%M:%S')}[/dim] | Precio: [bold]{price:.2f}[/bold] | OFI Z-Score: {mock_z:+.2f} | Pivots: {len(strat.swing_lows)}L/{len(strat.swing_highs)}H | FVGs Activos: {len(strat.active_fvgs)}", end="\r")
            
            time.sleep(0.5)
            tick_count += 1
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Estrategia detenida por el usuario.[/yellow]")

if __name__ == "__main__":
    main()

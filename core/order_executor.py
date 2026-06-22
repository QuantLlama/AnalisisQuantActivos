"""
core/order_executor.py — Main router for order execution.
"""
from __future__ import annotations

import json
from pathlib import Path
import datetime

from core.order_builder import OrderSpec
from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

BROKER_CHOICES = ["mt5", "binance_spot", "binance_futures"]

class OrderExecutor:
    def __init__(self):
        self.history_file = Path(".cache/order_history.json")
        self.history_file.parent.mkdir(exist_ok=True)

    @property
    def mode(self) -> str:
        return config.get("trading.mode", "paper")

    def send(self, spec: OrderSpec, broker: str) -> dict:
        if broker not in BROKER_CHOICES:
            return {"ok": False, "error": f"Broker {broker} no soportado."}
            
        if spec.sl is None:
            return {"ok": False, "error": "Stop Loss es obligatorio."}

        paper = self.mode == "paper"

        if broker == "mt5":
            from core.mt5_trader import send_mt5_order
            result = send_mt5_order(spec, paper=paper)
        elif broker == "binance_spot":
            from core.binance_trader import send_binance_spot_order
            result = send_binance_spot_order(spec, paper=paper)
        elif broker == "binance_futures":
            from core.binance_trader import send_binance_futures_order
            result = send_binance_futures_order(spec, paper=paper)
        else:
            result = {"ok": False, "error": "Not implemented"}

        self._append_history(spec, broker, result)
        return result

    def _append_history(self, spec: OrderSpec, broker: str, result: dict):
        try:
            entry = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "mode": self.mode,
                "broker": broker,
                "symbol": spec.symbol,
                "side": spec.side,
                "type": spec.order_type,
                "size_usd": spec.size_usd,
                "ok": result.get("ok"),
                "order_id": result.get("order_id"),
                "error": result.get("error")
            }
            with open(self.history_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Error guardando historial: {e}")

    def get_history(self, n: int = 20) -> list[dict]:
        if not self.history_file.exists():
            return []
        try:
            with open(self.history_file, "r") as f:
                lines = f.readlines()
            return [json.loads(line) for line in lines[-n:]]
        except Exception:
            return []

    def get_mt5_positions(self) -> list[dict]:
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                return []
            positions = mt5.positions_get()
            if not positions:
                return []
            return [
                {
                    "platform": "MT5",
                    "symbol": pos.symbol,
                    "size": pos.volume,
                    "pnl": pos.profit
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting MT5 positions: {e}")
            return []

    def get_binance_positions(self) -> list[dict]:
        try:
            from core.binance_trader import _make_exchange
            paper = self.mode == "paper"
            exchange, err = _make_exchange(paper=paper, futures=True)
            if not exchange:
                return []
            
            positions = exchange.fetch_positions()
            result = []
            for pos in positions:
                # Some ccxt versions use 'contracts', others 'info' fields.
                # 'contracts' is standard in newer ccxt for derivatives.
                size = float(pos.get("contracts", 0) or 0)
                if size == 0:
                    continue
                pnl = float(pos.get("unrealizedPnl", 0) or 0)
                symbol = pos.get("symbol", "")
                result.append({
                    "platform": "Binance Futures",
                    "symbol": symbol,
                    "size": size,
                    "pnl": pnl
                })
            return result
        except Exception as e:
            logger.error(f"Error getting Binance positions: {e}")
            return []

order_executor = OrderExecutor()

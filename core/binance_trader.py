"""
core/binance_trader.py — Binance Spot and Futures order execution.
"""
from __future__ import annotations

import os
import datetime
from typing import Any

from core.order_builder import OrderSpec
from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

def _get_ccxt():
    try:
        import ccxt
        return ccxt
    except ImportError:
        return None

def _make_exchange(paper: bool, futures: bool = False):
    ccxt = _get_ccxt()
    if not ccxt:
        return None, "ccxt not installed"

    api_key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_SECRET_KEY", "")

    exchange_class = ccxt.binanceusdm if futures else ccxt.binance
    
    exchange = exchange_class({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future' if futures else 'spot',
        }
    })

    if paper:
        exchange.set_sandbox_mode(True)

    return exchange, None

def _format_symbol(symbol: str) -> str:
    s = symbol.upper().replace("=X", "").replace("=F", "")
    if "-USDT" in s:
        s = s.replace("-USDT", "/USDT")
    elif "-USD" in s:
        s = s.replace("-USD", "/USDT")
    elif "-" in s:
        s = s.replace("-", "/")
    
    if "/" not in s:
        if s.endswith("USDT"):
            s = s[:-4] + "/USDT"
        else:
            s = s + "/USDT"
    return s

def send_binance_spot_order(spec: OrderSpec, paper: bool = True) -> dict:
    if paper:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return {
            "ok": True, 
            "mode": "paper", 
            "order_id": f"BINSPOT-PAPER-{ts}", 
            "broker": "binance_spot",
            "spec": spec.summary()
        }

    exchange, error = _make_exchange(paper=False, futures=False)
    if not exchange:
        return {"ok": False, "error": error}

    symbol = _format_symbol(spec.symbol)
    
    try:
        exchange.load_markets()
        market = exchange.market(symbol)
        
        # Calculate amount
        entry_price = spec.entry_price if spec.entry_price else exchange.fetch_ticker(symbol)['last']
        amount = spec.size_usd / entry_price
        amount = float(exchange.amount_to_precision(symbol, amount))
        
        side = spec.side.lower()
        
        if spec.order_type == "MARKET":
            order = exchange.create_order(symbol, 'market', side, amount)
            # Spot market orders don't natively support SL/TP on Binance easily without an open position concept,
            # would need separate STOP_LOSS_LIMIT orders. Leaving basic for spot.
            return {
                "ok": True,
                "mode": "live",
                "order_id": order.get("id"),
                "broker": "binance_spot"
            }
        else:
            price = float(exchange.price_to_precision(symbol, spec.entry_price))
            # Basic limit
            order = exchange.create_order(symbol, 'limit', side, amount, price)
            return {
                "ok": True,
                "mode": "live",
                "order_id": order.get("id"),
                "broker": "binance_spot"
            }

    except Exception as e:
        logger.error(f"Binance spot error: {e}")
        return {"ok": False, "error": str(e)}


def send_binance_futures_order(spec: OrderSpec, paper: bool = True) -> dict:
    if paper:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return {
            "ok": True, 
            "mode": "paper", 
            "order_id": f"BINFUT-PAPER-{ts}", 
            "broker": "binance_futures",
            "spec": spec.summary()
        }

    exchange, error = _make_exchange(paper=False, futures=True)
    if not exchange:
        return {"ok": False, "error": error}

    symbol = _format_symbol(spec.symbol)
    
    try:
        exchange.load_markets()
        
        # Set leverage
        leverage = config.get("trading.binance.futures_leverage", 1)
        try:
            exchange.set_leverage(leverage, symbol)
        except Exception as e:
            logger.warning(f"Could not set leverage: {e}")

        entry_price = spec.entry_price if spec.entry_price else exchange.fetch_ticker(symbol)['last']
        amount = spec.size_usd / entry_price
        amount = float(exchange.amount_to_precision(symbol, amount))
        
        side = spec.side.lower()
        order_type = spec.order_type.lower()
        
        params = {}
        if order_type == 'limit':
            price = float(exchange.price_to_precision(symbol, spec.entry_price))
            order = exchange.create_order(symbol, 'limit', side, amount, price, params)
        else:
            order = exchange.create_order(symbol, 'market', side, amount, None, params)

        order_id = order.get("id")

        # Place SL and TP
        stop_side = 'sell' if side == 'buy' else 'buy'
        
        sl_price = float(exchange.price_to_precision(symbol, spec.sl))
        sl_params = {'stopPrice': sl_price, 'reduceOnly': True}
        try:
            exchange.create_order(symbol, 'STOP_MARKET', stop_side, amount, None, sl_params)
        except Exception as e:
            logger.error(f"Failed to place SL: {e}")

        tp_price = float(exchange.price_to_precision(symbol, spec.tp1))
        tp_params = {'stopPrice': tp_price, 'reduceOnly': True}
        try:
            exchange.create_order(symbol, 'TAKE_PROFIT_MARKET', stop_side, amount, None, tp_params)
        except Exception as e:
            logger.error(f"Failed to place TP: {e}")

        return {
            "ok": True,
            "mode": "live",
            "order_id": order_id,
            "broker": "binance_futures"
        }

    except Exception as e:
        logger.error(f"Binance futures error: {e}")
        return {"ok": False, "error": str(e)}

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

    active_exchange = config.get("trading.active_crypto_exchange", "binance").lower()
    
    # Obtener credenciales de config.toml
    creds = config.get(f"exchanges.{active_exchange}", {})
    api_key = creds.get("apiKey", "") or os.getenv(f"{active_exchange.upper()}_API_KEY", "")
    secret = creds.get("secret", "") or os.getenv(f"{active_exchange.upper()}_SECRET_KEY", "")
    password = creds.get("password", "") or os.getenv(f"{active_exchange.upper()}_PASSWORD", "")

    # Mapear a la clase correspondiente en ccxt
    exchange_classes = {
        "binance": ccxt.binanceusdm if futures else ccxt.binance,
        "bingx": ccxt.bingx,
        "blofin": ccxt.blofin,
        "bolfin": ccxt.blofin,
        "bybit": ccxt.bybit,
        "bitmex": ccxt.bitmex
    }

    exchange_class = exchange_classes.get(active_exchange)
    if not exchange_class:
        return None, f"Exchange '{active_exchange}' no soportado o no implementado."

    config_dict = {
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
    }
    if password:
        config_dict['password'] = password

    # Configuración por defecto de tipo para Binance
    if active_exchange == "binance":
        config_dict['options'] = {
            'defaultType': 'future' if futures else 'spot',
        }

    exchange = exchange_class(config_dict)

    if paper:
        try:
            exchange.set_sandbox_mode(True)
        except Exception:
            pass

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
    active_exchange = config.get("trading.active_crypto_exchange", "binance").lower()
    broker_name = f"{active_exchange}_spot"
    if paper:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return {
            "ok": True, 
            "mode": "paper", 
            "order_id": f"CRYPTSPOT-PAPER-{ts}", 
            "broker": broker_name,
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
                "broker": broker_name
            }
        else:
            price = float(exchange.price_to_precision(symbol, spec.entry_price))
            # Basic limit
            order = exchange.create_order(symbol, 'limit', side, amount, price)
            return {
                "ok": True,
                "mode": "live",
                "order_id": order.get("id"),
                "broker": broker_name
            }

    except Exception as e:
        logger.error(f"{active_exchange} spot error: {e}")
        return {"ok": False, "error": str(e)}


def send_binance_futures_order(spec: OrderSpec, paper: bool = True) -> dict:
    active_exchange = config.get("trading.active_crypto_exchange", "binance").lower()
    broker_name = f"{active_exchange}_futures"
    if paper:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return {
            "ok": True, 
            "mode": "paper", 
            "order_id": f"CRYPTSFUT-PAPER-{ts}", 
            "broker": broker_name,
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
            "broker": broker_name
        }

    except Exception as e:
        logger.error(f"{active_exchange} futures error: {e}")
        return {"ok": False, "error": str(e)}

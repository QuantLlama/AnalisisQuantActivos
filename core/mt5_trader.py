"""
core/mt5_trader.py — MetaTrader 5 order execution.
"""
from __future__ import annotations

import datetime
from typing import Any, Optional

from core.order_builder import OrderSpec
from core.mt5_provider import _import_mt5, find_best_mt5_symbol, _initialize
from utils.logger import get_logger

logger = get_logger(__name__)


def _round_to_tick(price: float, tick_size: float) -> float:
    """Round price to the nearest valid tick for the instrument."""
    if tick_size <= 0:
        return price
    return round(round(price / tick_size) * tick_size, 10)

def send_mt5_order(spec: OrderSpec, paper: bool = True) -> dict:
    """
    Sends an order to MetaTrader 5.
    """
    if paper:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return {
            "ok": True, 
            "mode": "paper", 
            "order_id": f"MT5-PAPER-{ts}", 
            "broker": "mt5",
            "spec": spec.summary()
        }

    mt5, error = _import_mt5()
    if mt5 is None:
        return {"ok": False, "error": error}

    ok, init_error = _initialize(mt5)
    if not ok:
        return {"ok": False, "error": init_error}

    try:
        # Find symbol
        selected_symbol = find_best_mt5_symbol(mt5, spec.symbol)

        if not selected_symbol:
            return {"ok": False, "error": f"Símbolo no encontrado en MT5: {spec.symbol}"}
            
        symbol_info = mt5.symbol_info(selected_symbol)

        # Calculate lots
        # approx: size_usd / (price * contract_size)
        # We need the current ask/bid to place market orders
        tick = mt5.symbol_info_tick(selected_symbol)
        if not tick:
            return {"ok": False, "error": f"Sin ticks para {selected_symbol}"}

        tick_size = symbol_info.trade_tick_size or symbol_info.point

        price = tick.ask if spec.side == "BUY" else tick.bid
        if spec.order_type == "LIMIT" and spec.entry_price:
            price = spec.entry_price

        # Round all prices to the instrument's tick size.
        # MT5 rejects orders (10016) if SL/TP don't align to the tick grid.
        price = _round_to_tick(price, tick_size)
        sl    = _round_to_tick(spec.sl, tick_size)
        tp1   = _round_to_tick(spec.tp1, tick_size)

        # Validate SL/TP respect broker's minimum stop level
        stops_level = symbol_info.trade_stops_level  # minimum distance in points
        point = symbol_info.point
        min_stop_distance = stops_level * point
        if min_stop_distance > 0:
            sl_distance = abs(price - spec.sl)
            tp_distance = abs(price - spec.tp1)
            if sl_distance < min_stop_distance:
                return {
                    "ok": False,
                    "error": (
                        f"SL demasiado cercano al precio: distancia={sl_distance:.5f}, "
                        f"mínimo requerido={min_stop_distance:.5f} ({stops_level} puntos)"
                    ),
                }
            if tp_distance < min_stop_distance:
                return {
                    "ok": False,
                    "error": (
                        f"TP demasiado cercano al precio: distancia={tp_distance:.5f}, "
                        f"mínimo requerido={min_stop_distance:.5f} ({stops_level} puntos)"
                    ),
                }

        contract_size = symbol_info.trade_contract_size if symbol_info.trade_contract_size else 1.0
        
        # very basic lot calculation, might need adjustment based on currency
        raw_lots = spec.size_usd / (price * contract_size)
        
        step = symbol_info.volume_step
        min_vol = symbol_info.volume_min
        max_vol = symbol_info.volume_max
        
        # round to step
        lots = round(raw_lots / step) * step
        lots = max(min_vol, min(lots, max_vol))
        
        spec.lots = lots

        # Build request
        action = mt5.TRADE_ACTION_DEAL if spec.order_type == "MARKET" else mt5.TRADE_ACTION_PENDING
        
        if spec.order_type == "MARKET":
            order_type = mt5.ORDER_TYPE_BUY if spec.side == "BUY" else mt5.ORDER_TYPE_SELL
        else: # LIMIT
            order_type = mt5.ORDER_TYPE_BUY_LIMIT if spec.side == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT

        request = {
            "action": action,
            "symbol": selected_symbol,
            "volume": float(lots),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp1),
            "deviation": 20,
            "magic": 234000,
            "comment": "FLUXQuant",
            "type_time": mt5.ORDER_TIME_GTC,
            # LIMIT/STOP orders must use RETURN filling; IOC is for MARKET only
            "type_filling": mt5.ORDER_FILLING_IOC if spec.order_type == "MARKET" else mt5.ORDER_FILLING_RETURN,
        }

        result = mt5.order_send(request)
        
        if result is None:
            return {"ok": False, "error": f"Error order_send: {mt5.last_error()}"}
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {"ok": False, "error": f"Rechazado: {result.retcode} - {result.comment}"}

        return {
            "ok": True,
            "mode": "live",
            "order_id": str(result.order),
            "broker": "mt5",
            "lots": lots,
            "result": result._asdict() if hasattr(result, "_asdict") else str(result)
        }

    except Exception as e:
        logger.error(f"Excepción enviando orden MT5: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        mt5.shutdown()

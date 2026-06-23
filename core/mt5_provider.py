"""
core/mt5_provider.py — Lazy MetaTrader 5 data adapter.

MetaTrader5 is intentionally imported only inside runtime functions so the
application keeps working when the package or a terminal installation is absent.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

MT5_TF_MAP = {
    "1m": "TIMEFRAME_M1",
    "2m": "TIMEFRAME_M2",
    "3m": "TIMEFRAME_M3",
    "5m": "TIMEFRAME_M5",
    "15m": "TIMEFRAME_M15",
    "30m": "TIMEFRAME_M30",
    "60m": "TIMEFRAME_H1",
    "1h": "TIMEFRAME_H1",
    "4h": "TIMEFRAME_H4",
    "1d": "TIMEFRAME_D1",
    "5d": "TIMEFRAME_D1",
    "1wk": "TIMEFRAME_W1",
    "1mo": "TIMEFRAME_MN1",
}

TF_MINUTES = {
    "1m": 1,
    "2m": 2,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
    "1h": 60,
    "4h": 240,
    "1d": 1_440,
    "5d": 1_440,
    "1wk": 10_080,
    "1mo": 43_200,
}

PERIOD_DAYS = {
    "1d": 1,
    "5d": 5,
    "7d": 7,
    "1mo": 30,
    "3mo": 90,
    "6mo": 180,
    "1y": 365,
    "2y": 730,
    "5y": 1_825,
    "10y": 3_650,
    "ytd": max(1, (datetime.utcnow() - datetime(datetime.utcnow().year, 1, 1)).days),
    "max": 3_650,
}

DEFAULT_SYMBOL_ALIASES = {
    "EURUSD=X": ["EURUSD", "EURUSD.a", "EURUSDm", "EURUSD.r"],
    "GBPUSD=X": ["GBPUSD", "GBPUSD.a", "GBPUSDm", "GBPUSD.r"],
    "USDJPY=X": ["USDJPY", "USDJPY.a", "USDJPYm", "USDJPY.r"],
    "AUDUSD=X": ["AUDUSD", "AUDUSD.a", "AUDUSDm", "AUDUSD.r"],
    "USDCAD=X": ["USDCAD", "USDCAD.a", "USDCADm", "USDCAD.r"],
    "NZDUSD=X": ["NZDUSD", "NZDUSD.a", "NZDUSDm", "NZDUSD.r"],
    "USDCHF=X": ["USDCHF", "USDCHF.a", "USDCHFm", "USDCHF.r"],
    "EURGBP=X": ["EURGBP", "EURGBP.a", "EURGBPm", "EURGBP.r"],
    "NQ=F": ["NAS100", "US100", "USTEC", "NAS100.cash", "NQ", "NQ100"],
    "ES=F": ["US500", "SPX500", "SP500", "US500.cash", "ES", "SPX"],
    "YM=F": ["US30", "DJ30", "WallStreet30", "YM"],
    "RTY=F": ["US2000", "RUSSELL2000", "RTY"],
    "GC=F": ["XAUUSD", "GOLD", "Gold", "GC"],
    "SI=F": ["XAGUSD", "SILVER", "Silver", "SI"],
    "CL=F": ["USOIL", "WTI", "WTICOUSD", "XTIUSD", "CL"],
    "NG=F": ["NATGAS", "NGAS", "XNGUSD", "NG"],
    "AAPL": ["AAPL", "AAPL.US", "#AAPL"],
    "MSFT": ["MSFT", "MSFT.US", "#MSFT"],
    "NVDA": ["NVDA", "NVDA.US", "#NVDA"],
    "TSLA": ["TSLA", "TSLA.US", "#TSLA"],
    "SPY": ["SPY", "SPY.US", "#SPY"],
    "QQQ": ["QQQ", "QQQ.US", "#QQQ"],
}


def _import_mt5() -> tuple[Any | None, str | None]:
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5, None
    except Exception as exc:
        return None, f"MetaTrader5 no disponible: {exc}"


def _merge_aliases() -> dict[str, list[str]]:
    aliases = {k.upper(): list(v) for k, v in DEFAULT_SYMBOL_ALIASES.items()}
    configured = config.get("mt5.symbol_aliases", {}) or {}
    if isinstance(configured, dict):
        for key, values in configured.items():
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list):
                aliases[key.upper()] = [str(v) for v in values if str(v).strip()]
    return aliases


def symbol_candidates(symbol: str) -> list[str]:
    """Return broker-symbol candidates using config aliases plus safe fallbacks."""
    raw = symbol.upper().strip()
    aliases = _merge_aliases()
    candidates = list(aliases.get(raw, []))

    fallbacks = [raw]
    if raw.endswith("=X"):
        fallbacks.append(raw[:-2])
    if raw.endswith("=F"):
        fallbacks.append(raw[:-2])
    if "-" in raw:
        base, quote = raw.split("-", 1)
        fallbacks.extend([f"{base}{quote}", f"{base}{quote.replace('USD', 'USDT')}"])

    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates + fallbacks:
        if candidate and candidate not in seen:
            ordered.append(candidate)
            seen.add(candidate)
    return ordered

import re

def extract_root_symbol(symbol: str) -> str:
    s = symbol.upper().replace("=F", "").replace("=X", "").strip()
    if " " in s:
        s = s.split(" ")[0]
    match = re.match(r'^([A-Z]{1,4})[FGHJKMNQUVXZ]\d{1,2}$', s)
    if match:
        return match.group(1)
    return s

def find_best_mt5_symbol(mt5: Any, target_symbol: str) -> str | None:
    """Intenta encontrar el mejor símbolo en MT5 usando alias, exact matches o substring fuzzy matching."""
    for candidate in symbol_candidates(target_symbol):
        if mt5.symbol_select(candidate, True):
            tick = mt5.symbol_info_tick(candidate)
            info = mt5.symbol_info(candidate)
            if tick is not None or info is not None:
                return candidate
                
    clean_target = target_symbol.upper().replace("=F", "").replace("=X", "").strip()
    root_target = extract_root_symbol(target_symbol)
    
    all_symbols = mt5.symbols_get()
    if not all_symbols:
        return None
        
    best_match = None
    best_score = -1
    
    for sym_info in all_symbols:
        name = sym_info.name.upper()
        
        # El nombre debe contener al menos la raíz
        if clean_target in name or root_target in name:
            score = 100 - len(name)
            if sym_info.visible:
                score += 50
            if "!" in name or "EXPIRED" in name:
                score -= 100
                
            # Bonus si contiene el clean_target entero
            if clean_target in name and clean_target != root_target:
                score += 30
                
            if score > best_score:
                best_score = score
                best_match = sym_info.name
                
    if best_match:
        mt5.symbol_select(best_match, True)
        return best_match
        
    return None


def _initialize(mt5: Any) -> tuple[bool, str | None]:
    path = config.get("mt5.terminal_path")
    initialized = mt5.initialize(path=path) if path else mt5.initialize()
    if initialized:
        return True, None
    return False, f"MT5 initialize falló: {mt5.last_error()}"


def test_connection() -> dict[str, Any]:
    """Check package import, terminal initialization, and basic terminal metadata."""
    mt5, error = _import_mt5()
    if mt5 is None:
        return {"ok": False, "source": "MetaTrader5", "error": error}

    ok, init_error = _initialize(mt5)
    if not ok:
        return {"ok": False, "source": "MetaTrader5", "error": init_error}

    try:
        terminal = mt5.terminal_info()
        version = mt5.version()
        return {
            "ok": True,
            "source": "MetaTrader5",
            "terminal": terminal._asdict() if hasattr(terminal, "_asdict") else str(terminal),
            "version": version,
        }
    finally:
        mt5.shutdown()


def _period_start(period: str) -> datetime:
    days = PERIOD_DAYS.get(period, 365)
    return datetime.utcnow() - timedelta(days=days)


def _bar_count(timeframe: str, period: str) -> int:
    days = PERIOD_DAYS.get(period, 365)
    minutes = TF_MINUTES.get(timeframe, 1_440)
    count = int((days * 1_440) / minutes) + 10
    return max(50, min(count, int(config.get("mt5.max_bars", 5_000))))


def fetch_mt5_bars(symbol: str, timeframe: str, period: str) -> tuple[pd.DataFrame, dict]:
    """Fetch OHLCV bars from MetaTrader 5, returning an empty frame on any failure."""
    mt5, error = _import_mt5()
    if mt5 is None:
        logger.info(error)
        return pd.DataFrame(), {"source": "mt5", "error": error}

    ok, init_error = _initialize(mt5)
    if not ok:
        logger.info(init_error)
        return pd.DataFrame(), {"source": "mt5", "error": init_error}

    try:
        tf_attr = MT5_TF_MAP.get(timeframe, "TIMEFRAME_D1")
        mt5_timeframe = getattr(mt5, tf_attr)
        
        selected_symbol = find_best_mt5_symbol(mt5, symbol)
        
        if selected_symbol is None:
            error_msg = f"No se encontró símbolo MT5 para {symbol}: {mt5.last_error()}"
            logger.info(error_msg)
            return pd.DataFrame(), {"source": "mt5", "error": error_msg}
            
        symbol_info = mt5.symbol_info(selected_symbol)

        start = _period_start(period)
        rates = mt5.copy_rates_from(selected_symbol, mt5_timeframe, datetime.utcnow(), _bar_count(timeframe, period))
        if rates is None or len(rates) == 0:
            rates = mt5.copy_rates_from_pos(selected_symbol, mt5_timeframe, 0, _bar_count(timeframe, period))
        if rates is None or len(rates) == 0:
            error_msg = f"MT5 sin barras para {selected_symbol}: {mt5.last_error()}"
            logger.info(error_msg)
            return pd.DataFrame(), {"source": "mt5", "symbol": selected_symbol, "error": error_msg}

        df = pd.DataFrame(rates)
        df["Date"] = pd.to_datetime(df["time"], unit="s")
        df = df[df["Date"] >= pd.Timestamp(start)]
        if df.empty:
            return pd.DataFrame(), {"source": "mt5", "symbol": selected_symbol, "error": "MT5 no devolvió datos en el período solicitado"}

        real_volume = df.get("real_volume", pd.Series(0, index=df.index)).fillna(0)
        tick_volume = df.get("tick_volume", pd.Series(0, index=df.index)).fillna(0)
        df["Volume"] = real_volume.where(real_volume > 0, tick_volume)
        df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"}, inplace=True)
        df.set_index("Date", inplace=True)
        result = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
        result.index.name = "Date"
        result.attrs.update({"source": "mt5", "exchange": "MetaTrader5", "mt5_symbol": selected_symbol, "asset_type": "MT5"})

        info_dict = symbol_info._asdict() if hasattr(symbol_info, "_asdict") else {}
        meta = {
            "source": "mt5",
            "exchange": "MetaTrader5",
            "symbol": symbol,
            "mt5_symbol": selected_symbol,
            "name": info_dict.get("description") or selected_symbol,
            "currency": info_dict.get("currency_profit") or info_dict.get("currency_base") or "",
        }
        return result, meta
    except Exception as exc:
        logger.warning(f"Error descargando desde MT5 para {symbol}: {exc}")
        return pd.DataFrame(), {"source": "mt5", "error": str(exc)}
    finally:
        mt5.shutdown()

"""
core/data_provider.py — Multi-source data layer with persistent cache.

Routing order:
- Crypto: Binance first, yfinance fallback.
- Forex/futures/commodities/CFD/stocks: MetaTrader 5 first, yfinance fallback.
"""
from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

from core.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────
# Timeframes válidos de yfinance
# ──────────────────────────────────────────────────────
VALID_TIMEFRAMES = {
    "1m": "1m", "2m": "2m", "5m": "5m", "15m": "15m",
    "30m": "30m", "60m": "60m", "90m": "90m", "1h": "1h",
    "4h": "4h", "1d": "1d", "5d": "5d", "1wk": "1wk",
    "1mo": "1mo", "3mo": "3mo",
}

VALID_PERIODS = {
    "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
}

# Límites de datos por timeframe en yfinance
TF_PERIOD_LIMITS: dict[str, str] = {
    "1m": "7d",  "2m": "60d",  "5m": "60d",  "15m": "60d",
    "30m": "60d", "60m": "730d", "90m": "60d", "1h": "730d",
    "4h": "730d", "1d": "max",   "5d": "max",  "1wk": "max",
    "1mo": "max", "3mo": "max",
}


class DataProvider:
    """
    Proveedor de datos OHLCV con caché persistente en disco (Parquet).
    Soporta cualquier activo de Yahoo Finance: índices, forex, crypto,
    materias primas y futuros.
    """

    def __init__(self) -> None:
        self._cache_dir = Path(config.get("data.cache_dir", ".cache"))
        self._cache_enabled = config.get("data.cache_enabled", True)
        self._cache_ttl = config.get("data.cache_ttl_minutes", 15) * 60  # en segundos
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    # ──────────────────────────────────────────────
    # Interfaz pública
    # ──────────────────────────────────────────────

    def fetch(
        self,
        symbol: str,
        timeframe: str = "1d",
        period: str = "1y",
        force_refresh: bool = False,
        futures: bool = False,
    ) -> tuple[pd.DataFrame, dict]:
        """
        Descarga datos OHLCV para el símbolo indicado.

        Returns
        -------
        df      : DataFrame con columnas Open, High, Low, Close, Volume
        info    : Diccionario con metadatos del activo
        """
        symbol = symbol.upper()
        timeframe = self._normalize_tf(timeframe)
        period = self._validate_period(timeframe, period)

        cache_key = self._cache_key(symbol, timeframe, period)
        cache_file = self._cache_dir / f"{cache_key}.parquet"
        meta_file = self._cache_dir / f"{cache_key}_info.pkl"

        # Intentar desde caché
        if self._cache_enabled and not force_refresh:
            df, info = self._load_cache(cache_file, meta_file)
            if df is not None:
                logger.debug(f"Cache hit: {symbol} {timeframe} {period}")
                return df, info

        # Descargar desde el proveedor prioritario del activo.
        logger.info(f"Descargando {symbol} | TF: {timeframe} | Período: {period}")
        df, info = self._download(symbol, timeframe, period, futures)

        # Guardar en caché
        if self._cache_enabled and df is not None and not df.empty:
            self._save_cache(df, info, cache_file, meta_file)

        return df, info

    def get_info(self, symbol: str) -> dict:
        """Obtiene información detallada del activo (nombre, sector, etc.)."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            return info
        except Exception as e:
            logger.warning(f"No se pudo obtener info de {symbol}: {e}")
            return {}

    def validate_symbol(self, symbol: str) -> bool:
        """Verifica si un símbolo es válido consultando yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            return not hist.empty
        except Exception:
            return False

    def clear_cache(self, symbol: Optional[str] = None) -> int:
        """Limpia el caché. Si se indica símbolo, solo ese símbolo."""
        count = 0
        pattern = f"{symbol.upper()}_" if symbol else ""
        for f in self._cache_dir.glob("*.parquet"):
            if not pattern or f.name.startswith(pattern):
                f.unlink()
                pkl = f.with_suffix("").with_name(f.stem + "_info.pkl")
                if pkl.exists():
                    pkl.unlink()
                count += 1
        return count

    def cache_status(self) -> dict:
        """Retorna estadísticas del caché."""
        files = list(self._cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)
        return {
            "files": len(files),
            "size_mb": round(total_size / 1024 / 1024, 2),
            "dir": str(self._cache_dir),
            "ttl_minutes": self._cache_ttl // 60,
        }

    # ──────────────────────────────────────────────
    # Internals
    # ──────────────────────────────────────────────

    def _download(self, symbol: str, timeframe: str, period: str, futures: bool = False) -> tuple[pd.DataFrame, dict]:
        """Descarga real desde Binance/MT5 con fallback a yfinance."""
        asset_type = self._detect_type(symbol)
        df = pd.DataFrame()
        provider_info: dict = {}
        source = "yfinance"

        if asset_type.lower() == "crypto":
            try:
                from core.binance_provider import fetch_binance_klines
                logger.info(f"Usando Binance API para {symbol} (volumen taker real, futures={futures})")
                df = fetch_binance_klines(symbol, timeframe, period, futures)
                if df is not None and not df.empty:
                    source = "binance"
                    provider_info = {"source": "binance", "exchange": "Binance"}
            except Exception as e:
                logger.warning(f"Fallo Binance API para {symbol}, cayendo a yfinance: {e}")
        else:
            try:
                from core.mt5_provider import fetch_mt5_bars
                logger.info(f"Usando MetaTrader 5 para {symbol}")
                df, provider_info = fetch_mt5_bars(symbol, timeframe, period)
                if df is not None and not df.empty:
                    source = "mt5"
            except Exception as e:
                logger.warning(f"Fallo MetaTrader 5 para {symbol}, cayendo a yfinance: {e}")

        try:
            ticker = yf.Ticker(symbol)

            if df is None or df.empty:
                logger.info(f"Usando yfinance API para {symbol}")
                df = ticker.history(period=period, interval=timeframe, auto_adjust=True)
                if df.empty:
                    logger.warning(f"Sin datos para {symbol} {timeframe} {period}")
                    return pd.DataFrame(), {}
                
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.index = pd.to_datetime(df.index)
                df.index.name = "Date"
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                source = "yfinance"

            df = df.dropna(how="all")
            df = df[["Open", "High", "Low", "Close", "Volume", *[c for c in ("Taker_Buy_Volume", "Taker_Sell_Volume") if c in df.columns]]].copy()

            # Metadatos básicos
            try:
                raw_info = ticker.info or {}
            except Exception:
                raw_info = {}
            exchange = provider_info.get("exchange")
            if not exchange:
                exchange = "Binance" if source == "binance" else ("MetaTrader5" if source == "mt5" else raw_info.get("exchange", ""))
            info = {
                "symbol": symbol,
                "name": provider_info.get("name") or raw_info.get("longName") or raw_info.get("shortName") or symbol,
                "currency": provider_info.get("currency") or raw_info.get("currency", "USD"),
                "exchange": exchange,
                "type": asset_type,
                "source": source,
                "mt5_symbol": provider_info.get("mt5_symbol"),
                "rows": len(df),
                "start": str(df.index[0].date()),
                "end": str(df.index[-1].date()),
                "timeframe": timeframe,
                "period": period,
            }
            df.attrs.update({
                "symbol": symbol,
                "asset_type": asset_type,
                "source": source,
                "exchange": exchange,
            })
            return df, info

        except Exception as e:
            logger.error(f"Error descargando {symbol}: {e}")
            return pd.DataFrame(), {}

    def _load_cache(self, cache_file: Path, meta_file: Path) -> tuple[Optional[pd.DataFrame], dict]:
        """Carga datos del caché si no han expirado."""
        if not cache_file.exists():
            return None, {}

        # Verificar TTL
        mtime = cache_file.stat().st_mtime
        if (time.time() - mtime) > self._cache_ttl:
            logger.debug("Cache expirado")
            return None, {}

        try:
            df = pd.read_parquet(str(cache_file))
            info = {}
            if meta_file.exists():
                import pickle
                with open(meta_file, "rb") as f:
                    info = pickle.load(f)
            if info:
                df.attrs.update({
                    "symbol": info.get("symbol"),
                    "asset_type": info.get("type"),
                    "source": info.get("source"),
                    "exchange": info.get("exchange"),
                })
            return df, info
        except Exception as e:
            logger.warning(f"Error leyendo caché: {e}")
            return None, {}

    def _save_cache(self, df: pd.DataFrame, info: dict, cache_file: Path, meta_file: Path) -> None:
        """Guarda datos en caché."""
        try:
            df.to_parquet(str(cache_file))
            import pickle
            with open(meta_file, "wb") as f:
                pickle.dump(info, f)
        except Exception as e:
            logger.warning(f"Error guardando caché: {e}")

    def _cache_key(self, symbol: str, timeframe: str, period: str) -> str:
        """Genera una clave única para el caché."""
        raw = f"{symbol}_{timeframe}_{period}"
        h = hashlib.md5(raw.encode()).hexdigest()[:8]
        clean = symbol.replace("=", "").replace("^", "").replace("-", "")
        return f"{clean}_{timeframe}_{period}_{h}"

    def _normalize_tf(self, tf: str) -> str:
        """Normaliza el timeframe al formato yfinance."""
        tf = tf.lower().strip()
        aliases = {
            "h": "1h", "d": "1d", "w": "1wk", "m": "1mo",
            "daily": "1d", "weekly": "1wk", "monthly": "1mo",
            "hourly": "1h", "4hour": "4h",
        }
        return aliases.get(tf, VALID_TIMEFRAMES.get(tf, "1d"))

    def _validate_period(self, timeframe: str, period: str) -> str:
        """Ajusta el período si excede el límite del timeframe."""
        limit = TF_PERIOD_LIMITS.get(timeframe, "max")
        # Para timeframes intradía muy cortos, limitar automáticamente
        if timeframe in ("1m", "2m", "5m", "15m", "30m", "90m") and period not in ("1d", "5d", "7d", "60d"):
            logger.warning(f"TF {timeframe} limitado a 60d por yfinance. Ajustando período a '60d'.")
            return "60d"
        if period not in VALID_PERIODS:
            return "1y"
        return period

    def _detect_type(self, symbol: str) -> str:
        """Detecta el tipo de activo por el símbolo."""
        s = symbol.upper()
        if s.endswith("=X"):
            return "Forex"
        if s.endswith("=F"):
            return "Futuros/Commodities"
        if s.startswith("^"):
            return "Índice"
        if "-USD" in s or "-BTC" in s or "-ETH" in s:
            return "Crypto"
            
        # MT5 Futures heuristics (MESU26, MNQZ25, etc.)
        futures_prefixes = ("MES", "ES", "MNQ", "NQ", "MYM", "YM", "RTY", "M2K", "CL", "GC", "SI", "ZN", "ZB")
        for pref in futures_prefixes:
            if s.startswith(pref) and any(char.isdigit() for char in s):
                return "Futuros/Commodities"
                
        return "Acción/ETF"

# Instancia global
data_provider = DataProvider()

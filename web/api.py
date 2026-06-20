"""
web/api.py — API REST con FastAPI que expone todos los motores de análisis.
Sirve también los archivos estáticos del dashboard HTML.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en el path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import pandas as pd
import numpy as np

from core.data_provider import DataProvider
from analysis.support_resistance import full_sr_analysis
from analysis.fibonacci import full_fibonacci_analysis
from analysis.gann import full_gann_analysis
from analysis.imbalance import full_imbalance_analysis
from analysis.volatility import full_volatility_analysis
from analysis.volume_analysis import full_volume_analysis
from analysis.indicators import calculate_all_indicators
from analysis.market_structure import analyze_market_structure
from analysis.report_engine import generate_market_report
from utils.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Sistema de Análisis Financiero",
    description="API profesional de análisis técnico multi-activo",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_provider = DataProvider()


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _safe(val):
    """Convierte NaN/Inf a None para JSON serialization."""
    if val is None:
        return None
    try:
        f = float(val)
        if not (f == f) or f == float("inf") or f == float("-inf"):  # NaN/Inf
            return None
        return f
    except (TypeError, ValueError):
        return val


def _df_to_ohlcv(df: pd.DataFrame) -> list[dict]:
    """Convierte el DataFrame a formato OHLCV listo para TradingView Lightweight Charts."""
    rows = []
    for ts, row in df.iterrows():
        # TradingView espera tiempo en UNIX segundos (int)
        if hasattr(ts, "timestamp"):
            t = int(ts.timestamp())
        else:
            t = int(pd.Timestamp(ts).timestamp())
        rows.append({
            "time":   t,
            "open":   _safe(row["Open"]),
            "high":   _safe(row["High"]),
            "low":    _safe(row["Low"]),
            "close":  _safe(row["Close"]),
            "volume": _safe(row["Volume"]),
        })
    return rows


def _fetch_or_404(symbol: str, timeframe: str, period: str):
    """Descarga datos o lanza HTTP 404 si no hay datos."""
    df, info = _provider.fetch(symbol.upper(), timeframe, period)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"Sin datos para {symbol}")
    return df, info


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/api/ohlcv/{symbol}")
def get_ohlcv(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe yfinance"),
    period:    str = Query("1y", description="Período histórico"),
):
    """
    Retorna las velas OHLCV + volumen en formato TradingView Lightweight Charts.
    """
    df, info = _fetch_or_404(symbol, timeframe, period)
    candles = _df_to_ohlcv(df)
    return {
        "symbol":    symbol.upper(),
        "timeframe": timeframe,
        "period":    period,
        "info":      info,
        "candles":   candles,
    }


@app.get("/api/indicators/{symbol}")
def get_indicators(
    symbol:    str,
    timeframe: str = Query("1d"),
    period:    str = Query("1y"),
):
    """
    Retorna EMAs, RSI, MACD, Bandas de Bollinger y VWAP como series temporales
    para superponerlas en el gráfico.
    """
    df, _ = _fetch_or_404(symbol, timeframe, period)

    close = df["Close"]
    high  = df["High"]
    low   = df["Low"]
    vol   = df["Volume"]

    def _series(s: pd.Series) -> list[dict]:
        out = []
        for ts, v in s.items():
            if pd.isna(v):
                continue
            t = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(pd.Timestamp(ts).timestamp())
            out.append({"time": t, "value": _safe(v)})
        return out

    # ── EMAs ──
    emas = {
        "EMA_9":  _series(close.ewm(span=9,   adjust=False).mean()),
        "EMA_21": _series(close.ewm(span=21,  adjust=False).mean()),
        "EMA_50": _series(close.ewm(span=50,  adjust=False).mean()),
        "EMA_200":_series(close.ewm(span=200, adjust=False).mean()),
    }

    # ── Bollinger Bands ──
    sma20   = close.rolling(20).mean()
    std20   = close.rolling(20).std()
    bb_up   = _series(sma20 + 2 * std20)
    bb_mid  = _series(sma20)
    bb_low  = _series(sma20 - 2 * std20)

    # ── RSI(14) ──
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, float("nan"))
    rsi   = _series(100 - (100 / (1 + rs)))

    # ── MACD ──
    ema12    = close.ewm(span=12, adjust=False).mean()
    ema26    = close.ewm(span=26, adjust=False).mean()
    macd_l   = ema12 - ema26
    signal_l = macd_l.ewm(span=9, adjust=False).mean()
    hist_l   = macd_l - signal_l
    macd     = _series(macd_l)
    signal   = _series(signal_l)
    hist     = _series(hist_l)

    # ── VWAP (acumulado del período) ──
    typical = (high + low + close) / 3
    cum_pv  = (typical * vol).cumsum()
    cum_v   = vol.cumsum().replace(0, float("nan"))
    vwap    = _series(cum_pv / cum_v)

    return {
        "emas":     emas,
        "bollinger": {"upper": bb_up, "middle": bb_mid, "lower": bb_low},
        "rsi":      rsi,
        "macd":     {"macd": macd, "signal": signal, "histogram": hist},
        "vwap":     vwap,
    }


@app.get("/api/analysis/{symbol}")
def get_analysis(
    symbol:    str,
    timeframe: str = Query("1d"),
    period:    str = Query("1y"),
    capital:   float = Query(10000.0),
    risk:      float = Query(1.0),
):
    """
    Ejecuta todos los motores de análisis y retorna el reporte completo
    con soportes, resistencias, Fibonacci, Gann, imbalances, volatilidad y señal.
    """
    df, info = _fetch_or_404(symbol, timeframe, period)

    report   = generate_market_report(df, symbol.upper(), timeframe, capital, risk)
    results  = report["results"]
    vol_res  = results.get("volatility", {})
    sr_res   = results.get("sr", {})
    fib_res  = results.get("fibonacci", {})
    imb_res  = results.get("imbalance", {})
    ind_res  = results.get("indicators", {})
    ms_res   = results.get("market_structure", {})
    quant_res = results.get("quant", {})
    mean_rev_res = results.get("mean_reversion", {})

    # ── Soportes y Resistencias como niveles horizontales ──
    sr_levels = []
    for zone in sr_res.get("zones", []):
        sr_levels.append({
            "price": _safe(zone.get("price")),
            "type":  zone.get("type", "neutral"),
            "strength": _safe(zone.get("strength", 1)),
        })

    # ── Fibonacci retrocesos ──
    fib_levels = []
    retracements = fib_res.get("retracements", {}).get("levels", {})
    fib_names = fib_res.get("fib_names", {})
    for ratio, price in retracements.items():
        fib_levels.append({
            "price": _safe(price),
            "label": fib_names.get(ratio, f"{ratio*100}%"),
        })

    # ── Fair Value Gaps (imbalances) ──
    fvgs = []
    for fvg in imb_res.get("fvgs", []):
        fvgs.append({
            "top":    _safe(fvg.get("top")),
            "bottom": _safe(fvg.get("bottom")),
            "type":   fvg.get("type", "bullish"),
            "time":   fvg.get("time"),
        })

    # ── Indicadores escalares ──
    rsi_val  = _safe(ind_res.get("rsi",  {}).get("value"))
    macd_val = _safe(ind_res.get("macd", {}).get("macd"))
    adx_val  = _safe(ind_res.get("adx",  {}).get("adx"))
    stoch_k  = _safe(ind_res.get("stochastic", {}).get("k"))

    return {
        "symbol":    symbol.upper(),
        "timeframe": timeframe,
        "price":     _safe(report.get("price")),
        "date":      report.get("date"),
        "direction": report.get("direction"),
        "score_buy": _safe(report.get("score_buy")),
        "score_sell":_safe(report.get("score_sell")),
        "setup":     report.get("setup", {}),
        "market_structure": {
            "trend":      ms_res.get("trend", "neutral"),
            "last_bos":   ms_res.get("last_bos"),
            "last_choch": ms_res.get("last_choch"),
        },
        "volatility": {
            "atr":    _safe(vol_res.get("atr")),
            "atr_pct":_safe(vol_res.get("atr_pct")),
            "regime": vol_res.get("volatility_regime", {}).get("regime", ""),
        },
        "sr_levels":  sr_levels,
        "fib_levels": fib_levels,
        "fvgs":       fvgs,
        "indicators": {
            "rsi":    rsi_val,
            "macd":   macd_val,
            "adx":    adx_val,
            "stoch_k":stoch_k,
        },
        "quant": quant_res,
        "mean_reversion": mean_rev_res,
    }


@app.get("/api/watchlist/scan")
def scan_watchlist(
    symbols:   str = Query(..., description="Tickers separados por coma: BTC-USD,MES=F"),
    timeframe: str = Query("1d"),
    capital:   float = Query(10000.0),
):
    """Escanea una lista de activos y retorna un resumen comparativo."""
    results = []
    for sym in [s.strip().upper() for s in symbols.split(",") if s.strip()]:
        try:
            df, info = _provider.fetch(sym, timeframe, "3mo")
            if df is None or df.empty:
                continue
            p_start = float(df["Close"].iloc[0])
            p_end   = float(df["Close"].iloc[-1])
            perf    = ((p_end - p_start) / p_start) * 100
            vol_res = full_volatility_analysis(df, capital, 1)
            ms_res  = analyze_market_structure(df)
            results.append({
                "symbol":  sym,
                "price":   _safe(p_end),
                "change":  _safe(perf),
                "atr_pct": _safe(vol_res.get("atr_pct")),
                "trend":   ms_res.get("trend", "neutral"),
                "name":    info.get("name", sym),
            })
        except Exception as e:
            logger.warning(f"Error escaneando {sym}: {e}")
            results.append({"symbol": sym, "error": str(e)})
    return {"results": results}


# ─────────────────────────────────────────────────────────────
# Archivos estáticos del frontend
# ─────────────────────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_dashboard():
    """Sirve el dashboard HTML principal."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard no encontrado")
    return FileResponse(str(index_file))

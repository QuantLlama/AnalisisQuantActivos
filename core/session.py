"""
core/session.py — Estado de la sesión activa del usuario.
Mantiene el símbolo activo, timeframe, período y datos cargados.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from core.config import config


@dataclass
class Session:
    """Estado completo de la sesión de análisis."""

    # ── Selección de activo ──────────────────────────────────
    symbol: str = ""
    timeframe: str = ""
    period: str = ""

    # ── Datos cargados ───────────────────────────────────────
    df: Optional[pd.DataFrame] = None
    symbol_info: dict = field(default_factory=dict)

    # ── Watchlist ────────────────────────────────────────────
    watchlist: list[str] = field(default_factory=list)

    # ── Cache de resultados de análisis ──────────────────────
    last_analysis: dict = field(default_factory=dict)
    last_report: dict = field(default_factory=dict)

    # ── Capital y riesgo ─────────────────────────────────────
    capital: float = 10000.0
    risk_percent: float = 1.0

    def __post_init__(self) -> None:
        self.symbol = config.get("general.default_symbol", "BTC-USD")
        self.timeframe = config.get("general.default_timeframe", "1d")
        self.period = config.get("general.default_period", "1y")
        self.capital = config.get("risk.default_capital", 10000.0)
        self.risk_percent = config.get("risk.default_risk_percent", 1.0)

    def has_data(self) -> bool:
        """Verifica si hay datos cargados y no vacíos."""
        return self.df is not None and not self.df.empty

    def reset_analysis(self) -> None:
        """Limpia los resultados de análisis previos."""
        self.last_analysis = {}
        self.last_report = {}

    def current_price(self) -> Optional[float]:
        """Retorna el último precio de cierre disponible."""
        if self.has_data():
            return float(self.df["Close"].iloc[-1])
        return None

    def summary(self) -> dict:
        """Resumen de estado de sesión."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "period": self.period,
            "rows": len(self.df) if self.df is not None else 0,
            "has_data": self.has_data(),
            "capital": self.capital,
            "risk_percent": self.risk_percent,
            "watchlist_count": len(self.watchlist),
        }

    def __repr__(self) -> str:
        rows = len(self.df) if self.df is not None else 0
        return f"Session(symbol={self.symbol}, tf={self.timeframe}, rows={rows})"


# Instancia global de sesión
session = Session()

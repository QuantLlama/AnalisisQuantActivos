"""
core/config.py — Gestión de configuración global del sistema.
Carga config.toml con valores por defecto y permite modificación en caliente.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml

# Ruta base del proyecto
BASE_DIR = Path(__file__).parent.parent

# Ruta al archivo de configuración
CONFIG_FILE = BASE_DIR / "config.toml"

# ──────────────────────────────────────────────
# Valores por defecto (si no existe config.toml)
# ──────────────────────────────────────────────
DEFAULTS: dict[str, Any] = {
    "general": {
        "default_symbol": "BTC-USD",
        "default_timeframe": "1d",
        "default_period": "1y",
        "theme": "dark",
        "language": "es",
    },
    "data": {
        "cache_enabled": True,
        "cache_ttl_minutes": 15,
        "cache_dir": ".cache",
    },
    "fibonacci": {
        "levels": [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0],
        "extensions": [1.272, 1.618, 2.0, 2.618],
        "auto_detect_swings": True,
    },
    "gann": {
        "angles": [82.5, 75.0, 63.75, 45.0, 26.25, 15.0, 7.5],
        "square_of_9": True,
        "time_cycles": True,
    },
    "volatility": {
        "atr_period": 14,
        "atr_sl_multiplier": 2.0,
        "atr_tp_multiplier_1": 3.0,
        "atr_tp_multiplier_2": 5.0,
        "bb_period": 20,
        "bb_std": 2.0,
        "keltner_period": 20,
        "keltner_atr_mult": 1.5,
    },
    "volume": {
        "vpvr_bins": 50,
        "value_area_percent": 70,
        "absorption_threshold": 2.0,
    },
    "sr": {
        "pivot_method": "classic",
        "fractal_period": 5,
        "zone_tolerance_percent": 0.5,
        "max_levels": 10,
    },
    "imbalance": {
        "fvg_min_size_percent": 0.1,
        "show_filled": False,
        "order_block_lookback": 10,
    },
    "chart": {
        "width": 120,
        "height": 30,
        "candle_up": "green",
        "candle_down": "red",
        "show_volume": True,
        "show_indicators": True,
    },
    "indicators": {
        "rsi_period": 14,
        "macd_fast": 12,
        "macd_slow": 26,
        "macd_signal": 9,
        "ema_periods": [9, 21, 50, 200],
        "sma_periods": [20, 50, 200],
        "stoch_k": 14,
        "stoch_d": 3,
        "adx_period": 14,
    },
    "screener": {
        "crypto_symbols": ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                           "ADA-USD", "AVAX-USD", "DOT-USD", "MATIC-USD", "LINK-USD"],
        "forex_symbols": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
                          "USDCAD=X", "NZDUSD=X", "USDCHF=X", "EURGBP=X"],
        "commodity_symbols": ["GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "ZC=F", "ZS=F"],
        "indices_symbols": ["^GSPC", "^NDX", "^DJI", "^FTSE", "^DAX", "^N225", "^HSI"],
        "futures_symbols": ["ES=F", "NQ=F", "YM=F", "RTY=F", "GC=F", "CL=F"],
    },
    "risk": {
        "default_capital": 10000.0,
        "default_risk_percent": 1.0,
        "default_rr_ratio": 2.0,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Fusiona 'override' sobre 'base' de forma recursiva."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Config:
    """Gestión de configuración con acceso por puntos (config.get('sr.pivot_method'))."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = DEFAULTS.copy()
        self.load()

    def load(self) -> None:
        """Carga config.toml y lo fusiona con los defaults."""
        if CONFIG_FILE.exists():
            try:
                file_data = toml.load(str(CONFIG_FILE))
                self._data = _deep_merge(DEFAULTS, file_data)
            except Exception as e:
                print(f"[WARN] Error cargando config.toml: {e}. Usando defaults.")
                self._data = DEFAULTS.copy()
        else:
            self._data = DEFAULTS.copy()

    def save(self) -> None:
        """Guarda la configuración actual a config.toml."""
        with open(CONFIG_FILE, "w") as f:
            toml.dump(self._data, f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Acceso por clave punteada. Ejemplo: config.get('volatility.atr_period')
        """
        parts = key.split(".")
        node = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, key: str, value: Any) -> None:
        """
        Establece un valor por clave punteada.
        Ejemplo: config.set('volatility.atr_period', 21)
        """
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        # Intentar conversión de tipos inteligente
        try:
            existing = node.get(parts[-1])
            if isinstance(existing, bool):
                value = str(value).lower() in ("true", "1", "yes", "si", "sí")
            elif isinstance(existing, int):
                value = int(value)
            elif isinstance(existing, float):
                value = float(value)
            elif isinstance(existing, list) and isinstance(value, str):
                # Parsear lista desde string: "1,2,3" → [1,2,3]
                raw = [v.strip() for v in value.split(",")]
                if existing and isinstance(existing[0], float):
                    value = [float(v) for v in raw]
                elif existing and isinstance(existing[0], int):
                    value = [int(v) for v in raw]
                else:
                    value = raw
        except (ValueError, TypeError):
            pass
        node[parts[-1]] = value

    def section(self, name: str) -> dict[str, Any]:
        """Retorna una sección completa de la configuración."""
        return self._data.get(name, {})

    def all(self) -> dict[str, Any]:
        """Retorna toda la configuración."""
        return self._data

    def __repr__(self) -> str:
        return f"Config(file='{CONFIG_FILE}', sections={list(self._data.keys())})"


# Instancia global
config = Config()

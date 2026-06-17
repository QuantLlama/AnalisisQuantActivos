"""
utils/validators.py — Validadores de entrada del usuario.
"""
from __future__ import annotations

from core.data_provider import VALID_TIMEFRAMES, VALID_PERIODS


def validate_timeframe(tf: str) -> tuple[bool, str]:
    """Valida un timeframe. Retorna (válido, mensaje)."""
    tf = tf.lower().strip()
    aliases = {
        "h": "1h", "d": "1d", "w": "1wk", "m": "1mo",
        "daily": "1d", "weekly": "1wk", "monthly": "1mo",
    }
    resolved = aliases.get(tf, tf)
    if resolved in VALID_TIMEFRAMES:
        return True, resolved
    valid_list = ", ".join(sorted(VALID_TIMEFRAMES.keys()))
    return False, f"Timeframe '{tf}' inválido. Opciones: {valid_list}"


def validate_period(period: str) -> tuple[bool, str]:
    """Valida un período. Retorna (válido, mensaje)."""
    p = period.lower().strip()
    if p in VALID_PERIODS:
        return True, p
    valid_list = ", ".join(sorted(VALID_PERIODS))
    return False, f"Período '{period}' inválido. Opciones: {valid_list}"


def validate_float(value: str, name: str = "valor") -> tuple[bool, float | str]:
    """Valida que un string sea un float positivo."""
    try:
        v = float(value)
        if v <= 0:
            return False, f"{name} debe ser positivo."
        return True, v
    except ValueError:
        return False, f"{name} '{value}' no es un número válido."


def validate_int(value: str, name: str = "valor", min_val: int = 1) -> tuple[bool, int | str]:
    """Valida que un string sea un entero >= min_val."""
    try:
        v = int(value)
        if v < min_val:
            return False, f"{name} debe ser >= {min_val}."
        return True, v
    except ValueError:
        return False, f"{name} '{value}' no es un entero válido."

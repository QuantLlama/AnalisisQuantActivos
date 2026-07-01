from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from strategies.asian_session.range_calculator import AsianSessionRange


@dataclass
class BreakoutSignal:
    triggered: bool
    direction: Optional[str]
    entry_price: Optional[float]
    stop_loss: Optional[float]
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    confidence: float
    reason: str
    range_data: Optional[AsianSessionRange]


class BreakoutLogic:
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict or {}
        self.min_atr_percentile: float = float(self.config.get("min_atr_percentile", 60))
        self.atr_sl_multiplier: float = float(self.config.get("atr_sl_multiplier", 1.5))
        self.rr_target_1: float = float(self.config.get("rr_target_1", 2.0))
        self.rr_target_2: float = float(self.config.get("rr_target_2", 3.0))
        self.min_range_pct: float = float(self.config.get("min_range_pct", 0.1))

    def evaluate(
        self,
        current_price: float,
        range_data: AsianSessionRange,
        now: Optional[datetime] = None,
    ) -> BreakoutSignal:
        if range_data is None:
            return BreakoutSignal(
                triggered=False, direction=None, entry_price=None,
                stop_loss=None, take_profit_1=None, take_profit_2=None,
                confidence=0.0, reason="No range data available", range_data=None,
            )

        if not self._has_sufficient_volatility(range_data):
            return BreakoutSignal(
                triggered=False, direction=None, entry_price=None,
                stop_loss=None, take_profit_1=None, take_profit_2=None,
                confidence=0.0, reason=f"ATR percentile {range_data.atr_percentile:.1f}% below threshold {self.min_atr_percentile:.1f}%",
                range_data=range_data,
            )

        direction: Optional[str] = None
        if current_price > range_data.high:
            direction = "LONG"
        elif current_price < range_data.low:
            direction = "SHORT"

        if direction is None:
            return BreakoutSignal(
                triggered=False, direction=None, entry_price=None,
                stop_loss=None, take_profit_1=None, take_profit_2=None,
                confidence=0.0, reason="Price within Asian range, no breakout",
                range_data=range_data,
            )

        exit_price = current_price
        sl = self._get_stop_loss(exit_price, direction, range_data)
        tp1, tp2 = self._get_targets(exit_price, sl, direction, range_data)

        risk = abs(exit_price - sl)
        potential_rr = (abs(tp1 - exit_price) / risk) if risk > 0 else 0
        confidence = self._calculate_confidence(range_data, direction)

        return BreakoutSignal(
            triggered=True,
            direction=direction,
            entry_price=exit_price,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            confidence=confidence,
            reason=f"{direction} breakout at {exit_price:.2f} (range: {range_data.low:.1f}-{range_data.high:.1f})",
            range_data=range_data,
        )

    def _has_sufficient_volatility(self, range_data: AsianSessionRange) -> bool:
        return range_data.atr_percentile >= self.min_atr_percentile

    def _get_stop_loss(
        self, entry: float, direction: str, range_data: AsianSessionRange
    ) -> float:
        atr = range_data.atr if range_data.atr > 0 else entry * 0.005
        mult = self.atr_sl_multiplier
        if direction == "LONG":
            sl_atr = entry - (atr * mult)
            sl_range = range_data.low - (range_data.range_size * 0.1)
            return min(sl_atr, sl_range)
        else:
            sl_atr = entry + (atr * mult)
            sl_range = range_data.high + (range_data.range_size * 0.1)
            return max(sl_atr, sl_range)

    def _get_targets(
        self, entry: float, sl: float, direction: str, range_data: AsianSessionRange
    ) -> tuple[float, float]:
        risk = abs(entry - sl)
        if direction == "LONG":
            tp1 = entry + (risk * self.rr_target_1)
            tp2 = entry + (risk * self.rr_target_2)
        else:
            tp1 = entry - (risk * self.rr_target_1)
            tp2 = entry - (risk * self.rr_target_2)
        max_ext = range_data.range_size * 2
        if direction == "LONG":
            tp2 = min(tp2, entry + max_ext)
        else:
            tp2 = max(tp2, entry - max_ext)
        return float(tp1), float(tp2)

    def _calculate_confidence(
        self, range_data: AsianSessionRange, direction: str
    ) -> float:
        base = 0.5
        atr_bonus = min(range_data.atr_percentile / 100.0, 1.0) * 0.3
        range_bonus = min(range_data.range_size_pct / 5.0, 1.0) * 0.1
        volume_bonus = min(range_data.volume / 500000, 1.0) * 0.1
        return round(min(base + atr_bonus + range_bonus + volume_bonus, 1.0), 2)

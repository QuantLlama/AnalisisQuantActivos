from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional

import pandas as pd

from core.order_builder import OrderSpec
from core.order_executor import order_executor

from strategies.asian_session.range_calculator import (
    AsianSessionRangeCalculator,
    AsianSessionRange,
)
from strategies.asian_session.trade_guard import DailyTradeGuard, TradeGuardState
from strategies.asian_session.news_filter import NewsFilter
from strategies.asian_session.breakout_logic import BreakoutLogic, BreakoutSignal


class AsianBreakoutStrategy:
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict or {}

        self.range_calculator = AsianSessionRangeCalculator(self.config)
        self.trade_guard = DailyTradeGuard(self.config)
        self.news_filter = NewsFilter(config_dict=self.config)
        self.breakout_logic = BreakoutLogic(self.config)

        self.entry_window_start = time(7, 30)
        self.entry_window_end = time(9, 30)
        self.symbols: list[str] = self.config.get("symbols", ["MES=F", "MNQ=F"])
        self.last_signal: Optional[BreakoutSignal] = None
        self.last_range: Optional[AsianSessionRange] = None
        self._session_bars: Optional[pd.DataFrame] = None

    def process_bars(self, df: pd.DataFrame) -> None:
        if df is None or df.empty:
            return

        now = datetime.now(timezone.utc)
        if not self._is_entry_window(now):
            return

        if self.trade_guard.can_enter_trade(now) is False:
            return

        news_status = self.news_filter.is_blocked(now, symbols=self.symbols)
        if news_status.blocked:
            return

        self._session_bars = df.copy()
        range_data = self.range_calculator.calculate(df)
        if range_data is None:
            return

        self.last_range = range_data
        current_price = float(df["Close"].iloc[-1])
        signal = self.breakout_logic.evaluate(current_price, range_data, now)
        self.last_signal = signal

    def can_enter_now(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        now = now or datetime.now(timezone.utc)

        if not self._is_entry_window(now):
            return False, "Outside entry window (07:30-09:30 UTC)"

        if self.trade_guard.can_enter_trade(now) is False:
            status = self.trade_guard.get_status(now)
            if status.state == TradeGuardState.COOLDOWN:
                return False, f"Cooldown active ({status.cooldown_remaining:.0f}s remaining)"
            return False, f"Max trades reached ({status.trades_today}/{status.max_trades})"

        news_status = self.news_filter.is_blocked(now, symbols=self.symbols)
        if news_status.blocked:
            names = [e.title for e in news_status.blocking_events]
            return False, f"News block active: {', '.join(names)}"

        if self.last_signal is None or not self.last_signal.triggered:
            return False, "No active breakout signal"

        return True, self.last_signal.reason

    def execute_signal(
        self,
        symbol: str,
        broker: str = "mt5",
        now: Optional[datetime] = None,
    ) -> dict:
        now = now or datetime.now(timezone.utc)

        can_trade, reason = self.can_enter_now(now)
        if not can_trade:
            return {"ok": False, "error": reason}

        signal = self.last_signal
        if signal is None or not signal.triggered:
            return {"ok": False, "error": "No active breakout signal"}

        order_side = "BUY" if signal.direction == "LONG" else "SELL"

        try:
            spec = OrderSpec(
                symbol=symbol,
                side=order_side,
                order_type="MARKET",
                entry_price=signal.entry_price,
                sl=signal.stop_loss,
                tp1=signal.take_profit_1,
                tp2=signal.take_profit_2,
                size_usd=self._calculate_size(signal),
                lots=None,
                source="asian_session_breakout",
                confidence=signal.confidence,
                rr=self._calculate_rr(signal),
                notes=f"Asian breakout: {signal.reason}",
            )
        except Exception as e:
            return {"ok": False, "error": f"Failed to build order: {e}"}

        result = order_executor.send(spec, broker=broker)
        if result.get("ok"):
            self.trade_guard.record_trade(now)

        return result

    def get_status(self, now: Optional[datetime] = None) -> dict:
        now = now or datetime.now(timezone.utc)
        guard_status = self.trade_guard.get_status(now)
        can_trade, reason = self.can_enter_now(now)
        news_status = self.news_filter.is_blocked(now, symbols=self.symbols)

        return {
            "in_entry_window": self._is_entry_window(now),
            "can_trade": can_trade,
            "reason": reason,
            "guard": {
                "state": guard_status.state.name,
                "trades_today": guard_status.trades_today,
                "max_trades": guard_status.max_trades,
                "cooldown_remaining": guard_status.cooldown_remaining,
            },
            "news_blocked": news_status.blocked,
            "last_signal": {
                "triggered": self.last_signal.triggered if self.last_signal else False,
                "direction": self.last_signal.direction if self.last_signal else None,
                "confidence": self.last_signal.confidence if self.last_signal else 0.0,
            } if self.last_signal else None,
        }

    def _is_entry_window(self, now: datetime) -> bool:
        t = now.time()
        return self.entry_window_start <= t <= self.entry_window_end

    def _calculate_size(self, signal: BreakoutSignal) -> float:
        return 1000.0

    def _calculate_rr(self, signal: BreakoutSignal) -> float:
        if signal.stop_loss is None or signal.take_profit_1 is None or signal.entry_price is None:
            return 0.0
        risk = abs(signal.entry_price - signal.stop_loss)
        reward = abs(signal.take_profit_1 - signal.entry_price)
        return round(reward / risk, 2) if risk > 0 else 0.0

    def reset(self) -> None:
        self.trade_guard.reset()
        self.news_filter.clear_cache()
        self.last_signal = None
        self.last_range = None
        self._session_bars = None

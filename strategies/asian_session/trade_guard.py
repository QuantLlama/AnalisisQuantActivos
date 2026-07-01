from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum, auto
from typing import Optional


class TradeGuardState(Enum):
    IDLE = auto()
    COOLDOWN = auto()
    BLOCKED = auto()


@dataclass
class TradeGuardStatus:
    state: TradeGuardState
    trades_today: int
    max_trades: int
    cooldown_remaining: float
    blocked_until: Optional[datetime]
    can_trade: bool


class DailyTradeGuard:
    def __init__(self, config_dict: Optional[dict] = None):
        self.config = config_dict or {}
        self.max_trades_per_day: int = self.config.get("max_trades_per_day", 2)
        self.cooldown_minutes: int = self.config.get("cooldown_minutes", 30)

        self.trades_today: int = 0
        self._current_session_date: Optional[datetime] = None
        self._state: TradeGuardState = TradeGuardState.IDLE
        self._state_until: Optional[datetime] = None
        self._last_trade_time: Optional[datetime] = None

    def _reset_if_new_day(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self._current_session_date is None:
            self._current_session_date = today_start
            return

        if self._current_session_date < today_start:
            self.trades_today = 0
            self._current_session_date = today_start
            self._state = TradeGuardState.IDLE
            self._state_until = None
            self._last_trade_time = None

    def can_enter_trade(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        self._reset_if_new_day(now)

        if self.trades_today >= self.max_trades_per_day:
            return False

        if self._state == TradeGuardState.COOLDOWN:
            if self._state_until and now >= self._state_until:
                self._state = TradeGuardState.IDLE
                self._state_until = None
                return True
            return False

        if self._state == TradeGuardState.BLOCKED:
            if self._state_until and now >= self._state_until:
                self._state = TradeGuardState.IDLE
                self._state_until = None
                return True
            return False

        return True

    def record_trade(self, now: Optional[datetime] = None) -> None:
        now = now or datetime.now(timezone.utc)
        self._reset_if_new_day(now)

        self.trades_today += 1
        self._last_trade_time = now

        if self.trades_today >= self.max_trades_per_day:
            self._state = TradeGuardState.BLOCKED
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            self._state_until = tomorrow
        else:
            self._state = TradeGuardState.COOLDOWN
            self._state_until = now + timedelta(minutes=self.cooldown_minutes)

    def block_until(self, until: datetime) -> None:
        self._state = TradeGuardState.BLOCKED
        self._state_until = until

    def get_status(self, now: Optional[datetime] = None) -> TradeGuardStatus:
        now = now or datetime.now(timezone.utc)
        self._reset_if_new_day(now)

        cooldown_remaining = 0.0
        if self._state == TradeGuardState.COOLDOWN and self._state_until:
            remaining = (self._state_until - now).total_seconds()
            cooldown_remaining = max(0.0, remaining)

        blocked_until = self._state_until if self._state == TradeGuardState.BLOCKED else None

        return TradeGuardStatus(
            state=self._state,
            trades_today=self.trades_today,
            max_trades=self.max_trades_per_day,
            cooldown_remaining=cooldown_remaining,
            blocked_until=blocked_until,
            can_trade=self.can_enter_trade(now),
        )

    def reset(self) -> None:
        self.trades_today = 0
        self._current_session_date = None
        self._state = TradeGuardState.IDLE
        self._state_until = None
        self._last_trade_time = None

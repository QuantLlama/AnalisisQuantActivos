import pytest
from datetime import datetime, timedelta, timezone

from strategies.asian_session.trade_guard import (
    DailyTradeGuard,
    TradeGuardState,
    TradeGuardStatus,
)


def _utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


class TestDailyTradeGuard:
    def test_initial_state_allows_trade(self):
        guard = DailyTradeGuard()
        assert guard.can_enter_trade() is True

    def test_initial_status(self):
        guard = DailyTradeGuard()
        status = guard.get_status()
        assert status.state == TradeGuardState.IDLE
        assert status.trades_today == 0
        assert status.max_trades == 2
        assert status.can_trade is True

    def test_record_trade_increments_counter(self):
        guard = DailyTradeGuard()
        guard.record_trade(_utc(2024, 1, 1, 1))
        assert guard.trades_today == 1

    def test_after_one_trade_cooldown_active(self):
        guard = DailyTradeGuard({"cooldown_minutes": 30})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)
        assert guard.can_enter_trade(now + timedelta(minutes=1)) is False
        assert guard.can_enter_trade(now + timedelta(minutes=29)) is False

    def test_cooldown_expires(self):
        guard = DailyTradeGuard({"cooldown_minutes": 30})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)
        assert guard.can_enter_trade(now + timedelta(minutes=30)) is True

    def test_max_trades_blocks(self):
        guard = DailyTradeGuard({"max_trades_per_day": 1})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)
        assert guard.can_enter_trade(now + timedelta(hours=2)) is False

    def test_new_day_resets_counter(self):
        guard = DailyTradeGuard({"max_trades_per_day": 1})
        day1 = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(day1)
        assert guard.can_enter_trade(day1) is False

        day2 = _utc(2024, 1, 2, 1, 0)
        assert guard.can_enter_trade(day2) is True

    def test_two_trades_then_blocked(self):
        guard = DailyTradeGuard({"max_trades_per_day": 2})
        now = _utc(2024, 1, 1, 1, 0)

        guard.record_trade(now)
        assert guard.can_enter_trade(now + timedelta(minutes=31)) is True

        guard.record_trade(now + timedelta(minutes=31))
        assert guard.can_enter_trade(now + timedelta(hours=2)) is False

    def test_blocked_resets_next_day(self):
        guard = DailyTradeGuard({"max_trades_per_day": 2})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)
        guard.record_trade(now + timedelta(minutes=31))

        next_day = _utc(2024, 1, 2, 1, 0)
        assert guard.can_enter_trade(next_day) is True

    def test_block_until(self):
        guard = DailyTradeGuard()
        now = _utc(2024, 1, 1, 1, 0)
        guard.block_until(now + timedelta(hours=1))

        assert guard.can_enter_trade(now + timedelta(minutes=30)) is False
        assert guard.can_enter_trade(now + timedelta(hours=1)) is True

    def test_cooldown_remaining_in_status(self):
        guard = DailyTradeGuard({"cooldown_minutes": 30})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)

        status = guard.get_status(now + timedelta(minutes=10))
        assert status.cooldown_remaining == pytest.approx(20 * 60, rel=1)

    def test_status_blocked_until(self):
        guard = DailyTradeGuard({"max_trades_per_day": 1})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)

        status = guard.get_status(now)
        assert status.state == TradeGuardState.BLOCKED
        assert status.blocked_until is not None

    def test_reset(self):
        guard = DailyTradeGuard()
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)
        guard.reset()

        assert guard.trades_today == 0
        assert guard._state == TradeGuardState.IDLE
        assert guard.can_enter_trade() is True

    def test_default_config_values(self):
        guard = DailyTradeGuard()
        assert guard.max_trades_per_day == 2
        assert guard.cooldown_minutes == 30

    def test_custom_config(self):
        guard = DailyTradeGuard({"max_trades_per_day": 3, "cooldown_minutes": 15})
        assert guard.max_trades_per_day == 3
        assert guard.cooldown_minutes == 15

    def test_no_state_bleed_across_days(self):
        guard = DailyTradeGuard({"max_trades_per_day": 2})
        now = _utc(2024, 1, 1, 23, 0)
        guard.record_trade(now)
        guard.record_trade(now + timedelta(minutes=31))

        next_day = _utc(2024, 1, 2, 0, 5)
        assert guard.can_enter_trade(next_day) is True
        assert guard.trades_today == 0

    def test_get_status_after_max_trades(self):
        guard = DailyTradeGuard({"max_trades_per_day": 1})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)

        status = guard.get_status(now)
        assert status.can_trade is False
        assert status.trades_today == 1

    def test_get_status_during_cooldown(self):
        guard = DailyTradeGuard({"cooldown_minutes": 30})
        now = _utc(2024, 1, 1, 1, 0)
        guard.record_trade(now)

        status = guard.get_status(now + timedelta(minutes=5))
        assert status.state == TradeGuardState.COOLDOWN
        assert status.can_trade is False

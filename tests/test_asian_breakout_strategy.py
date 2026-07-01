import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from strategies.asian_session.asian_breakout_strategy import AsianBreakoutStrategy
from strategies.asian_session.range_calculator import AsianSessionRange


def _utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


SAMPLE_RANGE = AsianSessionRange(
    session_date=type("T", (), {"tz": None})(),
    high=4505.0, low=4495.0, mid=4500.0, vwap=4500.0,
    poc=4500.0, vah=4503.0, val=4497.0,
    range_size=10.0, range_size_pct=0.22, atr=12.0, atr_percentile=75.0,
    volume=250000, bar_count=96,
)


class TestAsianBreakoutStrategy:
    def test_initialization(self):
        strat = AsianBreakoutStrategy()
        assert strat.trade_guard is not None
        assert strat.news_filter is not None
        assert strat.breakout_logic is not None
        assert strat.range_calculator is not None

    def test_entry_window_morning(self):
        strat = AsianBreakoutStrategy()
        in_window = _utc(2024, 1, 1, 8, 0)
        assert strat._is_entry_window(in_window) is True

    def test_entry_window_outside(self):
        strat = AsianBreakoutStrategy()
        early = _utc(2024, 1, 1, 6, 0)
        late = _utc(2024, 1, 1, 10, 0)
        assert strat._is_entry_window(early) is False
        assert strat._is_entry_window(late) is False

    def test_entry_window_boundaries(self):
        strat = AsianBreakoutStrategy()
        start = _utc(2024, 1, 1, 7, 30)
        end = _utc(2024, 1, 1, 9, 30)
        assert strat._is_entry_window(start) is True
        assert strat._is_entry_window(end) is True

    def test_can_enter_outside_window(self):
        strat = AsianBreakoutStrategy()
        result, reason = strat.can_enter_now(_utc(2024, 1, 1, 10, 0))
        assert result is False
        assert "Outside entry window" in reason

    def test_can_enter_false_when_no_signal(self):
        strat = AsianBreakoutStrategy()
        result, reason = strat.can_enter_now(_utc(2024, 1, 1, 8, 0))
        assert result is False
        assert "No active breakout signal" in reason

    def test_process_bars_outside_window_ignored(self):
        strat = AsianBreakoutStrategy()
        df = MagicMock()
        strat.process_bars(df)
        assert strat.last_signal is None

    def test_process_bars_within_window_sets_signal(self):
        strat = AsianBreakoutStrategy({"min_atr_percentile": 40})
        now = _utc(2024, 1, 1, 8, 0)

        import pandas as pd
        import numpy as np
        dates = pd.date_range("2024-01-01 00:00", periods=96, freq="5min", tz="UTC")
        base = 4500.0
        prices = np.full(96, base)
        prices[-1] = 4600.0
        df = pd.DataFrame({
            "Open": prices,
            "High": prices - 1.0,
            "Low": prices - 3.0,
            "Close": prices,
            "Volume": [1000] * 96,
        }, index=dates)

        with patch("strategies.asian_session.asian_breakout_strategy.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            strat.process_bars(df)

        assert strat.last_signal is not None
        assert strat.last_signal.triggered is True

    def test_execute_signal_outside_window(self):
        strat = AsianBreakoutStrategy()
        result = strat.execute_signal("MES=F", broker="mt5", now=_utc(2024, 1, 1, 10, 0))
        assert result.get("ok") is False

    def test_execute_signal_no_signal(self):
        strat = AsianBreakoutStrategy()
        result = strat.execute_signal("MES=F", broker="mt5", now=_utc(2024, 1, 1, 8, 0))
        assert result.get("ok") is False

    @patch("strategies.asian_session.asian_breakout_strategy.order_executor")
    def test_execute_signal_full_flow(self, mock_executor):
        mock_executor.send.return_value = {"ok": True, "order_id": "abc123"}
        strat = AsianBreakoutStrategy({"min_atr_percentile": 40})
        now = _utc(2024, 1, 1, 8, 0)

        import pandas as pd
        import numpy as np
        dates = pd.date_range("2024-01-01 00:00", periods=96, freq="5min", tz="UTC")
        base = 4500.0
        prices = np.full(96, base)
        prices[-1] = 4600.0
        df = pd.DataFrame({
            "Open": prices,
            "High": prices - 1.0,
            "Low": prices - 3.0,
            "Close": prices,
            "Volume": [1000] * 96,
        }, index=dates)

        with patch("strategies.asian_session.asian_breakout_strategy.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            strat.process_bars(df)

        self.assert_signal_is_valid(strat)

        result = strat.execute_signal("MES=F", broker="mt5", now=now)
        assert result.get("ok") is True
        assert result.get("order_id") == "abc123"
        assert strat.trade_guard.trades_today == 1

    def assert_signal_is_valid(self, strat):
        assert strat.last_signal is not None
        assert strat.last_signal.triggered is True

    def test_get_status(self):
        strat = AsianBreakoutStrategy()
        status = strat.get_status(_utc(2024, 1, 1, 8, 0))
        assert "in_entry_window" in status
        assert "can_trade" in status
        assert "guard" in status
        assert "news_blocked" in status
        assert status["in_entry_window"] is True

    def test_get_status_outside_window(self):
        strat = AsianBreakoutStrategy()
        status = strat.get_status(_utc(2024, 1, 1, 10, 0))
        assert status["in_entry_window"] is False
        assert status["can_trade"] is False

    def test_reset_clears_state(self):
        strat = AsianBreakoutStrategy()
        strat.last_signal = MagicMock()
        strat.last_range = SAMPLE_RANGE
        strat._session_bars = MagicMock()
        strat.trade_guard.record_trade(_utc(2024, 1, 1, 8, 0))

        strat.reset()
        assert strat.last_signal is None
        assert strat.last_range is None
        assert strat._session_bars is None
        assert strat.trade_guard.trades_today == 0

    def test_default_symbols(self):
        strat = AsianBreakoutStrategy()
        assert "MES=F" in strat.symbols
        assert "MNQ=F" in strat.symbols

    def test_custom_symbols(self):
        strat = AsianBreakoutStrategy({"symbols": ["ES=F"]})
        assert strat.symbols == ["ES=F"]

    def test_calculate_rr_long(self):
        from strategies.asian_session.breakout_logic import BreakoutSignal
        signal = BreakoutSignal(
            triggered=True, direction="LONG", entry_price=4510.0,
            stop_loss=4500.0, take_profit_1=4530.0, take_profit_2=4540.0,
            confidence=0.8, reason="test", range_data=SAMPLE_RANGE,
        )
        strat = AsianBreakoutStrategy()
        rr = strat._calculate_rr(signal)
        assert rr == 2.0  # rr_target_1 = 2.0

    def test_calculate_rr_zero_on_no_risk(self):
        from strategies.asian_session.breakout_logic import BreakoutSignal
        signal = BreakoutSignal(
            triggered=True, direction="LONG", entry_price=4510.0,
            stop_loss=4510.0, take_profit_1=4530.0, take_profit_2=4540.0,
            confidence=0.8, reason="test", range_data=SAMPLE_RANGE,
        )
        strat = AsianBreakoutStrategy()
        rr = strat._calculate_rr(signal)
        assert rr == 0.0

    def test_news_block_prevents_entry(self):
        from strategies.asian_session.news_filter import NewsEvent, NewsProvider
        class FakeNewsProv(NewsProvider):
            def get_high_impact_events(self, from_dt, to_dt):
                return [NewsEvent(_utc(2024, 1, 1, 8, 0), "USD", "HIGH", "FOMC")]
        strat = AsianBreakoutStrategy()
        strat.news_filter.provider = FakeNewsProv()
        result, reason = strat.can_enter_now(_utc(2024, 1, 1, 8, 0))
        assert result is False
        assert "News block" in reason

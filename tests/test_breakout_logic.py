import pytest
from datetime import datetime, timezone

from strategies.asian_session.breakout_logic import BreakoutLogic, BreakoutSignal
from strategies.asian_session.range_calculator import AsianSessionRange
from tests.test_asian_session_range import _asian_5m_bars

SAMPLE_RANGE = AsianSessionRange(
    session_date=type("T", (), {"tz": None})(),
    high=4505.0, low=4495.0, mid=4500.0, vwap=4500.0,
    poc=4500.0, vah=4503.0, val=4497.0,
    range_size=10.0, range_size_pct=0.22, atr=12.0, atr_percentile=75.0,
    volume=250000, bar_count=96,
)

TIGHT_RANGE = AsianSessionRange(
    session_date=type("T", (), {"tz": None})(),
    high=4505.0, low=4495.0, mid=4500.0, vwap=4500.0,
    poc=4500.0, vah=4503.0, val=4497.0,
    range_size=10.0, range_size_pct=0.05, atr=12.0, atr_percentile=75.0,
    volume=250000, bar_count=96,
)

LOW_VOL_RANGE = AsianSessionRange(
    session_date=type("T", (), {"tz": None})(),
    high=4505.0, low=4495.0, mid=4500.0, vwap=4500.0,
    poc=4500.0, vah=4503.0, val=4497.0,
    range_size=10.0, range_size_pct=0.22, atr=12.0, atr_percentile=30.0,
    volume=250000, bar_count=96,
)

NO_RANGE = None


class TestBreakoutLogic:
    def test_long_breakout_triggers(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        assert signal.triggered is True
        assert signal.direction == "LONG"
        assert signal.entry_price == 4510.0

    def test_short_breakout_triggers(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4490.0, SAMPLE_RANGE)
        assert signal.triggered is True
        assert signal.direction == "SHORT"
        assert signal.entry_price == 4490.0

    def test_no_breakout_within_range(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4500.0, SAMPLE_RANGE)
        assert signal.triggered is False
        assert signal.direction is None
        assert "within Asian range" in signal.reason

    def test_no_range_data(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4500.0, None)
        assert signal.triggered is False
        assert signal.direction is None
        assert "No range data" in signal.reason

    def test_low_volatility_blocks_breakout(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, LOW_VOL_RANGE)
        assert signal.triggered is False
        assert "below threshold" in signal.reason

    def test_configured_min_atr_percentile(self):
        logic = BreakoutLogic({"min_atr_percentile": 20})
        signal = logic.evaluate(4510.0, LOW_VOL_RANGE)
        assert signal.triggered is True

    def test_stop_loss_long_below_entry(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        assert signal.stop_loss < signal.entry_price

    def test_stop_loss_short_above_entry(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4490.0, SAMPLE_RANGE)
        assert signal.stop_loss > signal.entry_price

    def test_take_profits_long(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        risk = abs(signal.entry_price - signal.stop_loss)
        assert signal.take_profit_1 == pytest.approx(signal.entry_price + risk * 2.0)
        assert signal.take_profit_2 <= signal.entry_price + risk * 3.0

    def test_take_profits_short(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4490.0, SAMPLE_RANGE)
        risk = abs(signal.entry_price - signal.stop_loss)
        assert signal.take_profit_1 == pytest.approx(signal.entry_price - risk * 2.0)
        assert signal.take_profit_2 >= signal.entry_price - risk * 3.0

    def test_tp2_at_least_tp1(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4506.0, SAMPLE_RANGE)
        assert signal.take_profit_2 >= signal.take_profit_1
        assert signal.take_profit_2 > signal.entry_price

    def test_confidence_between_0_and_1(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        assert 0.0 <= signal.confidence <= 1.0

    def test_confidence_higher_with_good_volatility(self):
        logic = BreakoutLogic()
        high_vol = AsianSessionRange(
            session_date=SAMPLE_RANGE.session_date,
            high=4510.0, low=4490.0, mid=4500.0, vwap=4500.0,
            poc=4500.0, vah=4505.0, val=4495.0,
            range_size=20.0, range_size_pct=0.44, atr=15.0, atr_percentile=95.0,
            volume=500000, bar_count=96,
        )
        signal_high = logic.evaluate(4515.0, high_vol)
        signal_low = logic.evaluate(4510.0, SAMPLE_RANGE)
        assert signal_high.confidence > signal_low.confidence

    def test_range_data_in_signal(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        assert signal.range_data is SAMPLE_RANGE

    def test_no_range_in_signal_when_none(self):
        logic = BreakoutLogic()
        signal = logic.evaluate(4510.0, None)
        assert signal.range_data is None

    def test_custom_rr_targets(self):
        logic = BreakoutLogic({"rr_target_1": 1.5, "rr_target_2": 2.5})
        signal = logic.evaluate(4510.0, SAMPLE_RANGE)
        risk = abs(signal.entry_price - signal.stop_loss)
        assert signal.take_profit_1 == pytest.approx(signal.entry_price + risk * 1.5)

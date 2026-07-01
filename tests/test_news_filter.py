import pytest
from datetime import datetime, timedelta, timezone

from strategies.asian_session.news_filter import (
    NewsFilter,
    NewsEvent,
    NewsProvider,
    StaticNewsProvider,
    NewsBlockStatus,
)


def _utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=timezone.utc)


class TestNewsEvent:
    def test_high_impact_detection(self):
        high = NewsEvent(_utc(2024, 1, 1), "USD", "HIGH", "NFP")
        low = NewsEvent(_utc(2024, 1, 1), "USD", "LOW", "Some Data")
        assert high.is_high_impact is True
        assert low.is_high_impact is False

    def test_case_insensitive_high_impact(self):
        event = NewsEvent(_utc(2024, 1, 1), "USD", "high", "test")
        assert event.is_high_impact is True


class FakeNewsProvider(NewsProvider):
    def __init__(self, events: list[NewsEvent]):
        self.events = events

    def get_high_impact_events(self, from_dt, to_dt):
        return [
            e for e in self.events
            if from_dt <= e.datetime_utc <= to_dt and e.is_high_impact
        ]


class TestStaticNewsProvider:
    def test_empty_provider_returns_no_events(self):
        provider = StaticNewsProvider()
        events = provider.get_high_impact_events(
            _utc(2024, 1, 1), _utc(2024, 1, 2)
        )
        assert events == []

    def test_custom_events_are_returned(self):
        event = NewsEvent(_utc(2024, 1, 1, 12), "USD", "HIGH", "FOMC")
        provider = StaticNewsProvider([event])
        events = provider.get_high_impact_events(
            _utc(2024, 1, 1), _utc(2024, 1, 2)
        )
        assert len(events) == 1
        assert events[0].title == "FOMC"

    def test_only_high_impact_returned(self):
        high = NewsEvent(_utc(2024, 1, 1, 12), "USD", "HIGH", "NFP")
        low = NewsEvent(_utc(2024, 1, 1, 12), "USD", "LOW", "Trivia")
        provider = StaticNewsProvider([high, low])
        events = provider.get_high_impact_events(
            _utc(2024, 1, 1), _utc(2024, 1, 2)
        )
        assert len(events) == 1
        assert events[0].title == "NFP"

    def test_outside_time_range_filtered(self):
        event = NewsEvent(_utc(2024, 1, 3), "USD", "HIGH", "CPI")
        provider = StaticNewsProvider([event])
        events = provider.get_high_impact_events(
            _utc(2024, 1, 1), _utc(2024, 1, 2)
        )
        assert events == []


class TestNewsFilter:
    def test_no_events_nothing_blocked(self):
        provider = FakeNewsProvider([])
        nf = NewsFilter(provider)
        result = nf.is_blocked(_utc(2024, 1, 1, 12))
        assert result.blocked is False
        assert result.blocking_events == []

    def test_high_impact_event_within_window_blocks(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "FOMC")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 45))
        assert result.blocked is True
        assert len(result.blocking_events) == 1

    def test_outside_window_not_blocked(self):
        event = NewsEvent(_utc(2024, 1, 1, 14, 0), "USD", "HIGH", "FOMC")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider, {"news_block_minutes": 10})
        result = nf.is_blocked(_utc(2024, 1, 1, 12, 0))
        assert result.blocked is False

    def test_window_before_event_blocks(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "NFP")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider, {"news_block_minutes": 15})
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 50))
        assert result.blocked is True

    def test_window_after_event_blocks(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "NFP")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider, {"news_block_minutes": 15})
        result = nf.is_blocked(_utc(2024, 1, 1, 12, 10))
        assert result.blocked is True

    def test_nearest_event_returned(self):
        fomc = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "FOMC")
        nfp = NewsEvent(_utc(2024, 1, 1, 13, 30), "USD", "HIGH", "NFP")
        provider = FakeNewsProvider([fomc, nfp])
        nf = NewsFilter(provider, {"news_block_minutes": 60})
        result = nf.is_blocked(_utc(2024, 1, 1, 12, 15))
        assert result.nearest_event is not None
        assert result.nearest_event.title == "FOMC"

    def test_low_impact_events_do_not_block(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "LOW", "Trivia")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 55))
        assert result.blocked is False

    def test_symbol_filter_usd(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "NFP")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 55), symbols=["MES"])
        assert result.blocked is True

    def test_symbol_filter_eur_only(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "EUR", "HIGH", "ECB")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 55), symbols=["MES"])
        assert result.blocked is False

    def test_symbols_to_currencies_mapping(self):
        assert NewsFilter._symbols_to_currencies(["MES"]) == {"USD"}
        assert NewsFilter._symbols_to_currencies(["EURUSD"]) == {"EUR"}
        assert NewsFilter._symbols_to_currencies(["CL"]) == {"USD"}

    def test_cache_returns_same_result(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "CPI")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        now = _utc(2024, 1, 1, 11, 55)
        result1 = nf.is_blocked(now)
        result2 = nf.is_blocked(now)
        assert result1 is result2

    def test_clear_cache(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "Non-Farm")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider)
        now = _utc(2024, 1, 1, 11, 55)
        result1 = nf.is_blocked(now)
        nf.clear_cache()
        result2 = nf.is_blocked(now)
        assert result1 is not result2

    def test_custom_block_minutes(self):
        event = NewsEvent(_utc(2024, 1, 1, 12, 0), "USD", "HIGH", "FOMC")
        provider = FakeNewsProvider([event])
        nf = NewsFilter(provider, {"news_block_minutes": 5})
        result = nf.is_blocked(_utc(2024, 1, 1, 11, 54))
        assert result.blocked is False  # 6 min before event, window is 5 min
        nf.clear_cache()
        result2 = nf.is_blocked(_utc(2024, 1, 1, 11, 56))
        assert result2.blocked is True  # 4 min before event, inside window

    def test_default_block_minutes(self):
        nf = NewsFilter()
        assert nf.block_minutes == 30

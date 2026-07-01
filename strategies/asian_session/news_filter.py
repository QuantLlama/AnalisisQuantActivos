from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass
class NewsEvent:
    datetime_utc: datetime
    currency: str
    impact: str  # "HIGH", "MEDIUM", "LOW"
    title: str
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None

    @property
    def is_high_impact(self) -> bool:
        return self.impact.upper() == "HIGH"


class NewsProvider:
    def get_high_impact_events(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[NewsEvent]:
        raise NotImplementedError


@dataclass
class NewsBlockStatus:
    blocked: bool
    blocking_events: list[NewsEvent]
    nearest_event: Optional[NewsEvent]
    block_window_minutes: int


class StaticNewsProvider(NewsProvider):
    """Provides news events from a static calendar list.
    
    Falls back to an internal list of known high-impact recurring events
    (FOMC, NFP, CPI, etc.) when no dynamic provider is configured.
    """

    DEFAULT_HIGH_IMPACT: list[tuple[str, str, str, int, int, int, int]] = [
        ("FOMC Rate Decision", "USD", "HIGH", 0, -5, 2, 14),
        ("Non-Farm Payrolls", "USD", "HIGH", 4, -5, 2, 7),
        ("CPI (YoY)", "USD", "HIGH", 5, -5, 2, 7),
        ("PPI (MoM)", "USD", "HIGH", 5, -5, 2, 7),
        ("GDP (QoQ)", "USD", "HIGH", 5, -5, 2, 7),
        ("Retail Sales (MoM)", "USD", "HIGH", 5, -5, 2, 7),
        ("Unemployment Rate", "USD", "HIGH", 4, -5, 2, 7),
        ("ISM Manufacturing PMI", "USD", "HIGH", 6, -5, 2, 7),
        ("ISM Services PMI", "USD", "HIGH", 6, -5, 2, 7),
        ("Industrial Production (MoM)", "USD", "HIGH", 6, -5, 2, 7),
        ("Consumer Confidence", "USD", "HIGH", 6, -5, 2, 7),
    ]

    def __init__(self, custom_events: Optional[list[NewsEvent]] = None):
        self._custom_events = custom_events or []

    def get_high_impact_events(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[NewsEvent]:
        matching: list[NewsEvent] = []

        for event in self._custom_events:
            if from_dt <= event.datetime_utc <= to_dt and event.is_high_impact:
                matching.append(event)

        return matching


class NewsFilter:
    def __init__(
        self,
        provider: Optional[NewsProvider] = None,
        config_dict: Optional[dict] = None,
    ):
        self.provider = provider or StaticNewsProvider()
        self.config = config_dict or {}
        self.block_minutes: int = self.config.get("news_block_minutes", 30)
        self._check_cache: Optional[tuple[datetime, datetime, NewsBlockStatus]] = None

    def is_blocked(
        self,
        now: Optional[datetime] = None,
        symbols: Optional[list[str]] = None,
    ) -> NewsBlockStatus:
        now = now or datetime.now(timezone.utc)

        if self._check_cache and self._check_cache[0] <= now <= self._check_cache[1]:
            return self._check_cache[2]

        window_start = now - timedelta(minutes=self.block_minutes)
        window_end = now + timedelta(minutes=self.block_minutes)

        events = self.provider.get_high_impact_events(window_start, window_end)

        if symbols:
            currencies = self._symbols_to_currencies(symbols)
            events = [e for e in events if e.currency in currencies]

        blocked = len(events) > 0
        nearest = min(events, key=lambda e: abs((e.datetime_utc - now).total_seconds())) if events else None

        result = NewsBlockStatus(
            blocked=blocked,
            blocking_events=events,
            nearest_event=nearest,
            block_window_minutes=self.block_minutes,
        )

        self._check_cache = (window_start, window_end, result)
        return result

    @staticmethod
    def _symbols_to_currencies(symbols: list[str]) -> set[str]:
        currency_map: dict[str, str] = {
            "MES": "USD",
            "MNQ": "USD",
            "ES": "USD",
            "NQ": "USD",
            "BTC-USDT": "USD",
            "EURUSD": "EUR",
            "GBPUSD": "GBP",
            "USDJPY": "JPY",
            "USDCAD": "CAD",
            "AUDUSD": "AUD",
            "XAUUSD": "USD",
            "GC": "USD",
            "CL": "USD",
        }
        return {currency_map.get(s.upper(), "USD") for s in symbols}

    def clear_cache(self) -> None:
        self._check_cache = None

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as np_pd
import pytest

from strategies.asian_session.run import main, load_strategy_config
from strategies.asian_session.asian_breakout_strategy import AsianBreakoutStrategy


class TestIntegrationAsianRun:
    def test_load_strategy_config_from_global(self):
        cfg = load_strategy_config()
        assert isinstance(cfg, dict)
        assert "symbols" in cfg
        assert "max_trades_per_day" in cfg

    @patch("strategies.asian_session.run.FloatPrompt")
    @patch("strategies.asian_session.run.Prompt")
    @patch("strategies.asian_session.run.order_executor")
    @patch("strategies.asian_session.run.DataProvider")
    def test_main_loop_handles_keyboard_interrupt(
        self, mock_provider_cls, mock_executor, mock_prompt, mock_float_prompt
    ):
        mock_prompt.ask.return_value = "MES=F"
        mock_float_prompt.ask.return_value = 1.0
        mock_executor.mode = "paper"

        df = np_pd.DataFrame()
        mock_provider = MagicMock()
        mock_provider.fetch.return_value = (df, {"error": "No data"})
        mock_provider_cls.return_value = mock_provider

        with patch(
            "strategies.asian_session.run.time.sleep",
            side_effect=KeyboardInterrupt,
        ):
            main()

        assert mock_provider.fetch.called
        assert mock_provider.fetch.call_count == 1

    def test_strategy_full_flow_with_mocks(self):
        strat = AsianBreakoutStrategy({"min_atr_percentile": 40})
        now = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)

        dates = np_pd.date_range(
            "2024-01-01 00:00", periods=96, freq="5min", tz="UTC"
        )
        base = 4500.0
        prices = np.full(96, base)
        prices[-1] = 4600.0

        df = np_pd.DataFrame(
            {
                "Open": prices,
                "High": prices - 1.0,
                "Low": prices - 3.0,
                "Close": prices,
                "Volume": [1000] * 96,
            },
            index=dates,
        )

        with patch(
            "strategies.asian_session.asian_breakout_strategy.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            strat.process_bars(df)

        assert strat.last_signal is not None
        assert strat.last_signal.triggered is True
        assert strat.last_signal.direction == "LONG"
        assert strat.last_signal.entry_price == 4600.0

        with patch(
            "strategies.asian_session.asian_breakout_strategy.order_executor"
        ) as mock_oe:
            mock_oe.send.return_value = {
                "ok": True,
                "order_id": "test-456",
            }
            result = strat.execute_signal("MES=F", broker="mt5", now=now)

        assert result.get("ok") is True
        assert strat.trade_guard.trades_today == 1

    def test_run_does_not_execute_outside_entry_window(self):
        strat = AsianBreakoutStrategy({"min_atr_percentile": 40})
        now = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

        dates = np_pd.date_range(
            "2024-01-01 00:00", periods=96, freq="5min", tz="UTC"
        )
        base = 4500.0
        prices = np.full(96, base)
        prices[-1] = 4600.0

        df = np_pd.DataFrame(
            {
                "Open": prices,
                "High": prices - 1.0,
                "Low": prices - 3.0,
                "Close": prices,
                "Volume": [1000] * 96,
            },
            index=dates,
        )

        with patch(
            "strategies.asian_session.asian_breakout_strategy.datetime"
        ) as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = datetime
            strat.process_bars(df)

        assert strat.last_signal is None

    def test_empty_data_does_not_crash(self):
        strat = AsianBreakoutStrategy()
        df = np_pd.DataFrame()
        strat.process_bars(df)
        assert strat.last_signal is None

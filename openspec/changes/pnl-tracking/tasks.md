# Tasks: PnL Tracking

## Delivery Strategy
`ask-on-risk`: Structured into distinct logical units that can be reviewed independently or as a chain of PRs.

## Phase 1: Order Executor Capabilities
**Goal:** Expose unified position and PnL fetching methods from MT5 and Binance.

- [x] Modify `core/order_executor.py`
  - Add `get_mt5_positions(self) -> list[dict]`
    - Import `MetaTrader5` dynamically.
    - Check initialization and call `mt5.positions_get()`.
    - Normalize output to dict `{"platform": "MT5", "symbol": pos.symbol, "size": pos.volume, "pnl": pos.profit}`.
    - Add exception handling to return `[]` on error.
  - Add `get_binance_positions(self) -> list[dict]`
    - Import Binance client dynamically.
    - Call `fetch_positions()` via CCXT.
    - Filter results (non-zero size, exclude spot).
    - Normalize output to dict `{"platform": "Binance Futures", "symbol": symbol, "size": size, "pnl": pnl}`.
    - Add exception handling to return `[]` on error.

## Phase 2: CLI UI Integration
**Goal:** Add the `order positions` subcommand and display a formatted Rich Table.

- [x] Modify `ui/shell.py`
  - Update `NestedCompleter` in `AnalysisShell.__init__` to include `"positions": None` under the `order` key.
  - Update `cmd_help` to document the `order positions` command.
  - Update `cmd_order` to handle `elif subcmd == "positions":`.
    - Call `order_executor.get_mt5_positions()` and `order_executor.get_binance_positions()`.
    - Create a `rich.table.Table` with columns: `Platform`, `Symbol`, `Size`, `PnL`.
    - Iterate over the unified position dictionaries, color-coding PnL (green for >0, red for <0).
    - Display aggregate PnL row.

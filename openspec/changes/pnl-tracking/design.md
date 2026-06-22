# Design: PnL Tracking

## Architecture & Responsibilities

The `pnl-tracking` feature spans across the UI layer and the execution core. It delegates exchange-specific API calls to the execution module while presenting the unified data cleanly in the UI.

### 1. UI Shell (`ui/shell.py`)
- **Autocomplete**: Add `"positions": None` to the `order` command dict in `NestedCompleter` within `AnalysisShell.__init__`.
- **Help Documentation**: Add a description for `order positions` in `cmd_help`.
- **Command Handling**: Add `elif subcmd == "positions":` in `cmd_order`.
  - Invoke `order_executor.get_mt5_positions()` and `order_executor.get_binance_positions()`.
  - Parse the arrays returned by both methods.
  - Filter out Binance Spot positions (ensure PnL calculations only include active derivatives or MT5 margin positions).
  - Create and populate a `rich.table.Table` with columns: `Platform`, `Symbol`, `Size`, `PnL`.
  - Format the output values: color-code PnL (green for positive, red for negative).
  - Calculate and display a total aggregate PnL.

### 2. Order Executor (`core/order_executor.py`)
Add two methods to unify the retrieval of positions across different brokers.

- `get_mt5_positions(self) -> list[dict]`:
  - Dynamically import the MT5 dependencies (e.g., `import MetaTrader5 as mt5`).
  - Check MT5 initialization status.
  - Call `mt5.positions_get()`. If none exist, return an empty list.
  - Extract and normalize data: `symbol`, `volume` (size), and `profit` (PnL).
  - Return a list of dicts: `{"platform": "MT5", "symbol": pos.symbol, "size": pos.volume, "pnl": pos.profit}`.

- `get_binance_positions(self) -> list[dict]`:
  - Dynamically import the binance client (e.g., from `core.binance_provider`).
  - Use the CCXT client or raw API wrapper to call `fetch_positions()`.
  - Filter the results:
    - Only include non-zero positions (where size > 0 or < 0).
    - Ensure Spot positions are excluded. This can be done by verifying the margin type or contract type.
  - Normalize data: extract `symbol`, `contracts`/`size`, and `unrealizedPnl`.
  - Return a list of dicts: `{"platform": "Binance Futures", "symbol": symbol, "size": size, "pnl": pnl}`.

## Data Normalization
To decouple the UI from broker-specific representations, `order_executor` will return standardized dictionaries:
```python
{
    "platform": str,   # e.g., "MT5" or "Binance Futures"
    "symbol": str,     # e.g., "BTCUSDT"
    "size": float,     # Position size
    "pnl": float       # Unrealized Profit and Loss
}
```

## Error Handling
- Wrap `fetch_positions()` and `positions_get()` calls in `try...except` blocks within `order_executor`. 
- If a connection fails or the exchange is unreachable, the method should catch the exception, log an error, and return an empty list `[]`. This ensures that if Binance is down, the user can still view MT5 positions.

## Dependencies
- `rich.table.Table` for presentation.
- Existing `ccxt` or raw Binance API wrappers.
- `MetaTrader5` python package.

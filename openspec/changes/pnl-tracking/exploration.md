# Exploration: PnL Tracking and Open Positions

## 1. Overview
The goal of this change is to add open position and live PnL tracking for Binance (Spot and Futures) and MT5 into the FLUX Quant system. Currently, the system can send orders via `core/order_executor.py`, `core/mt5_trader.py`, and `core/binance_trader.py`, but it lacks the capability to retrieve open positions and their unrealized profit and loss.

The `ui/shell.py` currently features an `order` namespace (`order send`, `order status`, `order history`, etc.). The most natural and user-friendly way to expose this feature is by adding an `order positions` (or `order position`) subcommand.

## 2. Binance Integration (`core/binance_trader.py`)
Binance has different endpoints and structures for Spot and Futures markets:
*   **Futures**: `ccxt` provides `exchange.fetch_positions()`. This endpoint returns active positions along with their `unrealizedPnl`, `entryPrice`, `contracts`, and `side`. This natively maps to our desired output.
*   **Spot**: Spot markets do not natively use "positions" in the same way (they just use wallet balances). We can query `exchange.fetch_balance()` to show held assets as positions, but calculating unrealized PnL requires tracking the average buy price locally, which is complex if trades were made outside the bot. It's best to prioritize Futures for the position table and leave Spot out of the PnL tracking scope for now.

**Proposed Implementation**:
*   Add `get_binance_positions(broker: str, paper: bool = True) -> list[dict]` to `core/binance_trader.py`.
*   Handle `paper=True` by returning dummy or cached paper positions.
*   For `live`, instantiate `exchange` using `_make_exchange(futures=True)`.
*   Call `exchange.fetch_positions()`, filter for positions with non-zero size, and map the output to a standard schema.

## 3. MT5 Integration (`core/mt5_trader.py`)
MetaTrader 5 natively supports positions and calculates PnL automatically.
*   The `MetaTrader5` python package provides `mt5.positions_get()`.
*   This returns a tuple of `TradePosition` namedtuples.
*   Key fields we can extract: `symbol`, `type` (0=Buy, 1=Sell), `volume`, `price_open`, `price_current`, `sl`, `tp`, and `profit` (Unrealized PnL).

**Proposed Implementation**:
*   Add `get_mt5_positions(paper: bool = True) -> list[dict]` to `core/mt5_trader.py`.
*   Return a standard schema matching the Binance implementation: `{'symbol': str, 'side': str, 'size': float, 'entry_price': float, 'current_price': float, 'pnl': float, 'broker': 'mt5'}`.

## 4. Order Executor (`core/order_executor.py`)
*   Add `get_positions(broker: str = None) -> list[dict]` inside `OrderExecutor`.
*   If `broker` is not specified, it can default to the active `config.get("trading.default_broker", "mt5")` or fetch from all configured brokers.
*   The executor routes the request to the respective function (`get_mt5_positions` or `get_binance_positions`).

## 5. UI / Shell (`ui/shell.py`)
*   Add `positions` to the `cmd_order` method in `ui/shell.py`.
*   Example usage: `order positions` or `order positions mt5` / `order positions binance_futures`.
*   Render a `Rich` Table with columns: `Símbolo`, `Lado` (colored green/red), `Tamaño`, `Precio Entrada`, `Precio Actual`, y `PnL` (colored green/red depending on profitability).
*   Add the total accumulated PnL at the bottom of the table.
*   Update the autocompletion dictionary (`self.completer`) to include `positions` under the `order` command.

## 6. Risks and Considerations
*   **Paper Trading State**: The current system simply returns mocked success messages for `paper=True` in orders but does not store virtual positions anywhere except history. Retrieving `paper` positions would either require a separate in-memory position tracker or just returning an empty list/warning that paper positions aren't fully simulated.
*   **CCXT Rate Limits**: Fetching positions in a loop can hit rate limits on Binance. `fetch_positions()` should be called on-demand only (when the user types the command) to avoid rate limits.
*   **Spot limitations**: The user might expect Spot PnL. We should be explicit if Spot PnL is not supported or if it simply returns asset balances.

## 7. Next Steps
Move to the `sdd-propose` phase to formalize the implementation plan, specifically standardizing the output schema for positions across brokers and deciding how to handle paper trading positions (e.g. simply return "Not implemented for paper mode" or build a mock position tracker).

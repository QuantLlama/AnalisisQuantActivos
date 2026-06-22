# Specification: PnL Tracking

## Overview
This capability adds position and PnL tracking for Binance Futures and MT5 directly from the CLI to give the user visibility into active open positions and their financial status without switching context.

## State Models
N/A

## Components

### `ui/shell.py`
The CLI UI will be extended with a `positions` subcommand under the `order` namespace.
This command will fetch position data from `order_executor` and display it in a formatted Rich Table.

### `order_executor`
Two new methods will be added to the `order_executor` to fetch position data:
1. `get_mt5_positions()`: Wraps MT5 `positions_get()` to fetch MT5 positions.
2. `get_binance_positions()`: Wraps Binance `fetch_positions()` to fetch Binance Futures positions.

The output from these methods will be normalized into a unified structure representing open positions (symbol, size, PnL, platform).
Binance Spot positions will be filtered out.

## Workflows
N/A

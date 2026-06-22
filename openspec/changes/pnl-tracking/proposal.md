# Proposal: PnL Tracking

## Intent

Add position and PnL tracking for Binance Futures and MT5 directly from the CLI to give the user visibility into active open positions and their financial status without switching context.

## Scope

### In Scope
- Add `positions` subcommand to `order` namespace in `ui/shell.py`.
- Add `get_mt5_positions()` in `order_executor` wrapping MT5 `positions_get()`.
- Add `get_binance_positions()` in `order_executor` wrapping Binance `fetch_positions()`.
- Filter out Spot Binance positions from PnL calculations.
- Display positions and PnL in a formatted Rich Table.

### Out of Scope
- Position modification or closing (read-only for now).
- Historical PnL reporting.
- Advanced metrics like unrealized funding fees (basic PnL only).

## Capabilities

### New Capabilities
- `pnl-tracking`: Tracks and displays active positions and PnL across Binance Futures and MT5.

### Modified Capabilities
- None

## Approach

Extend the CLI UI with a `positions` command. Wire it down to the `order_executor` which fetches from exchange adapters. For MT5, `positions_get()` provides position arrays. For Binance, `fetch_positions()` returns position arrays. Skip Spot wallets. Unify the output format and render a Rich Table to the terminal.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ui/shell.py` | Modified | Add `positions` command to `order` namespace |
| `order_executor` | Modified | Add MT5 and Binance position fetching logic |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Rate limiting from exchanges on `fetch_positions` | Low | Only fetch on explicit user request; no polling. |
| Inconsistent data types between MT5 and Binance | Med | Normalize output structs before returning to UI. |

## Rollback Plan

Revert the commits introducing the new `positions` command and corresponding `order_executor` methods, which isolates the feature.

## Dependencies

- Existing Binance and MT5 connection configurations.
- `rich` library for terminal tables.

## Success Criteria

- [ ] User can run `order positions` and see a table of open positions.
- [ ] Table displays PnL, sizes, and symbols for MT5 and Binance Futures.
- [ ] Spot positions are not included in PnL calculations.

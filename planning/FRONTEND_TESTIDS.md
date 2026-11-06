# Frontend data-testid reference

Header: `total-value`, `total-pnl`, `cash-balance`, `connection-dot` (attr `data-status`=connected|reconnecting|disconnected), `connection-label`, `chat-toggle`
Watchlist: `watchlist`, `watchlist-row-{T}`, `price-{T}` (attr `data-flash`=up|down|''), `change-{T}`, `remove-{T}`, `watchlist-input`, `watchlist-add`, `watchlist-error`, `sparkline`
Charts: `main-chart`, `main-chart-canvas`, `pnl-chart`, `pnl-chart-canvas` (attr `data-points`; absent until snapshots exist)
Heatmap: `heatmap`, `heatmap-cell-{T}` (attr `data-pnl`=profit|loss)
Positions: `positions`, `position-row-{T}`, `position-qty-{T}`, `positions-empty`
Trade bar: `trade-bar`, `trade-ticker`, `trade-quantity`, `buy-btn`, `sell-btn`, `trade-message`
Chat: `chat-panel`, `chat-messages`, `chat-input`, `chat-send`, `chat-message` (attr `data-role`), `chat-loading`, `chat-actions`, `chat-trade-action`, `chat-watchlist-action`

Notes: trade ticker field defaults to the selected watchlist ticker when left empty. Prices formatted with 2 decimals, no thousands separators concerns (toLocaleString: `1,234.50`).

# LLM Mock Mode (`LLM_MOCK=true`)

`app.llm.MockLLMClient` returns deterministic structured responses based only on the
**last user message** (case-insensitive, first matching rule wins). No network, no API key.

| Message contains | Result |
|---|---|
| `buy [QTY] [TICKER]` | trade buy, defaults QTY=1, TICKER=AAPL. e.g. "buy" -> buy 1 AAPL; "buy 5 tsla" -> buy 5 TSLA |
| `sell [QTY] [TICKER]` | trade sell, same defaults |
| `add TICKER` | watchlist add TICKER (uppercased) |
| `remove TICKER` | watchlist remove TICKER |
| anything else | plain analysis text, no actions |

Buy is checked before sell, then add, then remove. Trades go through normal validation
(e.g. sell with no position yields a failed action and an error appended to the message).

## Exact mock outputs (message text)
- `buy` -> `Buying {qty} {TICKER} at market.` (e.g. "buy" -> `Buying 1 AAPL at market.`; "buy 5 tsla" -> `Buying 5 TSLA at market.`)
- `sell` -> `Selling {qty} {TICKER} at market.`
- `add pypl` -> `Adding PYPL to your watchlist.`
- `remove nflx` -> `Removing NFLX from your watchlist.`
- default -> `Mock analysis: your portfolio looks reasonably diversified. Consider watching concentration risk in your largest positions.`

If an action fails (e.g. insufficient cash), the returned message gets appended:
`\n\nSome actions could not be completed:\n- buy 1 AAPL failed: <reason>` and the item has `status: "failed"`, `error: <reason>`.

## Chat response shape
Matches planning/API_CONTRACT.md: `{message, trades:[{ticker,side,quantity,price,status,error}], watchlist_changes:[{ticker,action,status,error}]}`.

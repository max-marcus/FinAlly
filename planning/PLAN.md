# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area. On load, that chart already shows the first watchlist ticker.
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio and get analysis. The assistant executes a trade only when the latest message names that buy or sell. It can also manage the watchlist through natural language.
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, amber = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
The palette uses the official USC Trojans colors, Cardinal and Gold, on the dark theme.

- Gold Primary: `#FFCC00` (USC Gold). Use for the logo, active tabs, focus rings, selected tickers, key numbers, and links.
- Cardinal Secondary: `#990000` (USC Cardinal). Use as a fill for submit buttons (Buy, Sell, Send) and brand accents. Hover state: `#B31B1B`.
- Text on Cardinal: white `#FFFFFF` or Gold `#FFCC00`.

Usage rules:
- Never use Cardinal for text or thin lines on the dark background. It has too little contrast (about 2.3:1). Use it only as a fill.
- Never use Cardinal or Gold for data meaning. Price flashes, P&L, and the heatmap use separate semantic colors:
  - Gain / uptick: `#3FB950` (green)
  - Loss / downtick: `#F85149` (bright red, clearly lighter than Cardinal)
- Use Gold sparingly as an accent. Large Gold areas make the dense layout hard to read.
- Connection status "reconnecting" uses amber `#D29922`, not Gold, so status stays separate from brand color.

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (bind-mounted from db/)        │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, bind-mounted from the project so the file stays on the host
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Bind-mount point (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Optional convenience wrapper
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend initializes the database on first request. It creates tables and seeds default data when the SQLite file is missing, empty, or has missing tables.
- **`db/`** at the top level is the runtime bind-mount point. The SQLite file (`db/finally.db`) is created here by the backend. The start scripts mount this directory at `/app/db`. The file remains on the host after the container stops, including after the image is rebuilt or Docker volumes are removed.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required for live chat. Not required when LLM_MOCK=true (tests and local mock runs).
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls the priced set: watchlist tickers plus positions with quantity greater than zero
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, timestamp, and a `baseline_price` for each ticker
- `previous_price` is the prior tick. The watchlist uses it only for the uptick and downtick flash
- `baseline_price` is the denominator for the watchlist change column. Set it in this order:
  1. Prior close. For Massive, use `day.previous_close` from the snapshot.
  2. The daily open, when the source provides it and prior close is missing.
  3. The first price cached for that ticker in the current server session. The simulator uses its seed price. Massive uses the first last-trade price.
- The simulator has no prior close and no daily open, so its baseline is the seed price
- The priced set is the union of watchlist tickers and positions with quantity greater than zero. Remove a ticker from the cache only when it is neither watched nor held. Reject a market order when the cache has no price for that ticker.
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- About every 500ms, when the cache version changes, the server sends one JSON object keyed by ticker. The keys are the priced set.
- Each value has `ticker`, `price`, `previous_price`, `timestamp` (Unix seconds), `change`, `change_percent`, and `direction` (`up`, `down`, or `flat`). `change` and `change_percent` are the move since the previous tick. `change_percent` is that ratio times 100, and it is 0 when `previous_price` is 0. Add `baseline_price` to this object. Shipped `PriceUpdate.to_dict()` does not include it yet.
- The watchlist daily change percent is `(price - baseline_price) / baseline_price * 100`. It is 0 when `baseline_price` is 0.
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on first request. If the file doesn't exist, is empty, or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- A new `db/finally.db` on the host bind mount starts with a clean, seeded database automatically

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — the `action_results` array for that assistant turn; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message. The response keeps the model message and adds `action_results` for each trade and watchlist change. |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Builds an `action_results` entry for each trade and watchlist change, then stores the model message and that array in `chat_messages`
8. Returns the model message plus `action_results` to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user. The backend keeps this text even when an order is rejected.
- `trades` (optional): Array of trades to auto-execute. Include an order only when the latest user message names that ticker and that side (`buy` or `sell`). Suggestions stay in `message`. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells).
- `watchlist_changes` (optional): Array of watchlist modifications

After execution, the HTTP response adds `action_results`. The model does not write this array. `chat_messages.actions` stores it. Each item has `kind` (`trade` or `watchlist`), `ticker`, `status` (`ok` or `error`), and `detail`. `detail` is the fill confirmation or the validation error.

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (for example, insufficient cash), the model message stays as written. The failed row appears under that message from `action_results`, with `status` `error` and the reason in `detail`. The backend does not call the model a second time.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning in `message` only. Do not copy a suggestion into `trades`.
- Put an order in `trades` only when the latest user message names that ticker and that side (`buy` or `sell`)
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change % from `baseline_price`, and a sparkline mini-chart (accumulated from SSE since page load). Include a ticker input, an Add button, and a remove control on each row. A duplicate ticker shows a message and does not add a second row. An empty list shows an empty-list message.
- **Main chart area** — larger chart for the selected ticker. On load, select the first watchlist ticker and plot that ticker's SSE prices since page load, the same series as its sparkline. Clicking a ticker in the watchlist replaces the selection. There is no ticker-history endpoint.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill. Insufficient cash, insufficient shares, a non-positive quantity, and a missing price leave holdings unchanged and show the error under the bar.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Show the model message, then one row per `action_results` item. `ok` rows are confirmations. `error` rows show `detail` under the message.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Use Lightweight Charts for the main chart, the sparklines, and the P&L line. It is canvas-based and built for streaming prices. Draw the heatmap as a treemap of positioned elements sized by market value. Lightweight Charts has no treemap.
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Host database file

The SQLite file stays on the host at `db/finally.db`. Bind-mount that directory. A named volume lives in Docker's store and is removed by volume cleanup or a Docker Desktop reset. The host file survives those, and it survives container removal and image rebuilds.

```bash
docker run -v "$(pwd)/db:/app/db" -p 127.0.0.1:8000:8000 --env-file .env finally
```

On Windows, the start script uses `-v "${PWD}/db:/app/db"`. The backend writes `finally.db` to `/app/db`. Publish `127.0.0.1:8000:8000` so the port is reachable only from the host. There is no login, and `POST /api/chat` spends `OPENROUTER_API_KEY`.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the `db/` bind mount, `127.0.0.1:8000:8000`, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does not delete `db/finally.db`

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Hosting

Public hosting is out of scope. Do not deploy this container to a public host. The local run binds port 8000 on `127.0.0.1` only.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Review notes (2026-10-20)

Questions 1–7 are answered below and copied into sections 2, 3, 4, 6, 7, 8, 9, 10, and 11. The priced set, the SSE object, the daily-change percent, database creation, the OpenRouter key rule, the watchlist controls, and the trade-bar errors are copied into those sections. The other clarifications, feedback, and simplifications below are not copied yet.

Market data in `backend/app/market/` is already built. Where this section cites the stream or the cache, it cites that code.

### Questions

1. **What does the watchlist change column measure?** Section 10 requires a daily change %. Each SSE event carries the latest price and the previous price. In the shipped cache, the previous price is the prior tick, and `change_percent` is the move since that tick. The simulator updates about every 500ms, so that figure stays near zero. Choose one baseline and name it in sections 6 and 10:
   - The first price cached for that ticker in the current server session (simulator seed price, or the first Massive last-trade price).
   - The prior close, which the archived Massive snapshot notes expose as `day.previous_close`. The shipped client does not store that field, and the simulator has no prior close.

   ANSWER: It should be the prior close (archived Massive snapshot notes expose as `day.previous_close`). If no prior close available, use the daily open price. And if that is not available use the first price cached for that ticker in the current server session (simulator seed price, or the first Massive last-trade price).

   Copied to sections 6 and 10 as `baseline_price`.

2. **What does the user see when a chat trade fails?** Section 9 says the error is included so the model can inform the user. Steps 4–8 call the model once, execute after that, and return the model's message. The response schema has `message`, `trades`, and `watchlist_changes`, and no error field. The model cannot describe a rejection it has not seen. Choose one:
   ANSWER: Keep the model message. Add an `action_results` array (kind, ticker, status, detail) and show failed rows under the message.

   Copied to sections 7, 8, 9, and 10.

3. **When may the assistant place an order?** The system prompt says to suggest trades and to execute only when the user asks or agrees. Every object in `trades` is a market order that runs with no confirmation. The schema has no separate suggestion field. A portfolio question can change cash and positions. Choose whether `trades` may contain an order only when the latest user message names that buy or sell.
  ANSWER: Yes, only when the latest user message names a buy or sell.

  Copied to sections 2 and 9.

4. **Where does `finally.db` live?** The `docker run` example uses a named volume, `finally-data`. The next sentence says the project `db/` directory maps to `/app/db`, and section 4 says the backend creates `db/finally.db` there. A named volume does not write that file into the project directory. Choose the bind mount (`-v "$(pwd)/db:/app/db"`) or the named volume, and make the command, the directory tree, and the stop scripts match.
  ANSWER: whatever is most persistent

  Recorded choice: bind-mount the project `db/` directory to `/app/db`. The file `db/finally.db` stays on the host, so it survives container removal, image rebuilds, Docker volume cleanup, and a Docker Desktop reset. A named volume does not. Copied to sections 3, 4, and 11.

5. **Who can reach port 8000?** There is no login. `POST /api/chat` spends `OPENROUTER_API_KEY`. The sample command publishes `8000:8000` on every host interface, and section 11 also says the image can deploy to a public container host. Choose whether local runs bind `127.0.0.1:8000:8000` and public hosting stays out of scope.
  ANSWER: public hosting is out of scope for now

  Recorded choice: local runs publish `127.0.0.1:8000:8000`. The cloud-deploy stretch goal is removed. Copied to section 11.

6. **What does the main chart plot before the user clicks?** Sparklines use prices received since page load. The only history route, `GET /api/portfolio/history`, returns portfolio value, not ticker prices. Choose the initial ticker (the first seed symbol) and state that the main chart uses the same since-load series as the sparkline.
  ANSWER: whatever is easiest and informative to the user

  Recorded choice: on load, select the first watchlist ticker and plot its SSE prices since page load, the same series as its sparkline. That needs no ticker-history endpoint, and the chart is filled as soon as prices arrive. Copied to sections 2 and 10.

7. **Which chart library?** Section 10 allows Lightweight Charts or Recharts. Pick one before the frontend starts.
  ANSWER: whichever better fits our acceptance criteria

  Recorded choice: Lightweight Charts for the main chart, sparklines, and the P&L line. The plan already prefers a canvas library for streaming prices, and Lightweight Charts is built for that. It has no treemap, so the heatmap stays a layout of positioned elements. Copied to section 10.

### Clarifications

- **Price the watchlist and open positions.** The priced set is the union of watchlist tickers and positions with quantity greater than zero. Remove a ticker from the cache only when it is neither watched nor held. Reject a market order when the cache has no price. Copied to section 6. Shipped `remove_ticker` still deletes the cache row.

- **A new Massive ticker is not priced immediately.** `MassiveDataSource.add_ticker` waits for the next poll, up to 15 seconds. The simulator writes a price before `add_ticker` returns. An instant fill in the same request as a new subscription needs one snapshot poll before the fill, matching `start()`. If the cache is still empty, reject the trade.

- **The SSE event is one object keyed by ticker.** `GET /api/stream/prices` sends that object about every 500ms when the cache version changes. Each value has `ticker`, `price`, `previous_price`, `timestamp` (Unix seconds), `change`, `change_percent`, and `direction` (`up`, `down`, or `flat`). `change_percent` is the move since the previous tick, times 100. Add `baseline_price` to that object. The watchlist daily change percent uses it, times 100, and is 0 when the baseline is 0. Copied to section 6. Shipped `PriceUpdate.to_dict()` does not include `baseline_price` yet.

- **`OPENROUTER_API_KEY` is required for live chat.** It is not required when `LLM_MOCK=true`. Copied to section 5. Section 9 and section 12 run mock mode without a key, including E2E tests.

- **Create the database on first request when the file is missing, empty, or tables are missing.** Copied to sections 4 and 7.

- **`users_profile.id` is the user id.** The schema introduction says every table has `user_id`. The `users_profile` column list uses `id` instead.

### Feedback

- Manual watchlist add and remove need a ticker input, an Add button, a per-row remove control, a duplicate message, and an empty-list message. Copied to section 10.

- Insufficient cash, insufficient shares, a non-positive quantity, and a missing price leave holdings unchanged and show the error under the trade bar. Copied to section 10. A position at quantity zero leaves the table and the heatmap.

- First launch has $10,000 cash and no positions. A buy at the current price starts at zero unrealized P&L. The heatmap needs a zero-P&L color and an empty state. The P&L chart needs a state for fewer than two snapshots.

- The simulator injects sudden 2–5% moves for drama. Chat context is cash, positions, watchlist prices, and portfolio value. The prompt asks for data-driven analysis and does not forbid invented news. Tell the assistant to reason only from the supplied figures, and to treat a sharp simulator move as an unexplained shock.

### Simplifications

- Drop `user_id` from `watchlist`, `positions`, `trades`, `portfolio_snapshots`, and `chat_messages` until login exists. Keep one `users_profile` row with `id` `"default"`. Make watchlist and positions unique on `ticker`. Delete the sentences about future multi-user support without a migration.

- Poll Massive every 15 seconds whenever `MASSIVE_API_KEY` is set. Delete the paid-tier interval range. The shipped client already defaults to 15 seconds, and the plan defines no tier setting.

- Use integer share quantities if the demo does not need fractional shares. The schema uses `REAL`, and the chat example uses `10`. Fractional fills make a full sell leave a dust row, so the position does not disappear.

- Leave `docker-compose.yml` out of the core path. The start scripts are the one command students run.

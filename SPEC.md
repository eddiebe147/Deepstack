---
last-synced-to-vision: 2026-04-02
status: ACTIVE
---

# SPEC

## Architecture

```
web/                           # Next.js 16 frontend (Vercel)
  src/
    app/                       # App Router pages
      (auth)/login/            # Auth flow
      app/                     # Main trading interface
      chat/                    # AI research chat
      journal/                 # Trade journal
      thesis/                  # Thesis engine
      dashboard/               # Customizable widget dashboard
      insights/                # AI pattern learning
      pricing/                 # Subscription tiers
      help/                    # Documentation
    components/                # 438 React components
      ui/                      # Base: Button, Dialog, Input, etc.
      chat/                    # Chat interface + tools
      market/                  # Charts, ticker, orderbook
      journal/                 # Trade logging + emotions
      thesis/                  # Hypothesis tracking
      prediction-markets/      # Kalshi + Polymarket
      options/                 # Chains, Greeks, payoff
      dashboard/               # 40+ widgets
      emotional-firewall/      # Pattern detection UI
      screener/                # Stock screener
    lib/
      supabase/                # Auth + DB client
      stores/                  # 25 Zustand stores
      subscription.ts          # Tier gating + trials

backend/                       # Python FastAPI
  main.py                      # API server
  routes/
    chat.py                    # Claude AI chat (Haiku/Sonnet/Opus)
    market.py                  # Alpaca market data
    prediction_markets.py      # Kalshi + Polymarket APIs
    perplexity.py              # Deep research
    options.py                 # Options chains + Greeks
```

## Data Flow

```
User (browser)
  |
  v
Next.js Frontend (Vercel)
  |-- Supabase Auth (login, sessions)
  |-- Supabase Realtime (journal, thesis, watchlists)
  |-- Alpaca WebSocket (live market data)
  |
  v
FastAPI Backend (Railway)
  |-- Anthropic Claude (AI chat, analysis)
  |-- Perplexity API (deep research)
  |-- Alpaca REST (quotes, bars, options chains)
  |-- Kalshi REST (prediction market odds)
  |-- Polymarket REST (prediction market odds)
```

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript 5 (strict) |
| Styling | Tailwind CSS 4, shadcn/ui, Radix UI |
| State | Zustand (25 stores) + localStorage persistence |
| Charts | Lightweight Charts (TradingView engine) |
| Editor | TipTap / ProseMirror (journal rich text) |
| Animations | Framer Motion |
| Backend | Python 3.11, FastAPI, WebSockets |
| AI | Anthropic Claude (Haiku, Sonnet, Opus) |
| Research | Perplexity API |
| Market Data | Alpaca Markets (real-time + historical) |
| Prediction Markets | Kalshi API + Polymarket API |
| Database | Supabase (PostgreSQL + Auth + Realtime) |
| Hosting | Vercel (frontend), Railway (backend) |
| Monitoring | Sentry, Vercel Analytics + Speed Insights |
| PWA | Serwist (offline support) |

## Features by Subscription Tier

| Feature | Free ($0) | Pro ($19/mo) | Elite ($49/mo) |
|---------|-----------|-------------|----------------|
| AI Chat | 5/day (Haiku) | 50/day (Sonnet) | Unlimited (all models) |
| Charts | Basic | 30+ indicators | Full + drawing tools |
| Journal | 10 entries | Unlimited | + emotion analytics |
| Thesis Engine | View only | Full tracking | + live validation |
| Prediction Markets | View odds | Cross-platform | + thesis linking |
| Emotional Firewall | Basic alerts | Pattern detection | + AI learning |
| Options | View chains | Greeks + builder | + payoff diagrams |
| Screener | 3 filters | Full NL + traditional | + custom alerts |
| Dashboard | 5 widgets | 20 widgets | 40+ widgets |
| Paper Trading | No | Yes | Yes |

## Deployment

| Service | URL | Project ID |
|---------|-----|-----------|
| Frontend | deepstack.trade | prj_kzjzJWL1qplE0TAzRNJhPvzDwyUt (Vercel) |
| Backend | TBD (Railway) | -- |
| Database | Supabase | scfdoayhmcruieppwawg |

## Key Files

| File | Purpose |
|------|---------|
| `web/src/lib/subscription.ts` | Tier definitions, feature gating, trial logic |
| `web/src/lib/supabase/middleware.ts` | Auth flow, protected routes |
| `web/src/app/layout.tsx` | Root layout, metadata, font loading |
| `web/src/lib/stores/` | 25 Zustand stores for app state |
| `web/package.json` | All frontend dependencies |
| `backend/main.py` | FastAPI entry point |

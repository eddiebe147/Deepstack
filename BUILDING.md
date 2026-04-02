---
last-updated: 2026-04-02
---

# BUILDING

## Timeline

### Phase 1: MVP (Dec 2025)
- AI Chat interface with Claude (Haiku/Sonnet/Opus)
- Real-time market data via Alpaca (quotes, charts, WebSocket)
- Portfolio tracking with paper trading
- Options screener and strategy builder
- Emotional Firewall v1 (basic discipline prompts)
- Supabase auth + multi-tenant data
- Deployed to Vercel (deepstack.trade)

### Phase 2: Research Platform (Dec 2025)
- Professional charts (Lightweight Charts, 30+ indicators)
- Thesis Engine (hypothesis tracking with live validation)
- Trade Journal (rich text, emotion tracking, P&L)
- Stock screener (NL + traditional filters)
- Deep Research Hub (Perplexity integration)
- Command palette (Cmd+K)
- 40+ dashboard widgets
- Mobile PWA with offline support

### Phase 3: Prediction Markets (Dec 2025)
- Kalshi API integration (live odds, event tracking)
- Polymarket API integration (cross-platform comparison)
- Prediction market thesis linking
- Politicians tracker (congressional trading activity)
- Emotional Firewall 2.0 (real-time pattern detection)
- Subscription tiers (Free/Pro/Elite)
- Trial system (14-day with phase messaging)

### Phase 4: Builder Program + Revenue (NOW)
- [x] Landing page rewrite: PM-first positioning (2026-04-02)
- [x] SEO meta tags updated for prediction markets (2026-04-02)
- [x] Triad files written (VISION/SPEC/BUILDING) (2026-04-02)
- [x] Apply for Kalshi Builder Program (submitted 2026-04-02)
- [ ] Wire Stripe checkout (backend integration)
- [ ] Integrate builder code for volume tracking
- [ ] Deepen Kalshi-specific features:
  - [ ] Cross-market correlation analysis
  - [ ] Settlement calendar with countdown
  - [ ] Historical accuracy tracker (how good are markets at predicting?)
  - [ ] Fee calculator (maker vs taker visualization)
- [ ] Record demo video for Builder Program application
- [ ] 2-minute product walkthrough highlighting PM features

### Phase 5: Growth (Next)
- [ ] Kalshi builder code revenue live
- [ ] Polymarket builder code revenue (if available)
- [ ] Content marketing: "How to trade prediction markets with discipline"
- [ ] SEO for prediction market keywords
- [ ] Community features (public thesis sharing)
- [ ] API for third-party integrations

## Architecture Decisions

### Why Prediction Markets as Primary Surface
The general trading research platform market is crowded (TradingView, ThinkorSwim, TradingView). Prediction markets are a $44B growing market with primitive tooling. Nobody has built the "Bloomberg for prediction markets." First mover advantage with Kalshi's Builder Program creates a revenue flywheel: better tools attract traders, traders generate volume, volume earns builder code revenue.

### Why Emotional Discipline as the Differentiator
92% of prediction market traders lose money. The pattern is consistent: overtrading, revenge trading after losses, chasing longshots. The Emotional Firewall is not a gimmick. It's a behavioral circuit breaker. No competitor has this. Academic research (Kahneman, Tversky) and our own V1 trading bot data confirm that emotional state is the strongest predictor of poor trading decisions.

### Why Subscriptions + Builder Codes
Pure subscription SaaS has proven unit economics ($19/$49/mo tiers). Builder code revenue is additive: every trade placed through DeepStack earns volume-based fees from Kalshi. This creates dual revenue streams where subscription revenue is stable and builder code revenue scales with user activity. The builder code also aligns incentives: we only earn when users trade, so the product must actually help them trade better.

### Why Keep Traditional Markets
Prediction markets are the primary surface, but stocks and options remain. Many prediction market traders also trade equities (the KXFED trader who also holds TLT, the KXCPI trader who also watches SPY). Removing traditional markets would narrow the audience unnecessarily. The emotional discipline engine works across all asset classes.

## Current Blockers

1. **Stripe not wired**: Subscription tiers are defined but checkout flow is unfinished. Users can't pay yet. This is the P0 blocker for revenue.

2. **Builder Program application**: Need to apply at kalshi.com/builders. Requires demo video and clear product narrative (this triad provides the narrative).

3. **Backend hosting**: Railway deployment needs to be finalized for production FastAPI server.

## Metrics to Track (Post-Launch)

| Metric | Target | Why |
|--------|--------|-----|
| MAU | 100 in 3 months | Validates product-market fit |
| Free-to-Pro conversion | 5% | Validates pricing |
| Pro-to-Elite upgrade | 15% | Validates premium features |
| Kalshi volume driven | $10K/month | Builder code revenue baseline |
| Churn (monthly) | < 8% | Retention signal |
| Emotional Firewall usage | 30% of sessions | Core differentiator adoption |

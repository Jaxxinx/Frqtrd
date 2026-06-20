---
title: Frqtrd
emoji: 📈
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Freqtrade Trading Bot

Dry run trading bot — MultiOffsetLamboV0 strategy.

## Environment Variables (HF Space Settings)
- `API_USERNAME` — Dashboard login
- `API_PASSWORD` — Dashboard password
- `JWT_SECRET` — JWT secret (min 32 chars)
- `STRATEGY` — Strategy (default: MultiOffsetLamboV0)
- `SUPABASE_DB_HOST` — Supabase pooler host (optional)
- `SUPABASE_DB_PASSWORD` — Supabase DB password (optional)
- `SUPABASE_PROJECT_REF` — Supabase project ref (optional)

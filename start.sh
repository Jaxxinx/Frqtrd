#!/bin/bash
set -e

echo "=== Freqtrade HF Space ==="

# Database: Supabase or SQLite
if [ -n "$SUPABASE_DB_PASSWORD" ]; then
    DB_URL="postgresql://postgres.mbhfuucletknrkumivhc:${SUPABASE_DB_PASSWORD}@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
    echo "DB: Supabase PostgreSQL"
else
    DB_URL="sqlite:////bot/user_data/tradesv3.dryrun.sqlite"
    echo "DB: local SQLite"
fi

# Build runtime config
python3 -c "
import json, os
with open('/bot/config.json') as f:
    cfg = json.load(f)
cfg['db_url'] = '${DB_URL}'
cfg['exchange']['key'] = os.environ.get('EXCHANGE_KEY', '')
cfg['exchange']['secret'] = os.environ.get('EXCHANGE_SECRET', '')
cfg['exchange']['passphrase'] = os.environ.get('EXCHANGE_PASSPHRASE', '')
cfg['api_server']['username'] = os.environ.get('API_USERNAME', 'freqtrader')
cfg['api_server']['password'] = os.environ.get('API_PASSWORD', 'SuperSecurePassword')
cfg['api_server']['jwt_secret_key'] = os.environ.get('JWT_SECRET', 'changeme-somethingRandomSomethingRandom12345678')
strategy = os.environ.get('STRATEGY', cfg.get('strategy', 'MultiOffsetLamboV0'))
cfg['strategy'] = strategy
with open('/bot/user_data/config-runtime.json', 'w') as f:
    json.dump(cfg, f, indent=2)
print(f'Strategy: {strategy}')
"

STRATEGY=$(python3 -c "import json; print(json.load(open('/bot/user_data/config-runtime.json'))['strategy'])")

echo "=== Starting freqtrade ==="
# Apply DB pool patch for Supabase
if [ -n "$SUPABASE_DB_PASSWORD" ]; then
    SITE_PACKAGES=$(python3 -c "import freqtrade; import os; print(os.path.dirname(os.path.dirname(freqtrade.__file__)))")
    cp /bot/patch_db_pool.py "$SITE_PACKAGES/patch_db_pool.py"
    export PYTHONSTARTUP="$SITE_PACKAGES/patch_db_pool.py"
    # Also use -c to preload the patch
    exec python3 -c "
import patch_db_pool
from freqtrade.main import main
import sys
sys.exit(main())
" trade --config /bot/user_data/config-runtime.json \
    --strategy "$STRATEGY" \
    --userdir /bot/user_data \
    --strategy-path /bot/user_data/strategies
else
    exec freqtrade trade \
        --config /bot/user_data/config-runtime.json \
        --strategy "$STRATEGY" \
        --userdir /bot/user_data \
        --strategy-path /bot/user_data/strategies
fi

"""
Custom exchange for dry run / backtesting with local yfinance data.
Uses CCXT binance for compatibility but loads OHLCV data from local feather files.
No real exchange API calls are made.
"""
import logging
import os
from typing import Any, Coroutine

import pandas as pd

from freqtrade.enums import CandleType
from freqtrade.exchange.binance import Binance
from freqtrade.exchange.exchange_types import OHLCVResponse, Ticker

logger = logging.getLogger(__name__)


class YfinanceExchange(Binance):
    """
    Exchange that reads local OHLCV data from feather files (yfinance format).
    Inherits from Binance for full CCXT compatibility.
    All API calls for market data are replaced with local file reads.
    """

    _ft_has = {
        "ohlcv_candle_limit": 10000,
        "ohlcv_has_history": True,
        "trades_has_history": False,
        "stoploss_on_exchange": False,
        "order_time_in_force": ["GTC"],
        "exchange_has_overrides": {},
        "ws_enabled": False,
    }

    def __init__(self, config: dict, validate: bool = True, **kwargs):
        original_name = config["exchange"]["name"]
        config["exchange"]["name"] = "binance"

        self._yf_dir = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "data", "yfinance"
            )
        )

        self._name = original_name
        super().__init__(config, validate=False, **kwargs)

        config["exchange"]["name"] = original_name

        self._markets = {}
        for pair in config.get("exchange", {}).get("pair_whitelist", []):
            if "/" not in pair:
                continue
            base = pair.split("/")[0]
            quote = pair.split("/")[1].split(":")[0]
            self._markets[pair] = {
                "id": pair.replace("/", "").replace(":", ""),
                "symbol": pair,
                "base": base,
                "quote": quote,
                "active": True,
                "spot": True,
                "future": False,
                "swap": False,
                "linear": False,
                "contract": False,
                "type": "spot",
                "precision": {"amount": 0.00000001, "price": 0.01},
                "limits": {
                    "amount": {"min": 0.00000001, "max": 999999999},
                    "price": {"min": 0.00000001, "max": 999999999},
                    "cost": {"min": 0.01, "max": 999999999},
                },
                "info": {},
                "maker": 0.001,
                "taker": 0.001,
            }

        logger.info(f"YfinanceExchange initialized with {len(self._markets)} pairs. "
                     f"Data dir: {self._yf_dir}")

    @property
    def name(self):
        return self._name

    def _load_async_markets(self, reload: bool = False):
        pass

    def reload_markets(self, force: bool = False, **kwargs):
        pass

    def validate_pairs(self, pairs):
        pass

    def get_fee(self, *args, **kwargs):
        return 0.001

    def price_to_precision(self, pair: str, price: float) -> float:
        return round(price, 2)

    def amount_to_precision(self, pair: str, amount: float) -> float:
        return round(amount, 8)

    def _ohlcv_to_ticks(self, df: pd.DataFrame) -> list:
        if df.empty:
            return []
        timestamps = (df["date"].astype("int64") // 10**6).values
        return [
            [int(ts), float(o), float(h), float(l), float(c), float(v)]
            for ts, o, h, l, c, v in zip(
                timestamps, df["open"], df["high"], df["low"], df["close"], df["volume"]
            )
        ]

    async def _async_get_candle_history(
        self,
        pair: str,
        timeframe: str,
        candle_type: CandleType,
        since_ms: int | None = None,
    ) -> OHLCVResponse:
        df = self._ohlcv_load(pair, timeframe)
        ticks = self._ohlcv_to_ticks(df)
        return pair, timeframe, candle_type, ticks, False

    async def _async_get_historic_ohlcv(
        self,
        pair: str,
        timeframe: str,
        since_ms: int,
        candle_type: CandleType,
        raise_: bool = False,
        until_ms: int | None = None,
    ) -> OHLCVResponse:
        df = self._ohlcv_load(pair, timeframe)

        if since_ms and not df.empty:
            since_dt = pd.Timestamp(since_ms, unit="ms", tz="UTC")
            df = df[df["date"] >= since_dt]
        if until_ms and not df.empty:
            until_dt = pd.Timestamp(until_ms, unit="ms", tz="UTC")
            df = df[df["date"] <= until_dt]

        ticks = self._ohlcv_to_ticks(df)
        return pair, timeframe, candle_type, ticks, False

    def fetch_ticker(self, pair: str) -> Ticker:
        df = self._ohlcv_load(pair, self._config.get("timeframe", "1h"))
        if df.empty:
            return Ticker(
                symbol=pair, ask=None, askVolume=None,
                bid=None, bidVolume=None, last=None,
                quoteVolume=None, baseVolume=None, percentage=None,
            )
        last = df.iloc[-1]
        prev_close = df.iloc[-2]["close"] if len(df) > 1 else last["close"]
        change = last["close"] - prev_close
        pct = (change / prev_close * 100) if prev_close else 0.0
        return Ticker(
            symbol=pair,
            ask=float(last["close"]),
            askVolume=float(last["volume"]),
            bid=float(last["close"]),
            bidVolume=float(last["volume"]),
            last=float(last["close"]),
            quoteVolume=None,
            baseVolume=float(last["volume"]),
            percentage=float(pct),
        )

    def _ohlcv_load(
        self, pair: str, timeframe: str, timerange=None, candle_type: str = ""
    ) -> pd.DataFrame:
        safe_pair = pair.replace("/", "_").replace(":", "_")
        patterns = [
            f"{safe_pair}-{timeframe}.feather",
            f"{safe_pair}-{timeframe}-spot.feather",
        ]
        if "USDT" in safe_pair:
            usd_pair = safe_pair.replace("USDT", "USD")
            patterns.extend([
                f"{usd_pair}-{timeframe}.feather",
                f"{usd_pair}-{timeframe}-spot.feather",
            ])
        for pattern in patterns:
            filepath = os.path.join(self._yf_dir, pattern)
            if os.path.exists(filepath):
                try:
                    df = pd.read_feather(filepath)
                    if "date" in df.columns:
                        if df["date"].dtype == "int64":
                            df["date"] = pd.to_datetime(df["date"], unit="ms", utc=True)
                        elif not pd.api.types.is_datetime64_any_dtype(df["date"]):
                            df["date"] = pd.to_datetime(df["date"], utc=True)
                    if timerange:
                        if timerange.startts:
                            start = pd.Timestamp(timerange.startts, unit="s", tz="UTC")
                            df = df[df["date"] >= start]
                        if timerange.stopts:
                            end = pd.Timestamp(timerange.stopts, unit="s", tz="UTC")
                            df = df[df["date"] <= end]
                    return df
                except Exception as e:
                    logger.error(f"Error loading {filepath}: {e}")
                    return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

        logger.warning(f"Data file not found for {pair} {timeframe} in {self._yf_dir}")
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])

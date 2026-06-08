"""
Technical Analysis Indicators
Computes RSI, MACD, Bollinger Bands, and Moving Averages.
Data sourced from yfinance (primary) with SQLite DB fallback.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("MarketMindAI.Indicators")

# ── Raw indicator functions ───────────────────────────────────────────────────

def compute_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (macd_line, signal_line, histogram)."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def compute_bollinger(
    prices: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Returns (upper_band, middle_band, lower_band)."""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    return sma + std * num_std, sma, sma - std * num_std


# ── Helper ────────────────────────────────────────────────────────────────────

def _safe(val) -> Optional[float]:
    try:
        v = float(val)
        return None if np.isnan(v) or np.isinf(v) else round(v, 4)
    except Exception:
        return None


def _series_tail(series: pd.Series, n: int = 30) -> List[Optional[float]]:
    return [_safe(x) for x in series.iloc[-n:].tolist()]


# ── Main entry point ──────────────────────────────────────────────────────────

def get_indicators(
    symbol: str,
    yfinance_first: bool = True,
    db_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Compute RSI, MACD, Bollinger Bands, and MAs for *symbol*.

    Parameters
    ----------
    symbol       : NSE ticker (e.g. 'TCS')
    yfinance_first : fetch 3-month daily history from yfinance before using DB
    db_history   : list of dicts with 'price' key (oldest first), used as fallback
    """
    prices: Optional[pd.Series] = None

    # 1 — try Yahoo Finance v8 API via curl_cffi (bypasses 429 rate-limiting)
    if yfinance_first:
        try:
            yf_sym = symbol.upper()
            if not yf_sym.endswith(".NS"):
                yf_sym += ".NS"
            try:
                from curl_cffi import requests as _cffi
                resp = _cffi.get(
                    f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_sym}",
                    impersonate="chrome124",
                    params={"interval": "1d", "range": "3mo"},
                    timeout=10,
                )
            except ImportError:
                import requests as _r
                resp = _r.get(
                    f"https://query2.finance.yahoo.com/v8/finance/chart/{yf_sym}",
                    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"},
                    params={"interval": "1d", "range": "3mo"},
                    timeout=10,
                )
            if resp.status_code == 200:
                d = resp.json()
                result = (d.get("chart", {}).get("result") or [None])[0]
                if result:
                    closes = (result.get("indicators", {}).get("quote", [{}])[0].get("close") or [])
                    closes = [v for v in closes if v is not None]
                    if closes:
                        prices = pd.Series(closes, dtype=float)
                        logger.debug(f"[{symbol}] Yahoo Finance v8: {len(prices)} rows")
        except Exception as exc:
            logger.warning(f"[{symbol}] Yahoo Finance fetch failed: {exc}")

    # 2 — fallback to DB rows (oldest → newest price list)
    if prices is None or len(prices) < 20:
        if db_history and len(db_history) >= 20:
            prices = pd.Series([h["price"] for h in db_history])
            logger.debug(f"[{symbol}] using DB history: {len(prices)} rows")
        else:
            return {"error": "insufficient price data (need ≥20 periods)"}

    n = len(prices)

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi = compute_rsi(prices, 14)
    rsi_val = _safe(rsi.iloc[-1])
    rsi_signal = (
        "overbought" if (rsi_val or 50) > 70
        else "oversold" if (rsi_val or 50) < 30
        else "neutral"
    )

    # ── MACD ─────────────────────────────────────────────────────────────────
    macd_line, sig_line, hist = compute_macd(prices)
    macd_val  = _safe(macd_line.iloc[-1])
    sig_val   = _safe(sig_line.iloc[-1])
    hist_val  = _safe(hist.iloc[-1])
    macd_trend = "bullish" if (macd_val or 0) > (sig_val or 0) else "bearish"

    # crossover detection (last 2 bars)
    crossover = None
    if n >= 2:
        prev_cross = (macd_line.iloc[-2] - sig_line.iloc[-2])
        curr_cross = (macd_line.iloc[-1] - sig_line.iloc[-1])
        if prev_cross < 0 < curr_cross:
            crossover = "bullish_cross"
        elif prev_cross > 0 > curr_cross:
            crossover = "bearish_cross"

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_upper, bb_mid, bb_lower = compute_bollinger(prices, 20, 2.0)
    curr_price = float(prices.iloc[-1])
    bu = _safe(bb_upper.iloc[-1])
    bm = _safe(bb_mid.iloc[-1])
    bl = _safe(bb_lower.iloc[-1])
    bw = (bu - bl) if (bu and bl) else None   # bandwidth
    pct_b = (
        round((curr_price - bl) / (bu - bl) * 100, 1)
        if bu and bl and (bu - bl) > 0 else 50.0
    )
    bb_signal = (
        "near_upper" if pct_b > 80
        else "near_lower" if pct_b < 20
        else "middle"
    )

    # ── Moving Averages ───────────────────────────────────────────────────────
    ma20 = prices.rolling(20).mean()
    ma50 = prices.rolling(min(50, n)).mean()
    ma200 = prices.rolling(min(200, n)).mean()
    ma20_val  = _safe(ma20.iloc[-1])
    ma50_val  = _safe(ma50.iloc[-1])
    ma200_val = _safe(ma200.iloc[-1])

    # ── Signals tally ─────────────────────────────────────────────────────────
    buys, sells = 0, 0
    if rsi_signal == "oversold":  buys += 1
    if rsi_signal == "overbought": sells += 1
    if macd_trend == "bullish":   buys += 1
    else:                          sells += 1
    if crossover == "bullish_cross": buys += 1
    if crossover == "bearish_cross": sells += 1
    if bb_signal == "near_lower":  buys += 1
    if bb_signal == "near_upper":  sells += 1
    if ma20_val and curr_price > ma20_val: buys += 1
    else:                                   sells += 1

    overall = "BUY" if buys > sells else "SELL" if sells > buys else "HOLD"

    # ── Build response ────────────────────────────────────────────────────────
    return {
        "symbol": symbol.upper(),
        "price": round(curr_price, 2),
        "data_points": n,
        "labels": [str(i) for i in range(min(n, 30))],

        "rsi": {
            "value": rsi_val,
            "signal": rsi_signal,
            "history": _series_tail(rsi, 30),
        },

        "macd": {
            "macd": macd_val,
            "signal_line": sig_val,
            "histogram": hist_val,
            "trend": macd_trend,
            "crossover": crossover,
            "history": {
                "macd":      _series_tail(macd_line, 30),
                "signal":    _series_tail(sig_line, 30),
                "histogram": _series_tail(hist, 30),
            },
        },

        "bollinger": {
            "upper": bu,
            "middle": bm,
            "lower": bl,
            "bandwidth": round(bw, 2) if bw else None,
            "pct_b": pct_b,
            "signal": bb_signal,
            "history": {
                "upper":  _series_tail(bb_upper, 30),
                "middle": _series_tail(bb_mid, 30),
                "lower":  _series_tail(bb_lower, 30),
                "price":  _series_tail(prices, 30),
            },
        },

        "moving_averages": {
            "ma20":  ma20_val,
            "ma50":  ma50_val,
            "ma200": ma200_val,
            "price_vs_ma20":  "above" if (ma20_val  and curr_price > ma20_val)  else "below",
            "price_vs_ma50":  "above" if (ma50_val  and curr_price > ma50_val)  else "below",
            "price_vs_ma200": "above" if (ma200_val and curr_price > ma200_val) else "below",
        },

        "summary": {
            "signal":   overall,
            "buy_signals":  buys,
            "sell_signals": sells,
            "strength": f"{max(buys, sells)}/{buys + sells}",
        },
    }

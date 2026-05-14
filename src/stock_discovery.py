"""
Stock Discovery Module
======================
Fetches the full NSE equity list dynamically from:
  1. NSE India open CSV (EQUITY_L.csv / bhavcopy) — no auth required
  2. yfinance search — fallback for broad symbol lookup
  3. Hardcoded NSE catalog — final fallback

Results are cached in memory for CACHE_TTL seconds (default 6 hours).
"""
import csv
import io
import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("MarketMindAI.StockDiscovery")

# ─── Cache ────────────────────────────────────────────────────────────────────
_CACHE: Optional[Dict[str, str]] = None   # {SYMBOL: COMPANY_NAME}
_CACHE_TS: float = 0.0
CACHE_TTL: int = 6 * 3600  # 6 hours

# ─── NSE open data URLs ────────────────────────────────────────────────────────
# Full NSE equity list (symbol + company name) – no login required
NSE_EQUITY_LIST_URL = "https://www1.nseindia.com/content/equities/EQUITY_L.csv"

# NSE bhavcopy alternate (updated daily; smaller, ~5 k rows)
NSE_BHAVCOPY_BASE = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# ─── Hardcoded fallback (same as main.py catalog) ────────────────────────────
_FALLBACK_CATALOG: Dict[str, List[str]] = {
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "OFSS"],
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB"],
    "Finance": ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "LICHSGFIN", "RECLTD", "PFC"],
    "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR", "ASHOKLEY"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "TORNTPHARM", "ALKEM", "BIOCON"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO", "COLPAL", "GODREJCP"],
    "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "ADANIGREEN", "TATAPOWER", "ADANIPORTS", "COALINDIA"],
    "Retail/Consumer": ["DMART", "TITAN", "TRENT", "NYKAA", "ZOMATO", "PAYTM", "NAUKRI", "IRCTC"],
    "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL", "NMDC", "NATIONALUM"],
    "Infra/Cement": ["ULTRACEMCO", "GRASIM", "AMBUJACEM", "ACC", "SHREECEM", "LT", "SIEMENS"],
}


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_all_nse_stocks(force_refresh: bool = False) -> Dict[str, str]:
    """
    Return a dict of {SYMBOL: company_name} for all NSE-listed equities.

    Sources tried in order:
      1. In-memory cache (if fresh)
      2. NSE EQUITY_L.csv
      3. Fallback flat catalog (symbols only, no company names)
    """
    global _CACHE, _CACHE_TS

    if not force_refresh and _CACHE and (time.time() - _CACHE_TS < CACHE_TTL):
        return _CACHE

    logger.info("Fetching NSE live stock list …")

    stocks = _try_nse_equity_list()
    if not stocks:
        logger.warning("NSE CSV unavailable, using fallback catalog")
        stocks = _fallback_flat()

    _CACHE = stocks
    _CACHE_TS = time.time()
    logger.info(f"Loaded {len(stocks)} NSE stocks")
    return stocks


def get_catalog_grouped(force_refresh: bool = False) -> Dict[str, List[Dict]]:
    """
    Return a dict of {sector: [{symbol, name}, …]}.

    When the live NSE list is available the stocks are bucketed into the
    known sectors by simple prefix/keyword matching; unmatched stocks go
    into an "Other" bucket.  If the live fetch fails, the hardcoded catalog
    is returned directly.
    """
    all_stocks = fetch_all_nse_stocks(force_refresh=force_refresh)

    # If only fallback is available (no company names), return sectored catalog
    if len(all_stocks) < 500:
        return {
            sector: [{"symbol": s, "name": s} for s in tickers]
            for sector, tickers in _FALLBACK_CATALOG.items()
        }

    # Build a fast lookup from symbol → sector using fallback catalog
    sym_to_sector: Dict[str, str] = {}
    for sector, tickers in _FALLBACK_CATALOG.items():
        for t in tickers:
            sym_to_sector[t] = sector

    sectored: Dict[str, List[Dict]] = {s: [] for s in _FALLBACK_CATALOG}
    sectored["Other"] = []

    for sym, name in sorted(all_stocks.items()):
        sector = sym_to_sector.get(sym, "Other")
        sectored[sector].append({"symbol": sym, "name": name})

    # Remove empty sectors
    return {k: v for k, v in sectored.items() if v}


def search_stocks(keyword: str, limit: int = 50) -> List[Dict]:
    """
    Search all NSE stocks by symbol prefix or company name substring.
    Returns list of {symbol, name}.
    """
    kw = keyword.strip().upper()
    all_stocks = fetch_all_nse_stocks()
    results = [
        {"symbol": sym, "name": name}
        for sym, name in all_stocks.items()
        if kw in sym or kw in name.upper()
    ]
    return results[:limit]


# ── Private helpers ────────────────────────────────────────────────────────────

def _try_nse_equity_list() -> Dict[str, str]:
    """Download and parse the NSE EQUITY_L.csv. Returns {} on any error."""
    urls = [NSE_EQUITY_LIST_URL, NSE_BHAVCOPY_BASE]
    for url in urls:
        try:
            resp = requests.get(url, headers=_NSE_HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.debug(f"NSE CSV {url} returned {resp.status_code}")
                continue
            # CSV columns vary — try to detect SYMBOL and NAME columns
            text = resp.text
            reader = csv.DictReader(io.StringIO(text))
            stocks: Dict[str, str] = {}
            for row in reader:
                # Column names differ between old and new NSE CSVs
                sym = (
                    row.get("SYMBOL") or row.get("Symbol") or
                    row.get("symbol") or row.get(" SYMBOL")
                )
                name = (
                    row.get("NAME OF COMPANY") or row.get("Company Name") or
                    row.get("companyName") or row.get("NAME") or sym
                )
                if sym:
                    stocks[sym.strip().upper()] = (name or sym).strip()
            if stocks:
                logger.info(f"Loaded {len(stocks)} stocks from {url}")
                return stocks
        except Exception as exc:
            logger.debug(f"NSE CSV fetch error ({url}): {exc}")
    return {}


def _fallback_flat() -> Dict[str, str]:
    """Return the hardcoded catalog as a flat {symbol: symbol} dict."""
    result: Dict[str, str] = {}
    for tickers in _FALLBACK_CATALOG.values():
        for t in tickers:
            result[t] = t
    return result

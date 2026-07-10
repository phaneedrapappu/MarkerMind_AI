"""
Market Data Agent - Fetches and processes market data.
Primary source: NSE India API.
Fallback: yfinance (Yahoo Finance) when NSE is unreachable.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import csv
import io
import requests

from ..agents.base_agent import BaseAgent
from ..data_sources.nse_fetcher import NSEDataFetcher
from ..models.market_data import (
    StockData, BulkBlockDeal, InstitutionalActivity,
    PromoterHolding, MarketDataSnapshot, TransactionType
)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    from curl_cffi import requests as cffi_requests
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False


class MarketDataAgent(BaseAgent):
    """
    Market Data Agent - Responsible for fetching stock market data
    including buy/sell activity, bulk/block deals, and institutional flows.
    Falls back to yfinance when NSE API is unreachable.
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__("MarketDataAgent", config)
        self.stocks = config.get('stocks', [])
        self.data_sources = config.get('data_sources', ['NSE'])
        self.nse_fetcher: Optional[NSEDataFetcher] = None
        self.collected_data: List[MarketDataSnapshot] = []
        self.db = db_manager
        self._finnhub_india_blocked = False   # set True on first 403 (free-tier NSE block)
        
    def initialize(self) -> bool:
        """
        Initialize the agent
        
        Returns:
            True if successful
        """
        try:
            self.logger.info("Initializing Market Data Agent")
            
            # Initialize NSE data fetcher
            if 'NSE' in self.data_sources:
                self.nse_fetcher = NSEDataFetcher(
                    timeout=self.config.get('timeout', 30)
                )
                self.logger.info("NSE Data Fetcher initialized")
            
            self.logger.info(f"Monitoring stocks: {', '.join(self.stocks)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Market Data Agent: {e}")
            return False
    
    def execute(self) -> List[MarketDataSnapshot]:
        """
        Execute the agent - fetch market data for all stocks
        
        Returns:
            List of MarketDataSnapshot objects
        """
        self.log_execution()
        self.logger.info("Executing Market Data Agent")
        
        self.collected_data = []
        
        for stock_symbol in self.stocks:
            try:
                snapshot = self._fetch_stock_data(stock_symbol)
                if snapshot:
                    self.collected_data.append(snapshot)
                    self.logger.info(f"Successfully fetched data for {stock_symbol}")
                    self._print_stock_summary(snapshot)
                    # Persist to DB
                    if self.db:
                        try:
                            self.db.save_stock_data({
                                "symbol": snapshot.stock_data.symbol,
                                "company_name": snapshot.stock_data.company_name,
                                "timestamp": snapshot.stock_data.timestamp,
                                "price": snapshot.stock_data.price,
                                "open_price": snapshot.stock_data.open_price,
                                "high": snapshot.stock_data.high,
                                "low": snapshot.stock_data.low,
                                "close_price": snapshot.stock_data.close_price,
                                "volume": snapshot.stock_data.volume,
                                "change": snapshot.stock_data.change,
                                "change_percent": snapshot.stock_data.change_percent,
                                "source": snapshot.stock_data.source,
                            })
                        except Exception as db_exc:
                            self.logger.warning(f"DB persist failed for {stock_symbol}: {db_exc}")
                else:
                    self.logger.warning(f"No data fetched for {stock_symbol}")
                
            except Exception as e:
                self.logger.error(f"Error fetching data for {stock_symbol}: {e}")
        
        return self.collected_data
    
    def _fetch_stock_data(self, symbol: str) -> Optional[MarketDataSnapshot]:
        """
        Fetch complete data for a single stock.
        Tries NSE → yfinance → Stooq → BSE in order until one succeeds.
        """
        if not self.nse_fetcher:
            self.logger.error("NSE fetcher not initialized")
            return None
        
        # Attempt NSE
        quote_data = self.nse_fetcher.get_stock_quote(symbol)

        # yfinance fallback
        if not quote_data:
            self.logger.info(f"{symbol}: NSE unavailable, trying Yahoo Finance …")
            quote_data = self._fetch_via_yfinance(symbol)

        # Finnhub fallback (60 req/min free tier)
        if not quote_data:
            self.logger.info(f"{symbol}: Yahoo Finance failed, trying Finnhub …")
            quote_data = self._fetch_via_finnhub(symbol)

        # Stooq fallback
        if not quote_data:
            self.logger.info(f"{symbol}: Finnhub failed, trying Stooq …")
            quote_data = self._fetch_via_stooq(symbol)

        # BSE India fallback
        if not quote_data:
            self.logger.info(f"{symbol}: Stooq failed, trying BSE India …")
            quote_data = self._fetch_via_bse(symbol)

        # Alpha Vantage fallback
        if not quote_data:
            self.logger.info(f"{symbol}: BSE failed, trying Alpha Vantage …")
            quote_data = self._fetch_via_alpha_vantage(symbol)

        # Local DB cache — last resort when all live sources are unavailable
        if not quote_data:
            self.logger.info(f"{symbol}: all live sources failed, trying local cache …")
            quote_data = self._fetch_from_cache(symbol)

        if not quote_data:
            self.logger.warning(f"{symbol}: all data sources failed (including cache)")
            return None
        
        # Create StockData object
        stock_data = StockData(
            symbol=quote_data['symbol'],
            company_name=quote_data['company_name'],
            timestamp=quote_data['timestamp'],
            price=quote_data['price'],
            open_price=quote_data['open'],
            high=quote_data['high'],
            low=quote_data['low'],
            close_price=quote_data['close'],
            volume=quote_data['volume'],
            change=quote_data['change'],
            change_percent=quote_data['change_percent'],
            source=quote_data.get('source', 'NSE')
        )
        
        # Fetch bulk deals — best-effort only, skip silently if NSE blocks
        bulk_deals = []
        try:
            bulk_deals_data = self.nse_fetcher.get_bulk_deals()
            bulk_deals = self._parse_bulk_deals(bulk_deals_data, symbol)
        except Exception:
            pass
        
        # Fetch block deals
        block_deals = []
        try:
            block_deals_data = self.nse_fetcher.get_block_deals()
            block_deals = self._parse_block_deals(block_deals_data, symbol)
        except Exception:
            pass
        
        # Fetch FII/DII data
        institutional_activity = []
        try:
            fii_dii_data = self.nse_fetcher.get_fii_dii_data()
            institutional_activity = self._parse_institutional_activity(fii_dii_data)
        except Exception:
            pass
        
        snapshot = MarketDataSnapshot(
            stock_data=stock_data,
            bulk_block_deals=bulk_deals + block_deals,
            institutional_activity=institutional_activity
        )
        return snapshot

    # ── Yahoo Finance helpers ─────────────────────────────────────────────────
    # NOTE: crumb/cookie flow removed — visiting finance.yahoo.com first
    # triggers 429 rate-limiting on the chart endpoint. Plain direct requests
    # to v8 API work reliably without any authentication.
    _YF_UA = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    def _fetch_via_yfinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from Yahoo Finance v8 API.
        Uses curl_cffi with Chrome TLS fingerprint to bypass 429 rate-limits;
        falls back to plain requests if curl_cffi is unavailable.
        """
        for suffix in (".NS", ".BO"):
            try:
                url = (
                    f"https://query2.finance.yahoo.com/v8/finance/chart/"
                    f"{symbol}{suffix}"
                )
                if CURL_CFFI_AVAILABLE:
                    resp = cffi_requests.get(
                        url,
                        impersonate="chrome124",
                        params={"interval": "1d", "range": "5d"},
                        timeout=8,
                    )
                else:
                    resp = requests.get(
                        url,
                        headers={"User-Agent": self._YF_UA},
                        params={"interval": "1d", "range": "5d"},
                        timeout=8,
                    )
                if resp.status_code == 429:
                    self.logger.debug(f"Yahoo Finance rate-limited for {symbol}{suffix}")
                    continue
                if resp.status_code != 200 or not resp.text.strip():
                    continue
                data   = resp.json()
                result = (data.get("chart", {}).get("result") or [None])[0]
                if not result:
                    continue
                meta   = result.get("meta", {})
                quotes = result.get("indicators", {}).get("quote", [{}])[0]
                closes = [v for v in (quotes.get("close")  or []) if v is not None]
                opens  = [v for v in (quotes.get("open")   or []) if v is not None]
                highs  = [v for v in (quotes.get("high")   or []) if v is not None]
                lows   = [v for v in (quotes.get("low")    or []) if v is not None]
                vols   = [v for v in (quotes.get("volume") or []) if v is not None]
                if not closes:
                    continue
                close      = float(closes[-1])
                prev_close = float(closes[-2]) if len(closes) >= 2 else float(meta.get("previousClose") or close)
                change     = close - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                return {
                    "symbol":         symbol.upper(),
                    "company_name":   meta.get("shortName") or meta.get("symbol") or symbol,
                    "timestamp":      datetime.now(),
                    "price":          close,
                    "open":           float(opens[-1]) if opens else close,
                    "high":           float(highs[-1]) if highs else close,
                    "low":            float(lows[-1])  if lows  else close,
                    "close":          close,
                    "volume":         int(vols[-1]) if vols else 0,
                    "change":         round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "source":         f"Yahoo Finance ({suffix.strip('.')})",
                }
            except Exception as exc:
                self.logger.debug(f"Yahoo Finance ({suffix}) for {symbol}: {exc}")
        return None

    def _fetch_via_stooq(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from Stooq CSV API. Returns None if Stooq serves HTML (bot-block)."""
        try:
            ticker = f"{symbol.lower()}.ns"
            url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            # Stooq returns HTML when bot-blocked — detect and skip
            if resp.text.lstrip().startswith("<"):
                self.logger.debug(f"Stooq returned HTML for {symbol} (bot-blocked)")
                return None
            reader = csv.DictReader(io.StringIO(resp.text))
            rows = [r for r in reader if r.get("Close") not in (None, "", "null", "N/D")]
            if not rows:
                return None
            r = rows[-1]   # last trading day
            close = float(r.get("Close") or 0)
            open_ = float(r.get("Open") or close)
            prev_close = float(rows[-2]["Close"]) if len(rows) >= 2 else open_
            change = close - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            if close == 0:
                return None
            try:
                ts = datetime.strptime(r.get("Date", ""), "%Y-%m-%d")
            except Exception:
                ts = datetime.now()
            return {
                "symbol": symbol.upper(),
                "company_name": symbol.upper(),
                "timestamp": ts,
                "price": close,
                "open": open_,
                "high": float(r.get("High") or close),
                "low": float(r.get("Low") or close),
                "close": close,
                "volume": int(float(r.get("Volume") or 0)),
                "change": change,
                "change_percent": change_pct,
                "source": "Stooq",
            }
        except Exception as exc:
            self.logger.error(f"Stooq fetch failed for {symbol}: {exc}")
            return None

    def _fetch_via_bse(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from BSE India public API (no auth required)."""
        # BSE uses numeric scrip codes; map via search API 
        try:
            search_url = (
                f"https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w"
                f"?Debtflag=&scripcode=&Scripname={symbol}&segment=0&status=A"
            )
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.bseindia.com/",
            }
            sr = requests.get(search_url, headers=headers, timeout=10)
            sr.raise_for_status()
            results = sr.json()
            if not results:
                return None
            scrip_code = results[0].get("SCRIP_CD") or results[0].get("scrip_cd")
            if not scrip_code:
                return None

            quote_url = (
                f"https://api.bseindia.com/BseIndiaAPI/api/getQuoteData/w"
                f"?scripcode={scrip_code}&flag=C&quotetype=EQ"
            )
            qr = requests.get(quote_url, headers=headers, timeout=10)
            qr.raise_for_status()
            q = qr.json()
            close = float(q.get("CurrRate") or q.get("PrevRate") or 0)
            if close == 0:
                return None
            prev = float(q.get("PrevRate") or close)
            change = close - prev
            change_pct = (change / prev * 100) if prev else 0
            return {
                "symbol": symbol.upper(),
                "company_name": q.get("CompanyName", symbol),
                "timestamp": datetime.now(),
                "price": close,
                "open": float(q.get("OpenRate") or close),
                "high": float(q.get("High52") or close),
                "low": float(q.get("Low52") or close),
                "close": close,
                "volume": int(float(q.get("TotalTradedQty") or 0)),
                "change": change,
                "change_percent": change_pct,
                "source": "BSE",
            }
        except Exception as exc:
            self.logger.error(f"BSE fetch failed for {symbol}: {exc}")
            return None

    def _fetch_via_finnhub(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch quote from Finnhub.
        Free tier (60 req/min) only covers US/major exchanges — NSE India
        requires a paid Finnhub plan. On first 403 a one-time warning is
        logged and all further Finnhub calls are skipped this session.
        """
        import os
        if self._finnhub_india_blocked:
            return None
        api_key = os.getenv("FINNHUB_KEY", "").strip()
        if not api_key:
            self.logger.debug("Finnhub: FINNHUB_KEY not set — skipping")
            return None
        try:
            url = "https://finnhub.io/api/v1/quote"
            # Use SYMBOL.NS format — returns 403 on free tier (better than silent zeros)
            resp = requests.get(url, params={"symbol": f"{symbol.upper()}.NS", "token": api_key}, timeout=8)
            if resp.status_code == 403:
                self._finnhub_india_blocked = True
                self.logger.warning(
                    "Finnhub: free tier does not include NSE India data (403). "
                    "Skipping Finnhub for this session. "
                    "Upgrade at https://finnhub.io or remove FINNHUB_KEY from .env to suppress this."
                )
                return None
            resp.raise_for_status()
            d = resp.json()
            price = float(d.get("c") or 0)
            if price == 0:
                return None
            prev  = float(d.get("pc") or price)
            chg   = round(price - prev, 2)
            chg_p = round((chg / prev * 100) if prev else 0, 2)
            return {
                "symbol":         symbol.upper(),
                "company_name":   symbol.upper(),
                "timestamp":      datetime.now(),
                "price":          price,
                "open":           float(d.get("o") or price),
                "high":           float(d.get("h") or price),
                "low":            float(d.get("l") or price),
                "close":          price,
                "volume":         0,
                "change":         chg,
                "change_percent": chg_p,
                "source":         "Finnhub",
            }
        except Exception as exc:
            self.logger.warning(f"Finnhub fetch failed for {symbol}: {exc}")
            return None

    def _fetch_via_alpha_vantage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch quote from Alpha Vantage (free tier: 25 req/day).
        Requires ALPHA_VANTAGE_KEY in .env (get free key at https://www.alphavantage.co/support/#api-key).
        """
        import os
        api_key = os.getenv("ALPHA_VANTAGE_KEY", "demo")
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": f"{symbol}.BSE",   # Alpha Vantage uses .BSE for Indian stocks
                "apikey": api_key,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            q = data.get("Global Quote", {})
            close = float(q.get("05. price") or 0)
            if close == 0:
                # Try NSE suffix
                params["symbol"] = f"{symbol}.NSE"
                resp = requests.get(url, params=params, timeout=10)
                q = resp.json().get("Global Quote", {})
                close = float(q.get("05. price") or 0)
            if close == 0:
                return None
            prev_close = float(q.get("08. previous close") or close)
            change     = float(q.get("09. change") or close - prev_close)
            change_pct = float(q.get("10. change percent", "0%").replace("%", "") or 0)
            return {
                "symbol": symbol.upper(),
                "company_name": symbol.upper(),
                "timestamp": datetime.now(),
                "price": close,
                "open": float(q.get("02. open") or close),
                "high": float(q.get("03. high") or close),
                "low": float(q.get("04. low") or close),
                "close": close,
                "volume": int(float(q.get("06. volume") or 0)),
                "change": change,
                "change_percent": change_pct,
                "source": "Alpha Vantage",
            }
        except Exception as exc:
            self.logger.error(f"Alpha Vantage fetch failed for {symbol}: {exc}")
            return None

    def _fetch_from_cache(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Return the most recent stock data from the local SQLite DB."""
        try:
            import sqlite3, os
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "marketmind.db"
            )
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM stock_data WHERE symbol = ? ORDER BY timestamp DESC LIMIT 1",
                (symbol.upper(),)
            ).fetchone()
            conn.close()
            if not row:
                return None
            cached_ts = row["timestamp"]
            self.logger.warning(
                f"{symbol}: using cached data from {cached_ts} (market may be closed)"
            )
            return {
                "symbol": row["symbol"],
                "company_name": row["company_name"],
                "timestamp": datetime.now(),
                "price": row["price"],
                "open": row["open_price"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close_price"],
                "volume": row["volume"],
                "change": row["change"],
                "change_percent": row["change_percent"],
                "source": f"Cache ({cached_ts[:10]})",
            }
        except Exception as exc:
            self.logger.debug(f"Cache fetch failed for {symbol}: {exc}")
            return None

    def _parse_bulk_deals(self, deals_data: List[Dict], symbol: str) -> List[BulkBlockDeal]:
        """Parse bulk deals data"""
        bulk_deals = []
        
        for deal in deals_data:
            if deal.get('symbol', '').upper() == symbol.upper():
                try:
                    bulk_deal = BulkBlockDeal(
                        symbol=symbol.upper(),
                        date=datetime.now(),
                        deal_type='BULK',
                        client_name=deal.get('clientName', ''),
                        quantity=int(deal.get('quantity', 0)),
                        price=float(deal.get('price', 0)),
                        transaction_type=TransactionType.BUY if 'buy' in deal.get('tradeType', '').lower() else TransactionType.SELL,
                        source='NSE'
                    )
                    bulk_deals.append(bulk_deal)
                except Exception as e:
                    self.logger.error(f"Error parsing bulk deal: {e}")
        
        return bulk_deals
    
    def _parse_block_deals(self, deals_data: List[Dict], symbol: str) -> List[BulkBlockDeal]:
        """Parse block deals data"""
        block_deals = []
        
        for deal in deals_data:
            if deal.get('symbol', '').upper() == symbol.upper():
                try:
                    block_deal = BulkBlockDeal(
                        symbol=symbol.upper(),
                        date=datetime.now(),
                        deal_type='BLOCK',
                        client_name=deal.get('clientName', ''),
                        quantity=int(deal.get('quantity', 0)),
                        price=float(deal.get('price', 0)),
                        transaction_type=TransactionType.BLOCK_DEAL,
                        source='NSE'
                    )
                    block_deals.append(block_deal)
                except Exception as e:
                    self.logger.error(f"Error parsing block deal: {e}")
        
        return block_deals
    
    def _parse_institutional_activity(self, fii_dii_data: Optional[Dict]) -> List[InstitutionalActivity]:
        """Parse FII/DII institutional activity data"""
        institutional_activities = []
        
        if not fii_dii_data:
            return institutional_activities
        
        try:
            # Parse FII data
            if 'fii' in fii_dii_data:
                fii_data = fii_dii_data['fii']
                fii_activity = InstitutionalActivity(
                    date=datetime.now(),
                    institution_type='FII',
                    buy_value=float(fii_data.get('buyValue', 0)),
                    sell_value=float(fii_data.get('sellValue', 0)),
                    net_value=float(fii_data.get('netValue', 0))
                )
                institutional_activities.append(fii_activity)
            
            # Parse DII data
            if 'dii' in fii_dii_data:
                dii_data = fii_dii_data['dii']
                dii_activity = InstitutionalActivity(
                    date=datetime.now(),
                    institution_type='DII',
                    buy_value=float(dii_data.get('buyValue', 0)),
                    sell_value=float(dii_data.get('sellValue', 0)),
                    net_value=float(dii_data.get('netValue', 0))
                )
                institutional_activities.append(dii_activity)
                
        except Exception as e:
            self.logger.error(f"Error parsing institutional activity: {e}")
        
        return institutional_activities
    
    def _print_stock_summary(self, snapshot: MarketDataSnapshot):
        """Print a summary of the stock data"""
        stock = snapshot.stock_data
        print(f"\n{'='*60}")
        print(f"📊 {stock.company_name} ({stock.symbol})")
        print(f"{'='*60}")
        print(f"💰 Current Price: ₹{stock.price:,.2f}")
        print(f"📈 Change: ₹{stock.change:+.2f} ({stock.change_percent:+.2f}%)")
        print(f"📊 Open: ₹{stock.open_price:,.2f} | High: ₹{stock.high:,.2f} | Low: ₹{stock.low:,.2f}")
        print(f"📦 Volume: {stock.volume:,}")
        print(f"🕒 Last Updated: {stock.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if snapshot.bulk_block_deals:
            print(f"\n🔔 Bulk/Block Deals: {len(snapshot.bulk_block_deals)}")
            for deal in snapshot.bulk_block_deals:
                print(f"  - {deal.deal_type}: {deal.client_name} | Qty: {deal.quantity:,} @ ₹{deal.price:.2f}")
        
        if snapshot.institutional_activity:
            print(f"\n🏦 Institutional Activity:")
            for activity in snapshot.institutional_activity:
                print(f"  - {activity.institution_type}: Buy ₹{activity.buy_value:,.0f}Cr | Sell ₹{activity.sell_value:,.0f}Cr | Net ₹{activity.net_value:+,.0f}Cr")
        
        print(f"{'='*60}\n")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up Market Data Agent")
        if self.nse_fetcher:
            self.nse_fetcher.close()
    
    def get_collected_data(self) -> List[MarketDataSnapshot]:
        """Get the collected data"""
        return self.collected_data

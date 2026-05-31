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
                
                time.sleep(1)   # Rate limit
                
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

        # yfinance fallback (direct Yahoo Finance v8 HTTP API)
        if not quote_data:
            self.logger.warning(f"NSE fetch failed for {symbol}, trying Yahoo Finance …")
            quote_data = self._fetch_via_yfinance(symbol)

        # BSE India fallback
        if not quote_data:
            self.logger.warning(f"Yahoo Finance failed for {symbol}, trying BSE India …")
            quote_data = self._fetch_via_bse(symbol)

        # Alpha Vantage fallback (free key: set ALPHA_VANTAGE_KEY in .env)
        if not quote_data:
            self.logger.warning(f"BSE failed for {symbol}, trying Alpha Vantage …")
            quote_data = self._fetch_via_alpha_vantage(symbol)
        
        if not quote_data:
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
        
        # Fetch bulk deals
        bulk_deals = []
        try:
            bulk_deals_data = self.nse_fetcher.get_bulk_deals()
            bulk_deals = self._parse_bulk_deals(bulk_deals_data, symbol)
        except Exception as e:
            self.logger.warning(f"Could not fetch bulk deals: {e}")
        
        # Fetch block deals
        block_deals = []
        try:
            block_deals_data = self.nse_fetcher.get_block_deals()
            block_deals = self._parse_block_deals(block_deals_data, symbol)
        except Exception as e:
            self.logger.warning(f"Could not fetch block deals: {e}")
        
        # Fetch FII/DII data
        institutional_activity = []
        try:
            fii_dii_data = self.nse_fetcher.get_fii_dii_data()
            institutional_activity = self._parse_institutional_activity(fii_dii_data)
        except Exception as e:
            self.logger.warning(f"Could not fetch FII/DII data: {e}")
        
        snapshot = MarketDataSnapshot(
            stock_data=stock_data,
            bulk_block_deals=bulk_deals + block_deals,
            institutional_activity=institutional_activity
        )
        return snapshot

    # ── Yahoo Finance helpers ─────────────────────────────────────────────────
    _yf_crumb: Optional[str] = None
    _yf_session: Optional[requests.Session] = None

    def _get_yf_crumb(self) -> Optional[str]:
        """Obtain a Yahoo Finance crumb+cookie (required since 2024)."""
        try:
            sess = requests.Session()
            sess.headers.update({
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
            })
            # Step 1: hit the main page to get cookies
            sess.get("https://finance.yahoo.com", timeout=10)
            # Step 2: get the crumb
            r = sess.get(
                "https://query2.finance.yahoo.com/v1/test/getcrumb",
                timeout=10,
            )
            crumb = r.text.strip()
            if crumb and len(crumb) < 20:
                MarketDataAgent._yf_crumb = crumb
                MarketDataAgent._yf_session = sess
                return crumb
        except Exception as exc:
            self.logger.warning(f"Could not get YF crumb: {exc}")
        return None

    def _fetch_via_yfinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch quote directly from Yahoo Finance v8 API with crumb auth."""
        crumb = MarketDataAgent._yf_crumb or self._get_yf_crumb()
        sess  = MarketDataAgent._yf_session or requests.Session()

        for suffix in (".NS", ".BO"):
            for attempt in range(3):
                try:
                    if attempt:
                        time.sleep(2 ** attempt)
                    params: Dict[str, Any] = {"interval": "1d", "range": "5d"}
                    if crumb:
                        params["crumb"] = crumb
                    url = (
                        f"https://query2.finance.yahoo.com/v8/finance/chart/"
                        f"{symbol}{suffix}"
                    )
                    resp = sess.get(url, params=params, timeout=10)
                    if resp.status_code == 401:
                        # Crumb expired — refresh and retry
                        crumb = self._get_yf_crumb()
                        sess  = MarketDataAgent._yf_session or sess
                        continue
                    if resp.status_code == 429:
                        self.logger.warning(f"YF rate-limited ({suffix}), retrying…")
                        time.sleep(3)
                        continue
                    if resp.status_code != 200:
                        break
                    data   = resp.json()
                    result = (data.get("chart", {}).get("result") or [None])[0]
                    if not result:
                        break
                    meta   = result.get("meta", {})
                    quotes = result.get("indicators", {}).get("quote", [{}])[0]
                    closes = [v for v in (quotes.get("close")  or []) if v is not None]
                    opens  = [v for v in (quotes.get("open")   or []) if v is not None]
                    highs  = [v for v in (quotes.get("high")   or []) if v is not None]
                    lows   = [v for v in (quotes.get("low")    or []) if v is not None]
                    vols   = [v for v in (quotes.get("volume") or []) if v is not None]
                    if not closes:
                        break
                    close      = float(closes[-1])
                    prev_close = float(closes[-2]) if len(closes) >= 2 else float(meta.get("previousClose") or close)
                    change     = close - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0
                    return {
                        "symbol": symbol.upper(),
                        "company_name": meta.get("shortName") or meta.get("symbol") or symbol,
                        "timestamp": datetime.now(),
                        "price": close,
                        "open": float(opens[-1]) if opens else close,
                        "high": float(highs[-1]) if highs else close,
                        "low": float(lows[-1]) if lows else close,
                        "close": close,
                        "volume": int(vols[-1]) if vols else 0,
                        "change": change,
                        "change_percent": change_pct,
                        "source": f"Yahoo Finance ({suffix.strip('.')})",
                    }
                except Exception as exc:
                    self.logger.warning(f"Yahoo Finance ({suffix}) attempt {attempt+1} for {symbol}: {exc}")
        return None

    def _fetch_via_stooq(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch quote from Stooq (free, no API key, reliable for NSE stocks)."""
        try:
            # Use historical daily endpoint — returns last N rows, works on weekends
            ticker = f"{symbol.lower()}.ns"
            url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
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

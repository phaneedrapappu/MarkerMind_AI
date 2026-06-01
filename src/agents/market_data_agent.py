"""
Market Data Agent - Fetches and processes market data.
Primary source: NSE India API.
Fallback: yfinance (Yahoo Finance) when NSE is unreachable.
Secondary fallback: direct HTTP to Yahoo Finance chart API.
"""
import logging
import requests as _requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

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
        Tries NSE first; falls back to yfinance if NSE is unavailable.
        """
        if not self.nse_fetcher:
            self.logger.error("NSE fetcher not initialized")
            return None
        
        # Attempt NSE
        quote_data = self.nse_fetcher.get_stock_quote(symbol)

        # yfinance fallback
        if not quote_data and YFINANCE_AVAILABLE:
            self.logger.warning(f"NSE fetch failed for {symbol}, trying yfinance …")
            quote_data = self._fetch_via_yfinance(symbol)
        
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

    def _fetch_via_yfinance(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch basic quote data for an NSE stock.

        Strategy (first success wins):
          1. yf.download()            – avoids Ticker() JSON-decode bugs
          2. Ticker().history()       – classic yfinance approach
          3. Direct Yahoo Finance API – raw HTTP, works when yfinance is blocked
        """
        ticker_sym = f"{symbol}.NS"

        # ── attempt 1: yf.download ────────────────────────────────────────────
        hist = None
        if YFINANCE_AVAILABLE:
            try:
                import pandas as _pd
                hist = yf.download(
                    ticker_sym,
                    period="5d",
                    auto_adjust=True,
                    progress=False,
                    timeout=15,
                )
                # Newer yfinance returns MultiIndex columns for a single ticker
                if hist is not None and not hist.empty and isinstance(hist.columns, _pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
            except Exception as dl_exc:
                self.logger.debug(f"yf.download failed for {ticker_sym}: {dl_exc}")
                hist = None

        # ── attempt 2: Ticker().history ───────────────────────────────────────
        if (hist is None or hist.empty) and YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(ticker_sym)
                hist = ticker.history(period="5d")
            except Exception as hist_exc:
                self.logger.debug(f"yfinance Ticker.history failed for {symbol}: {hist_exc}")
                hist = None

        # ── parse yfinance result if we got something ─────────────────────────
        if hist is not None and not hist.empty:
            try:
                row = hist.iloc[-1]
                prev_row = hist.iloc[-2] if len(hist) >= 2 else row
                prev_close = float(prev_row["Close"])
                close = float(row["Close"])
                change = close - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0.0
                return {
                    "symbol": symbol.upper(),
                    "company_name": symbol,
                    "timestamp": datetime.now(),
                    "price": close,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": close,
                    "volume": int(row.get("Volume", 0)),
                    "change": float(change),
                    "change_percent": float(change_pct),
                    "source": "Yahoo Finance",
                }
            except Exception as exc:
                self.logger.debug(f"yfinance data parsing failed for {symbol}: {exc}")

        # ── attempt 3: direct Yahoo Finance chart API ─────────────────────────
        return self._fetch_via_yahoo_direct(symbol)

    _YAHOO_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    def _fetch_via_yahoo_direct(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Direct HTTP call to Yahoo Finance v8 chart API — bypasses yfinance."""
        ticker_sym = f"{symbol}.NS"
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_sym}"
            f"?range=5d&interval=1d"
        )
        try:
            resp = _requests.get(url, headers=self._YAHOO_HEADERS, timeout=15)
            if resp.status_code != 200:
                self.logger.warning(
                    f"Yahoo direct API returned {resp.status_code} for {symbol}"
                )
                return None
            data = resp.json()
            result = data.get("chart", {}).get("result") or []
            if not result:
                return None
            meta = result[0].get("meta", {})
            price = float(meta.get("regularMarketPrice") or 0)
            prev_close = float(meta.get("chartPreviousClose") or meta.get("previousClose") or price)
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0.0
            # Pull OHLV from the last indicator row if available
            indicators = result[0].get("indicators", {}).get("quote", [{}])[0]
            opens  = indicators.get("open")  or []
            highs  = indicators.get("high")  or []
            lows   = indicators.get("low")   or []
            closes = indicators.get("close") or []
            volumes = indicators.get("volume") or []
            last_open   = float(opens[-1])   if opens   else price
            last_high   = float(highs[-1])   if highs   else price
            last_low    = float(lows[-1])    if lows    else price
            last_close  = float(closes[-1])  if closes  else price
            last_volume = int(volumes[-1])   if volumes else 0
            return {
                "symbol": symbol.upper(),
                "company_name": meta.get("longName") or symbol,
                "timestamp": datetime.now(),
                "price": price,
                "open": last_open,
                "high": last_high,
                "low": last_low,
                "close": last_close,
                "volume": last_volume,
                "change": float(change),
                "change_percent": float(change_pct),
                "source": "Yahoo Finance",
            }
        except Exception as exc:
            self.logger.error(f"Yahoo direct API failed for {symbol}: {exc}")
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

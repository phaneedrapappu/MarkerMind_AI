"""
Market Data Agent - Fetches and processes market data.
Primary source: NSE India API.
Fallback: yfinance (Yahoo Finance) when NSE is unreachable.
"""
import logging
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
        """Fetch basic quote data from Yahoo Finance (NS suffix for NSE stocks).

        Uses period='5d' so the last trading day is always available even on
        weekends and public holidays (period='1d' returns empty on non-trading days).
        """
        try:
            ticker_sym = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_sym)
            # Use 5d so weekend/holiday runs still get the last trading session
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
            row = hist.iloc[-1]
            # fast_info may throw a JSONDecodeError on weekends — fall back gracefully
            try:
                prev_close = ticker.fast_info.previous_close or row["Close"]
            except Exception:
                prev_close = row["Close"]
            change = row["Close"] - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            # ticker.info can also be slow/empty on weekends; use symbol as fallback
            try:
                company_name = ticker.info.get("longName", symbol)
            except Exception:
                company_name = symbol
            return {
                "symbol": symbol.upper(),
                "company_name": company_name,
                "timestamp": datetime.now(),
                "price": float(row["Close"]),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
                "change": float(change),
                "change_percent": float(change_pct),
                "source": "Yahoo Finance",
            }
        except Exception as exc:
            self.logger.error(f"yfinance fetch failed for {symbol}: {exc}")
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

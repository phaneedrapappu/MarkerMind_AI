"""
NSE Data Fetcher - Fetches data from NSE India
"""
import requests
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import time
from bs4 import BeautifulSoup


class NSEDataFetcher:
    """Fetches data from NSE (National Stock Exchange of India)"""
    
    def __init__(self, timeout: int = 10):
        """
        Initialize NSE Data Fetcher
        
        Args:
            timeout: Request timeout in seconds
        """
        self.base_url = "https://www.nseindia.com"
        self.timeout = timeout
        self.logger = logging.getLogger("MarketMindAI.NSEDataFetcher")
        self.session = requests.Session()
        self._cookies_fetched = False   # cache flag — only fetch once per session
        
        # NSE requires proper headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nseindia.com/',
            'Connection': 'keep-alive'
        }
        
    def _get_cookies(self):
        """Get cookies from NSE homepage — fetched only once per session."""
        if self._cookies_fetched:
            return self.session.cookies
        try:
            response = self.session.get(
                self.base_url,
                headers=self.headers,
                timeout=self.timeout
            )
            self._cookies_fetched = True
            return response.cookies
        except Exception as e:
            self.logger.warning(f"NSE cookie fetch failed: {e}")
            return None
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request to NSE
        
        Args:
            url: URL to fetch
            params: Query parameters
            
        Returns:
            JSON response or None
        """
        try:
            # Ensure cookies are loaded (cached after first call)
            self._get_cookies()
            
            response = self.session.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"Request failed with status code: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout for URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
    
    def get_stock_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time stock quote
        
        Args:
            symbol: Stock symbol (e.g., TCS, WIPRO)
            
        Returns:
            Stock data dictionary or None
        """
        url = f"{self.base_url}/api/quote-equity"
        params = {'symbol': symbol.upper()}
        
        self.logger.info(f"Fetching quote for {symbol}")
        data = self._make_request(url, params)
        
        if data and 'priceInfo' in data:
            try:
                price_info = data['priceInfo']
                metadata = data.get('metadata', {})
                
                return {
                    'symbol': symbol.upper(),
                    'company_name': metadata.get('companyName', ''),
                    'price': price_info.get('lastPrice', 0),
                    'open': price_info.get('open', 0),
                    'high': price_info.get('intraDayHighLow', {}).get('max', 0),
                    'low': price_info.get('intraDayHighLow', {}).get('min', 0),
                    'close': price_info.get('close', 0),
                    'volume': price_info.get('totalTradedVolume', 0),
                    'change': price_info.get('change', 0),
                    'change_percent': price_info.get('pChange', 0),
                    'timestamp': datetime.now(),
                    'source': 'NSE'
                }
            except Exception as e:
                self.logger.error(f"Error parsing stock quote: {e}")
                return None
        return None
    
    def get_bulk_deals(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get bulk deals data
        
        Args:
            date: Date in format DD-MM-YYYY (default: today)
            
        Returns:
            List of bulk deals
        """
        if not date:
            date = datetime.now().strftime("%d-%m-%Y")
        
        url = f"{self.base_url}/api/corporates-corporateActions"
        params = {'index': 'bulkDeals'}
        
        self.logger.info(f"Fetching bulk deals for {date}")
        data = self._make_request(url, params)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_block_deals(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get block deals data
        
        Args:
            date: Date in format DD-MM-YYYY (default: today)
            
        Returns:
            List of block deals
        """
        if not date:
            date = datetime.now().strftime("%d-%m-%Y")
        
        url = f"{self.base_url}/api/corporates-corporateActions"
        params = {'index': 'blockDeals'}
        
        self.logger.info(f"Fetching block deals for {date}")
        data = self._make_request(url, params)
        
        if data and isinstance(data, list):
            return data
        return []
    
    def get_fii_dii_data(self) -> Optional[Dict[str, Any]]:
        """
        Get FII/DII (Foreign and Domestic Institutional Investors) data
        
        Returns:
            FII/DII data dictionary or None
        """
        url = f"{self.base_url}/api/fiidiiTrading"
        
        self.logger.info("Fetching FII/DII data")
        data = self._make_request(url)
        
        return data
    
    def get_shareholding_pattern(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get shareholding pattern including promoter holdings
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Shareholding data or None
        """
        url = f"{self.base_url}/api/quote-equity"
        params = {'symbol': symbol.upper()}
        
        self.logger.info(f"Fetching shareholding pattern for {symbol}")
        data = self._make_request(url, params)
        
        if data and 'securityInfo' in data:
            return data.get('securityInfo', {})
        return None
    
    def close(self):
        """Close the session"""
        self.session.close()

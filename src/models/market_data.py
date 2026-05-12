"""
Data models for market data
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class TransactionType(Enum):
    """Types of market transactions"""
    BUY = "BUY"
    SELL = "SELL"
    BULK_DEAL = "BULK_DEAL"
    BLOCK_DEAL = "BLOCK_DEAL"
    PROMOTER_BUY = "PROMOTER_BUY"
    PROMOTER_SELL = "PROMOTER_SELL"
    FII_BUY = "FII_BUY"
    FII_SELL = "FII_SELL"
    DII_BUY = "DII_BUY"
    DII_SELL = "DII_SELL"


@dataclass
class StockData:
    """Basic stock data"""
    symbol: str
    company_name: str
    timestamp: datetime
    price: float
    open_price: float
    high: float
    low: float
    close_price: Optional[float]
    volume: int
    change: float
    change_percent: float
    source: str  # NSE or BSE
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'open_price': self.open_price,
            'high': self.high,
            'low': self.low,
            'close_price': self.close_price,
            'volume': self.volume,
            'change': self.change,
            'change_percent': self.change_percent,
            'source': self.source
        }


@dataclass
class BulkBlockDeal:
    """Bulk and Block deals data"""
    symbol: str
    date: datetime
    deal_type: str  # BULK or BLOCK
    client_name: str
    quantity: int
    price: float
    transaction_type: TransactionType
    source: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat(),
            'deal_type': self.deal_type,
            'client_name': self.client_name,
            'quantity': self.quantity,
            'price': self.price,
            'transaction_type': self.transaction_type.value,
            'source': self.source
        }


@dataclass
class InstitutionalActivity:
    """FII/DII activity data"""
    date: datetime
    institution_type: str  # FII or DII
    buy_value: float
    sell_value: float
    net_value: float
    symbol: Optional[str] = None  # If stock-specific, otherwise market-wide
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'date': self.date.isoformat(),
            'institution_type': self.institution_type,
            'buy_value': self.buy_value,
            'sell_value': self.sell_value,
            'net_value': self.net_value,
            'symbol': self.symbol
        }


@dataclass
class PromoterHolding:
    """Promoter holding and transaction data"""
    symbol: str
    quarter: str
    date: datetime
    promoter_holding_percent: float
    promoter_holding_change: Optional[float] = None
    transaction_type: Optional[TransactionType] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'symbol': self.symbol,
            'quarter': self.quarter,
            'date': self.date.isoformat(),
            'promoter_holding_percent': self.promoter_holding_percent,
            'promoter_holding_change': self.promoter_holding_change,
            'transaction_type': self.transaction_type.value if self.transaction_type else None
        }


@dataclass
class MarketDataSnapshot:
    """Complete market data snapshot for a stock"""
    stock_data: StockData
    bulk_block_deals: List[BulkBlockDeal] = field(default_factory=list)
    institutional_activity: List[InstitutionalActivity] = field(default_factory=list)
    promoter_holding: Optional[PromoterHolding] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'stock_data': self.stock_data.to_dict(),
            'bulk_block_deals': [deal.to_dict() for deal in self.bulk_block_deals],
            'institutional_activity': [ia.to_dict() for ia in self.institutional_activity],
            'promoter_holding': self.promoter_holding.to_dict() if self.promoter_holding else None
        }

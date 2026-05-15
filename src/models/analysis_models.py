"""
Analysis data models for AI-powered stock analysis
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum


class SignalType(Enum):
    """Trading signal types"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class RiskLevel(Enum):
    """Risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


@dataclass
class DailyTradingAnalysis:
    """Analysis of daily trading activity"""
    symbol: str
    date: datetime
    price_movement: str  # Description of price movement
    volume_analysis: str  # Volume vs average
    buyer_seller_balance: str  # Who is in control
    key_observations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat(),
            'price_movement': self.price_movement,
            'volume_analysis': self.volume_analysis,
            'buyer_seller_balance': self.buyer_seller_balance,
            'key_observations': self.key_observations
        }


@dataclass
class BulkBlockAnalysis:
    """Analysis of bulk and block deals"""
    symbol: str
    date: datetime
    total_deals: int
    significant_deals: List[str]  # Notable deals
    interpretation: str  # What these deals mean
    impact_assessment: str  # Bullish/Bearish/Neutral
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat(),
            'total_deals': self.total_deals,
            'significant_deals': self.significant_deals,
            'interpretation': self.interpretation,
            'impact_assessment': self.impact_assessment
        }


@dataclass
class InstitutionalAnalysis:
    """Analysis of FII/DII activity"""
    symbol: str
    date: datetime
    fii_sentiment: str  # Bullish/Bearish/Neutral
    dii_sentiment: str  # Bullish/Bearish/Neutral
    net_institutional_flow: float  # In crores
    interpretation: str  # What this means
    confidence_level: str  # High/Medium/Low
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat(),
            'fii_sentiment': self.fii_sentiment,
            'dii_sentiment': self.dii_sentiment,
            'net_institutional_flow': self.net_institutional_flow,
            'interpretation': self.interpretation,
            'confidence_level': self.confidence_level
        }


@dataclass
class PromoterAnalysis:
    """Analysis of promoter activity"""
    symbol: str
    date: datetime
    promoter_action: Optional[str]  # Buying/Selling/No Change
    holding_trend: Optional[str]  # Increasing/Decreasing/Stable
    significance: Optional[str]  # What this indicates
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'date': self.date.isoformat(),
            'promoter_action': self.promoter_action,
            'holding_trend': self.holding_trend,
            'significance': self.significance
        }


@dataclass
class AIAnalysisReport:
    """Complete AI-powered analysis report for a stock"""
    symbol: str
    company_name: str
    timestamp: datetime
    
    # Analysis components
    daily_trading: DailyTradingAnalysis
    bulk_block_analysis: Optional[BulkBlockAnalysis] = None
    institutional_analysis: Optional[InstitutionalAnalysis] = None
    promoter_analysis: Optional[PromoterAnalysis] = None
    
    # Overall assessment
    overall_sentiment: str = ""  # Bullish/Bearish/Neutral
    key_highlights: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    
    # Raw LLM response (for debugging)
    raw_llm_response: str = ""

    # Confidence directly from LLM (0-100).  None = not yet set.
    llm_confidence: Optional[float] = None
    # Real market metrics carried forward to signal generator
    price_change_pct: float = 0.0    # actual % price change from market data
    news_pos: int = 0                 # count of positive news articles
    news_neg: int = 0                 # count of negative news articles
    news_total: int = 0               # total news articles fetched
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'timestamp': self.timestamp.isoformat(),
            'daily_trading': self.daily_trading.to_dict(),
            'bulk_block_analysis': self.bulk_block_analysis.to_dict() if self.bulk_block_analysis else None,
            'institutional_analysis': self.institutional_analysis.to_dict() if self.institutional_analysis else None,
            'promoter_analysis': self.promoter_analysis.to_dict() if self.promoter_analysis else None,
            'overall_sentiment': self.overall_sentiment,
            'key_highlights': self.key_highlights,
            'concerns': self.concerns,
            'opportunities': self.opportunities
        }


@dataclass
class TradingSignal:
    """Trading signal with reasoning"""
    symbol: str
    company_name: str
    timestamp: datetime
    
    # Signal details
    signal: SignalType
    confidence: float  # 0-100
    risk_level: RiskLevel
    
    # Reasoning
    reasoning: str
    supporting_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    # Price targets (optional)
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Time horizon
    time_horizon: str = "Short-term (1-3 months)"
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'company_name': self.company_name,
            'timestamp': self.timestamp.isoformat(),
            'signal': self.signal.value,
            'confidence': self.confidence,
            'risk_level': self.risk_level.value,
            'reasoning': self.reasoning,
            'supporting_factors': self.supporting_factors,
            'risk_factors': self.risk_factors,
            'entry_price': self.entry_price,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'time_horizon': self.time_horizon
        }
    
    @property
    def signal_type(self) -> str:
        """Return a simplified BUY / SELL / HOLD string (used by email & report agents)."""
        mapping = {
            SignalType.STRONG_BUY: "BUY",
            SignalType.BUY: "BUY",
            SignalType.HOLD: "HOLD",
            SignalType.REDUCE_EXPOSURE: "SELL",
            SignalType.SELL: "SELL",
            SignalType.STRONG_SELL: "SELL",
        }
        return mapping.get(self.signal, "HOLD")

    @property
    def confidence_ratio(self) -> float:
        """Confidence as a 0-1 ratio (confidence field is 0-100)."""
        return min(self.confidence / 100.0, 1.0)

    @property
    def risk_level_str(self) -> str:
        """Risk level as plain string."""
        return self.risk_level.value if isinstance(self.risk_level, RiskLevel) else str(self.risk_level)

    def get_signal_emoji(self) -> str:
        """Get emoji for signal type"""
        emoji_map = {
            SignalType.STRONG_BUY: "🚀",
            SignalType.BUY: "✅",
            SignalType.HOLD: "⏸️",
            SignalType.REDUCE_EXPOSURE: "⚠️",
            SignalType.SELL: "⬇️",
            SignalType.STRONG_SELL: "🔴"
        }
        return emoji_map.get(self.signal, "❓")
    
    def get_risk_emoji(self) -> str:
        """Get emoji for risk level"""
        emoji_map = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.HIGH: "🟠",
            RiskLevel.VERY_HIGH: "🔴"
        }
        return emoji_map.get(self.risk_level, "⚪")

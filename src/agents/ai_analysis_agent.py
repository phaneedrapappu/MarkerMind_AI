"""
AI Analysis Agent - Uses GPT to analyze market data
"""
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from ..agents.base_agent import BaseAgent
from ..models.market_data import MarketDataSnapshot
from ..models.analysis_models import (
    AIAnalysisReport, DailyTradingAnalysis, BulkBlockAnalysis,
    InstitutionalAnalysis, PromoterAnalysis
)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


class AIAnalysisAgent(BaseAgent):
    """
    AI Analysis Agent - Analyzes market data using GPT
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AI Analysis Agent
        
        Args:
            config: Configuration dictionary
        """
        super().__init__("AIAnalysisAgent", config)
        self.api_key = config.get('api_key') or os.getenv('OPENAI_API_KEY')
        self.model = config.get('model', 'gpt-4o-mini')  # Cost-effective model
        self.client: Optional[OpenAI] = None
        self.analysis_results: List[AIAnalysisReport] = []
        
    def initialize(self) -> bool:
        """
        Initialize the agent
        
        Returns:
            True if successful
        """
        try:
            self.logger.info("Initializing AI Analysis Agent")
            
            if not OPENAI_AVAILABLE:
                self.logger.error("OpenAI library not installed. Run: pip install openai")
                return False
            
            if not self.api_key:
                self.logger.error("OpenAI API key not found. Set OPENAI_API_KEY environment variable or in config.")
                return False
            
            # Initialize OpenAI client
            self.client = OpenAI(api_key=self.api_key)
            
            self.logger.info(f"AI Analysis Agent initialized with model: {self.model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI Analysis Agent: {e}")
            return False
    
    def execute(self, market_data: List[MarketDataSnapshot]) -> List[AIAnalysisReport]:
        """
        Execute the agent - analyze market data using GPT
        
        Args:
            market_data: List of MarketDataSnapshot objects from Market Data Agent
            
        Returns:
            List of AIAnalysisReport objects
        """
        self.log_execution()
        self.logger.info(f"Analyzing {len(market_data)} stock(s) using GPT")
        
        self.analysis_results = []
        
        for snapshot in market_data:
            try:
                self.logger.info(f"Analyzing {snapshot.stock_data.symbol}")
                analysis = self._analyze_snapshot(snapshot)
                
                if analysis:
                    self.analysis_results.append(analysis)
                    self._print_analysis_summary(analysis)
                else:
                    self.logger.warning(f"No analysis generated for {snapshot.stock_data.symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error analyzing {snapshot.stock_data.symbol}: {e}")
        
        return self.analysis_results
    
    def _analyze_snapshot(self, snapshot: MarketDataSnapshot) -> Optional[AIAnalysisReport]:
        """
        Analyze a single stock snapshot using GPT
        
        Args:
            snapshot: MarketDataSnapshot object
            
        Returns:
            AIAnalysisReport or None
        """
        if not self.client:
            self.logger.error("OpenAI client not initialized")
            return None
        
        # Build prompt for GPT
        prompt = self._build_analysis_prompt(snapshot)
        
        try:
            # Call GPT API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst specializing in Indian stock markets. Analyze market data and provide clear, actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more focused analysis
                max_tokens=1500
            )
            
            llm_response = response.choices[0].message.content
            
            # Parse LLM response into structured analysis
            analysis = self._parse_llm_response(snapshot, llm_response)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error calling GPT API: {e}")
            return None
    
    def _build_analysis_prompt(self, snapshot: MarketDataSnapshot) -> str:
        """
        Build detailed prompt for GPT analysis
        
        Args:
            snapshot: MarketDataSnapshot
            
        Returns:
            Formatted prompt string
        """
        stock = snapshot.stock_data
        
        prompt = f"""Analyze this Indian stock market data for {stock.company_name} ({stock.symbol}):

📊 STOCK DATA:
- Current Price: ₹{stock.price:,.2f}
- Change: ₹{stock.change:+.2f} ({stock.change_percent:+.2f}%)
- Open: ₹{stock.open_price:,.2f} | High: ₹{stock.high:,.2f} | Low: ₹{stock.low:,.2f}
- Volume: {stock.volume:,} shares
- Date: {stock.timestamp.strftime('%Y-%m-%d')}

"""
        
        # Add bulk/block deals if available
        if snapshot.bulk_block_deals:
            prompt += f"""🔔 BULK/BLOCK DEALS ({len(snapshot.bulk_block_deals)} deals):
"""
            for deal in snapshot.bulk_block_deals[:5]:  # Limit to 5 deals
                prompt += f"- {deal.deal_type}: {deal.client_name} | Qty: {deal.quantity:,} @ ₹{deal.price:.2f}\n"
            prompt += "\n"
        
        # Add institutional activity if available
        if snapshot.institutional_activity:
            prompt += "🏦 INSTITUTIONAL ACTIVITY:\n"
            for activity in snapshot.institutional_activity:
                prompt += f"- {activity.institution_type}: Buy ₹{activity.buy_value:,.0f}Cr | Sell ₹{activity.sell_value:,.0f}Cr | Net ₹{activity.net_value:+,.0f}Cr\n"
            prompt += "\n"
        
        prompt += """
Please provide a structured analysis in the following format:

1. DAILY TRADING ANALYSIS:
   - Price movement interpretation
   - Volume analysis (compared to typical volumes)
   - Buyer/seller balance

2. BULK/BLOCK DEALS ANALYSIS (if any):
   - Number of shares traded: [exact number]
   - Significance of these deals
   - Impact assessment (Bullish/Bearish/Neutral)

3. FII/DII ACTIVITY ANALYSIS (if available):
   - FII sentiment (Bullish/Bearish/Neutral)
   - DII sentiment (Bullish/Bearish/Neutral)
   - Overall interpretation

4. OVERALL ASSESSMENT:
   - Overall sentiment (Bullish/Bearish/Neutral)
   - Key highlights (3-4 points)
   - Concerns (if any)
   - Opportunities (if any)

Keep analysis concise and actionable. Focus on what the data tells us about market sentiment and potential moves.
"""
        
        return prompt
    
    def _parse_llm_response(self, snapshot: MarketDataSnapshot, llm_response: str) -> AIAnalysisReport:
        """
        Parse LLM response into structured analysis
        
        Args:
            snapshot: Original market data snapshot
            llm_response: Raw LLM response text
            
        Returns:
            AIAnalysisReport
        """
        stock = snapshot.stock_data
        
        # Create daily trading analysis
        daily_trading = DailyTradingAnalysis(
            symbol=stock.symbol,
            date=stock.timestamp,
            price_movement=f"{stock.change_percent:+.2f}% move",
            volume_analysis=f"{stock.volume:,} shares traded",
            buyer_seller_balance="Analyzing..."
        )
        
        # Create bulk/block analysis if deals exist
        bulk_block_analysis = None
        if snapshot.bulk_block_deals:
            total_shares = sum(deal.quantity for deal in snapshot.bulk_block_deals)
            significant_deals = [
                f"{deal.client_name}: {deal.quantity:,} shares @ ₹{deal.price:.2f}"
                for deal in snapshot.bulk_block_deals[:3]
            ]
            
            bulk_block_analysis = BulkBlockAnalysis(
                symbol=stock.symbol,
                date=stock.timestamp,
                total_deals=len(snapshot.bulk_block_deals),
                significant_deals=significant_deals,
                interpretation=f"Total {total_shares:,} shares in bulk/block deals",
                impact_assessment="Analyzing..."
            )
        
        # Create institutional analysis if data exists
        institutional_analysis = None
        if snapshot.institutional_activity:
            fii_data = next((a for a in snapshot.institutional_activity if a.institution_type == 'FII'), None)
            dii_data = next((a for a in snapshot.institutional_activity if a.institution_type == 'DII'), None)
            
            if fii_data or dii_data:
                net_flow = (fii_data.net_value if fii_data else 0) + (dii_data.net_value if dii_data else 0)
                
                institutional_analysis = InstitutionalAnalysis(
                    symbol=stock.symbol,
                    date=stock.timestamp,
                    fii_sentiment="Analyzing..." if fii_data else "N/A",
                    dii_sentiment="Analyzing..." if dii_data else "N/A",
                    net_institutional_flow=net_flow,
                    interpretation="Analyzing institutional flows...",
                    confidence_level="Medium"
                )
        
        # Extract key insights from LLM response
        key_highlights = []
        concerns = []
        overall_sentiment = "Neutral"
        
        # Simple parsing - look for sentiment indicators
        response_lower = llm_response.lower()
        if "bullish" in response_lower or "positive" in response_lower or "buy" in response_lower:
            overall_sentiment = "Bullish"
        elif "bearish" in response_lower or "negative" in response_lower or "sell" in response_lower:
            overall_sentiment = "Bearish"
        
        # Create analysis report
        analysis = AIAnalysisReport(
            symbol=stock.symbol,
            company_name=stock.company_name,
            timestamp=datetime.now(),
            daily_trading=daily_trading,
            bulk_block_analysis=bulk_block_analysis,
            institutional_analysis=institutional_analysis,
            overall_sentiment=overall_sentiment,
            key_highlights=key_highlights,
            concerns=concerns,
            raw_llm_response=llm_response
        )
        
        return analysis
    
    def _print_analysis_summary(self, analysis: AIAnalysisReport):
        """Print analysis summary"""
        print(f"\n{'='*70}")
        print(f"🤖 AI ANALYSIS: {analysis.company_name} ({analysis.symbol})")
        print(f"{'='*70}")
        print(f"\n📊 Overall Sentiment: {analysis.overall_sentiment}")
        print(f"\n💡 GPT Analysis:")
        print(analysis.raw_llm_response)
        print(f"{'='*70}\n")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up AI Analysis Agent")
        self.client = None
    
    def get_analysis_results(self) -> List[AIAnalysisReport]:
        """Get the analysis results"""
        return self.analysis_results

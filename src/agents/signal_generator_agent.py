"""
Signal Generator Agent - Generates trading signals from AI analysis
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.base_agent import BaseAgent
from ..models.analysis_models import (
    AIAnalysisReport, TradingSignal, SignalType, RiskLevel
)


class SignalGeneratorAgent(BaseAgent):
    """
    Signal Generator Agent - Generates BUY/HOLD/SELL signals
    from AI analysis reports
    """
    
    def __init__(self, config: Dict[str, Any], db_manager=None):
        super().__init__("SignalGeneratorAgent", config)
        self.risk_tolerance = config.get('risk_tolerance', 'medium')
        self.signals: List[TradingSignal] = []
        self.db = db_manager
        
    def initialize(self) -> bool:
        """
        Initialize the agent
        
        Returns:
            True if successful
        """
        try:
            self.logger.info("Initializing Signal Generator Agent")
            self.logger.info(f"Risk tolerance: {self.risk_tolerance}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Signal Generator Agent: {e}")
            return False
    
    def execute(self, analysis_reports: List[AIAnalysisReport]) -> List[TradingSignal]:
        """
        Execute the agent - generate signals from analysis reports
        
        Args:
            analysis_reports: List of AIAnalysisReport objects from AI Analysis Agent
            
        Returns:
            List of TradingSignal objects
        """
        self.log_execution()
        self.logger.info(f"Generating signals for {len(analysis_reports)} stock(s)")
        
        self.signals = []
        
        for analysis in analysis_reports:
            try:
                self.logger.info(f"Generating signal for {analysis.symbol}")
                signal = self._generate_signal(analysis)
                
                if signal:
                    self.signals.append(signal)
                    self._print_signal(signal)
                    # Persist
                    if self.db:
                        try:
                            import json as _json
                            self.db.save_trading_signal({
                                "symbol": signal.symbol,
                                "signal_date": signal.timestamp,
                                "signal_type": signal.signal_type,
                                "confidence": signal.confidence_ratio,
                                "risk_level": signal.risk_level_str,
                                "target_price": signal.target_price,
                                "stop_loss": signal.stop_loss,
                                "supporting_factors": _json.dumps(signal.supporting_factors),
                                "risk_factors": _json.dumps(signal.risk_factors),
                                "current_price": signal.entry_price,
                            })
                        except Exception as db_exc:
                            self.logger.warning(f"DB persist failed for signal {signal.symbol}: {db_exc}")
                else:
                    self.logger.warning(f"No signal generated for {analysis.symbol}")
                    
            except Exception as e:
                self.logger.error(f"Error generating signal for {analysis.symbol}: {e}")
        
        return self.signals
    
    def _generate_signal(self, analysis: AIAnalysisReport) -> Optional[TradingSignal]:
        """
        Generate trading signal from analysis
        
        Args:
            analysis: AIAnalysisReport
            
        Returns:
            TradingSignal or None
        """
        # Score various factors
        scores = {
            'price_movement': 0,
            'volume': 0,
            'institutional': 0,
            'bulk_deals': 0,
            'overall_sentiment': 0
        }
        
        supporting_factors = []
        risk_factors = []
        
        # 1. Analyze overall sentiment from LLM
        response_lower = analysis.raw_llm_response.lower()
        
        if "strong buy" in response_lower or "strongly bullish" in response_lower:
            scores['overall_sentiment'] = 3
            supporting_factors.append("Strong bullish sentiment from AI analysis")
        elif "buy" in response_lower or "bullish" in response_lower or "positive" in response_lower:
            scores['overall_sentiment'] = 2
            supporting_factors.append("Bullish sentiment indicated")
        elif "sell" in response_lower or "bearish" in response_lower or "negative" in response_lower:
            scores['overall_sentiment'] = -2
            risk_factors.append("Bearish sentiment indicated")
        elif "strong sell" in response_lower or "strongly bearish" in response_lower:
            scores['overall_sentiment'] = -3
            risk_factors.append("Strong bearish sentiment")
        else:
            scores['overall_sentiment'] = 0
        
        # 2. Institutional activity analysis
        if analysis.institutional_analysis:
            inst = analysis.institutional_analysis
            if inst.net_institutional_flow > 100:  # Net buying > 100 Cr
                scores['institutional'] = 2
                supporting_factors.append(f"Strong institutional buying (₹{inst.net_institutional_flow:,.0f}Cr)")
            elif inst.net_institutional_flow > 0:
                scores['institutional'] = 1
                supporting_factors.append(f"Positive institutional flow (₹{inst.net_institutional_flow:,.0f}Cr)")
            elif inst.net_institutional_flow < -100:
                scores['institutional'] = -2
                risk_factors.append(f"Heavy institutional selling (₹{inst.net_institutional_flow:,.0f}Cr)")
            elif inst.net_institutional_flow < 0:
                scores['institutional'] = -1
                risk_factors.append(f"Institutional outflow (₹{inst.net_institutional_flow:,.0f}Cr)")
        
        # 3. Bulk/Block deals analysis
        if analysis.bulk_block_analysis:
            bulk = analysis.bulk_block_analysis
            if bulk.total_deals > 0:
                if "bullish" in bulk.impact_assessment.lower() or "positive" in bulk.impact_assessment.lower():
                    scores['bulk_deals'] = 1
                    supporting_factors.append(f"{bulk.total_deals} bulk/block deal(s) - positive signal")
                elif "bearish" in bulk.impact_assessment.lower() or "negative" in bulk.impact_assessment.lower():
                    scores['bulk_deals'] = -1
                    risk_factors.append(f"{bulk.total_deals} bulk/block deal(s) - negative signal")
        
        # 4. Volume and price movement from LLM analysis
        if "strong volume" in response_lower or "high volume" in response_lower or "volume spike" in response_lower:
            scores['volume'] = 1
            supporting_factors.append("Above-average trading volume")
        
        if "strong upward" in response_lower or "significant gain" in response_lower:
            scores['price_movement'] = 1
        elif "strong downward" in response_lower or "significant loss" in response_lower:
            scores['price_movement'] = -1
        
        # Calculate total score
        total_score = sum(scores.values())
        
        # Determine signal type and base confidence from score
        signal_type, _, risk_level = self._score_to_signal(total_score, scores)

        # Compute real, data-driven confidence
        confidence = self._compute_real_confidence(analysis, signal_type, total_score)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(analysis, total_score, scores)
        
        # Create trading signal
        signal = TradingSignal(
            symbol=analysis.symbol,
            company_name=analysis.company_name,
            timestamp=datetime.now(),
            signal=signal_type,
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning,
            supporting_factors=supporting_factors if supporting_factors else ["Analysis in progress"],
            risk_factors=risk_factors if risk_factors else ["Monitor market conditions"]
        )
        
        return signal
    
    def _score_to_signal(self, total_score: int, scores: Dict[str, int]) -> tuple:
        """
        Convert score to (SignalType, placeholder_confidence, RiskLevel).
        Confidence is now computed by _compute_real_confidence — this method
        only determines signal direction and risk level.
        """
        if total_score >= 5:
            return SignalType.STRONG_BUY, 0, RiskLevel.MEDIUM
        elif total_score >= 3:
            return SignalType.BUY, 0, RiskLevel.MEDIUM
        elif total_score >= 1:
            return SignalType.BUY, 0, RiskLevel.MEDIUM
        elif total_score <= -5:
            return SignalType.STRONG_SELL, 0, RiskLevel.HIGH
        elif total_score <= -3:
            return SignalType.SELL, 0, RiskLevel.HIGH
        elif total_score <= -1:
            return SignalType.REDUCE_EXPOSURE, 0, RiskLevel.MEDIUM
        else:
            return SignalType.HOLD, 0, RiskLevel.LOW

    def _compute_real_confidence(self, analysis: AIAnalysisReport,
                                  signal_type: SignalType,
                                  total_score: int) -> float:
        """
        Compute a data-driven confidence score (0-100).
        Sources (all independent per stock):
          1. Gemini's own confidence integer (primary — most accurate)
          2. Actual price change %   — big moves signal stronger conviction
          3. News sentiment skew     — majority pos/neg = more certainty
          4. LLM text strength clues — "strongly bullish/bearish" keywords
          5. Score magnitude fallback — only when Gemini gave no confidence
        """
        import re as _re

        # ── 1. Base: Gemini confidence or score-derived ─────────────────────
        if analysis.llm_confidence is not None:
            base = float(analysis.llm_confidence)
        else:
            score_abs = abs(total_score)
            if score_abs >= 5:   base = 72.0
            elif score_abs >= 3: base = 62.0
            elif score_abs >= 1: base = 52.0
            else:                base = 42.0

        # ── 2. Real price change % (parse from daily_trading if not direct) ─
        pct = analysis.price_change_pct
        if pct == 0.0 and analysis.daily_trading:
            m = _re.search(r"([+-]?\d+\.?\d*)\s*%",
                           analysis.daily_trading.price_movement or "")
            if m:
                try: pct = float(m.group(1))
                except ValueError: pass
        price_factor = min(abs(pct) * 1.8, 12.0)   # ±0..12 pts

        # ── 3. News sentiment consensus (±0..8 pts) ─────────────────────────
        news_factor = 0.0
        if analysis.news_total > 0:
            skew = max(analysis.news_pos, analysis.news_neg) / analysis.news_total
            news_factor = skew * 8.0

        # ── 4. LLM text strength bonus (±0..6 pts) ──────────────────────────
        text_bonus = 0.0
        if analysis.raw_llm_response:
            lower = analysis.raw_llm_response.lower()
            pos_hits = sum(1 for w in ["strongly bullish", "strong buy", "high conviction",
                                        "significantly outperform", "breakout", "robust"]
                           if w in lower)
            neg_hits = sum(1 for w in ["strongly bearish", "strong sell", "high risk",
                                        "significant downside", "breakdown", "caution"]
                           if w in lower)
            text_bonus = max(min((pos_hits - neg_hits) * 2.0, 6.0), -6.0)

        # ── 5. HOLD penalty — inherently uncertain ──────────────────────────
        hold_penalty = -10.0 if signal_type == SignalType.HOLD else 0.0

        raw = base + price_factor + news_factor + text_bonus + hold_penalty
        return round(min(max(raw, 28.0), 97.0), 1)
    
    def _generate_reasoning(self, analysis: AIAnalysisReport, total_score: int, scores: Dict[str, int]) -> str:
        """
        Generate human-readable reasoning for the signal
        
        Args:
            analysis: AIAnalysisReport
            total_score: Total score
            scores: Individual scores
            
        Returns:
            Reasoning string
        """
        reasons = []
        
        # Overall sentiment
        if scores['overall_sentiment'] > 0:
            reasons.append("Positive market sentiment")
        elif scores['overall_sentiment'] < 0:
            reasons.append("Negative market sentiment")
        
        # Institutional activity
        if analysis.institutional_analysis and scores['institutional'] != 0:
            if scores['institutional'] > 0:
                reasons.append("Strong institutional buying support")
            else:
                reasons.append("Institutional selling pressure")
        
        # Bulk deals
        if analysis.bulk_block_analysis and scores['bulk_deals'] != 0:
            if scores['bulk_deals'] > 0:
                reasons.append("Positive bulk/block deal activity")
            else:
                reasons.append("Concerning bulk/block deal patterns")
        
        # Combine into reasoning
        if reasons:
            reasoning = " | ".join(reasons)
        else:
            reasoning = "Mixed signals - monitoring recommended"
        
        return reasoning
    
    def _print_signal(self, signal: TradingSignal):
        """Print trading signal in a beautiful format"""
        print(f"\n{'='*70}")
        print(f"🎯 TRADING SIGNAL: {signal.company_name} ({signal.symbol})")
        print(f"{'='*70}")
        print(f"\n{signal.get_signal_emoji()} Signal: {signal.signal.value}")
        print(f"📊 Confidence: {signal.confidence:.0f}%")
        print(f"{signal.get_risk_emoji()} Risk Level: {signal.risk_level.value}")
        print(f"\n💡 Reasoning: {signal.reasoning}")
        
        if signal.supporting_factors:
            print(f"\n✅ Supporting Factors:")
            for factor in signal.supporting_factors:
                print(f"   • {factor}")
        
        if signal.risk_factors:
            print(f"\n⚠️  Risk Factors:")
            for factor in signal.risk_factors:
                print(f"   • {factor}")
        
        print(f"\n⏰ Time Horizon: {signal.time_horizon}")
        print(f"{'='*70}\n")
    
    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up Signal Generator Agent")
    
    def get_signals(self) -> List[TradingSignal]:
        """Get the generated signals"""
        return self.signals

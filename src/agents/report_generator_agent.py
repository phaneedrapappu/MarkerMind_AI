"""
Report Generator Agent - Creates matplotlib charts and PDF/PNG reports
for each stock analysis cycle.  Charts are attached to emails.
"""
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")           # Non-interactive backend – safe in server/CLI mode
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import numpy as np

from .base_agent import BaseAgent
from ..database.db_manager import DatabaseManager

logger = logging.getLogger("MarketMindAI.ReportGeneratorAgent")

REPORTS_DIR = Path("data/reports")


class ReportGeneratorAgent(BaseAgent):
    """
    Generates graphical reports for each stock and returns file paths
    so they can be attached to emails.
    """

    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        super().__init__("ReportGeneratorAgent", config)
        self.db = db_manager
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> bool:
        try:
            logger.info("Report Generator Agent initialised")
            return True
        except Exception as exc:
            logger.error(f"Report Generator init failed: {exc}")
            return False

    def cleanup(self):
        """Cleanup resources"""
        self.logger.info("ReportGeneratorAgent cleanup")

    # ── Public interface ───────────────────────────────────────────────────────

    def execute(
        self,
        market_data: List[Any],
        analysis_reports: List[Any],
        signals: List[Any],
        news: List[Dict],
    ) -> Dict[str, List[str]]:
        """
        Build per-stock report images.

        Returns:
            {symbol: [list of absolute file paths to PNG images]}
        """
        self.log_execution()
        result: Dict[str, List[str]] = {}

        for snapshot in market_data:
            symbol = snapshot.stock_data.symbol
            logger.info(f"Generating report charts for {symbol} …")

            analysis = next(
                (a for a in analysis_reports if a.symbol == symbol), None
            )
            signal = next(
                (s for s in signals if s.symbol == symbol), None
            )
            stock_news = [n for n in news if n.get("symbol") == symbol][: 5]

            paths: List[str] = []

            # 1. Price / volume chart
            path = self._price_volume_chart(snapshot, signal)
            if path:
                paths.append(path)

            # 2. Signal summary chart
            path = self._signal_summary_chart(symbol, signal, analysis)
            if path:
                paths.append(path)

            # 3. News sentiment chart
            path = self._news_sentiment_chart(symbol, stock_news)
            if path:
                paths.append(path)

            # 4. Historical signals chart (from DB)
            path = self._historical_signals_chart(symbol)
            if path:
                paths.append(path)

            result[symbol] = paths
            logger.info(f"  → {len(paths)} chart(s) generated for {symbol}")

        return result

    # ── Chart builders ─────────────────────────────────────────────────────────

    def _price_volume_chart(self, snapshot: Any, signal: Optional[Any]) -> Optional[str]:
        """Price line chart with history + signal annotation + 52w high/low band."""
        symbol = snapshot.stock_data.symbol
        history = self.db.get_recent_stock_data(symbol, limit=30)
        stock = snapshot.stock_data

        fig, axes = plt.subplots(2, 1, figsize=(11, 6),
                                 gridspec_kw={"height_ratios": [3, 1]})
        fig.patch.set_facecolor("#1a1a2e")
        for ax in axes:
            ax.set_facecolor("#16213e")

        ax1, ax2 = axes
        title_color = "#38bdf8"

        if len(history) >= 2:
            dates  = [datetime.fromisoformat(r["timestamp"]) for r in reversed(history)]
            prices = [r["price"] for r in reversed(history)]
            vols   = [r.get("volume", 0) or 0 for r in reversed(history)]

            trend_color = "#22c55e" if prices[-1] >= prices[0] else "#ef4444"
            ax1.plot(dates, prices, color=trend_color, linewidth=2.2, zorder=3)
            ax1.fill_between(dates, prices, min(prices) * 0.995,
                             alpha=0.18, color=trend_color)

            # 52w high/low bands if available
            h52 = getattr(stock, "week_52_high", None)
            l52 = getattr(stock, "week_52_low",  None)
            if h52 and l52:
                ax1.axhline(h52, color="#f59e0b", linewidth=1, linestyle="--",
                            alpha=0.6, label=f"52w H ₹{h52:,.0f}")
                ax1.axhline(l52, color="#a78bfa", linewidth=1, linestyle="--",
                            alpha=0.6, label=f"52w L ₹{l52:,.0f}")
                ax1.legend(fontsize=9, facecolor="#1a1a2e", labelcolor="white",
                           framealpha=0.7, loc="upper left")

            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            fig.autofmt_xdate(rotation=30)
            bar_colors = [trend_color] * len(dates)
            ax2.bar(dates, vols, color=bar_colors, alpha=0.6, width=0.8)
        else:
            # Single point: show OHLCV as annotated bars with distinct colours
            labels = ["Open", "High", "Low", "Close"]
            vals   = [stock.open_price, stock.high, stock.low, stock.price]
            clrs   = ["#38bdf8", "#22c55e", "#ef4444", "#f59e0b"]
            bars   = ax1.bar(labels, vals, color=clrs, alpha=0.85, width=0.5)
            for bar, val in zip(bars, vals):
                ax1.text(bar.get_x() + bar.get_width() / 2,
                         bar.get_height() + max(vals) * 0.005,
                         f"₹{val:,.1f}", ha="center", va="bottom",
                         fontsize=9, fontweight="bold", color="white")
            ax2.bar(["Volume"], [stock.volume], color="#38bdf8", alpha=0.8)
            ax2.text(0, stock.volume, f"{stock.volume:,}",
                     ha="center", va="bottom", fontsize=9, color="white")

        ax1.set_ylabel("Price (₹)", color="white", fontsize=10)
        ax2.set_ylabel("Volume", color="white", fontsize=10)
        for ax in axes:
            ax.tick_params(colors="white")
            ax.spines[:].set_edgecolor("#334155")
            ax.grid(True, alpha=0.15, color="white")

        chg_color = "#22c55e" if stock.change_percent >= 0 else "#ef4444"
        fig.suptitle(
            f"{stock.company_name} ({symbol})  ·  "
            f"₹{stock.price:,.2f}  "
            f"{'▲' if stock.change_percent >= 0 else '▼'}{abs(stock.change_percent):.2f}%",
            fontsize=13, fontweight="bold", color=title_color
        )
        if signal:
            sig_clr = {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#f59e0b"}.get(
                signal.signal_type, "white")
            ax1.set_title(
                f"Signal: {signal.signal_type}  ·  "
                f"Confidence: {signal.confidence_ratio:.0%}  ·  "
                f"Risk: {signal.risk_level_str}",
                fontsize=9, color=sig_clr, pad=4
            )

        plt.tight_layout()
        path = str(REPORTS_DIR / f"{symbol}_price_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return path

    def _signal_summary_chart(
        self, symbol: str, signal: Optional[Any], analysis: Optional[Any]
    ) -> Optional[str]:
        """Per-stock summary: AI highlights text + confidence gauge + key metrics."""
        fig = plt.figure(figsize=(11, 5), facecolor="#1a1a2e")
        gs  = gridspec.GridSpec(1, 3, figure=fig, wspace=0.35)
        fig.suptitle(f"{symbol} — AI Signal Summary", fontsize=13,
                     fontweight="bold", color="#38bdf8")

        # ── Left: Confidence gauge ──────────────────────────────────────────
        ax_g = fig.add_subplot(gs[0])
        ax_g.set_facecolor("#16213e")
        if signal:
            conf = signal.confidence_ratio
            sig_clr = {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#f59e0b"}.get(
                signal.signal_type, "#94a3b8")
            # donut-style gauge using a wedge
            theta = conf * 360
            ax_g.pie([theta, 360 - theta],
                     colors=[sig_clr, "#1e293b"],
                     startangle=90, counterclock=False,
                     wedgeprops={"width": 0.38, "edgecolor": "#1a1a2e"})
            ax_g.text(0, 0, f"{signal.signal_type}\n{conf:.0%}",
                      ha="center", va="center", fontsize=16,
                      fontweight="bold", color=sig_clr)
        else:
            ax_g.text(0.5, 0.5, "No\nSignal", ha="center", va="center",
                      color="#94a3b8", fontsize=14, transform=ax_g.transAxes)
        ax_g.set_title("Confidence", color="white", fontsize=10, pad=6)

        # ── Middle: AI Key Highlights (stock-specific text) ─────────────────
        ax_t = fig.add_subplot(gs[1])
        ax_t.set_facecolor("#16213e")
        ax_t.axis("off")
        ax_t.set_title("AI Highlights", color="white", fontsize=10, pad=6)
        lines = []
        if analysis:
            for i, h in enumerate((analysis.key_highlights or [])[:4], 1):
                lines.append(f"✔  {h[:55]}")
            if analysis.concerns:
                lines.append("")
                for c in (analysis.concerns or [])[:2]:
                    lines.append(f"✘  {c[:55]}")
        if not lines:
            lines = ["No AI highlights yet.", "Run the pipeline to", "generate analysis."]
        ax_t.text(0.04, 0.95, "\n".join(lines), transform=ax_t.transAxes,
                  va="top", ha="left", fontsize=9, color="#cbd5e1",
                  linespacing=1.7,
                  bbox=dict(facecolor="#0f172a", alpha=0.6, boxstyle="round,pad=0.5"))

        # ── Right: Supporting vs Risk factor counts ──────────────────────────
        ax_b = fig.add_subplot(gs[2])
        ax_b.set_facecolor("#16213e")
        ax_b.set_title("Signal Factors", color="white", fontsize=10, pad=6)
        if signal:
            sup = len(signal.supporting_factors)
            risk = len(signal.risk_factors)
            bars = ax_b.barh(["Supporting", "Risk"], [sup, risk],
                             color=["#22c55e", "#ef4444"], alpha=0.85, height=0.4)
            for bar, val in zip(bars, [sup, risk]):
                ax_b.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                          str(val), va="center", color="white", fontweight="bold")
            ax_b.set_xlim(0, max(sup, risk, 3) + 1)
            ax_b.tick_params(colors="white")
        else:
            ax_b.text(0.5, 0.5, "No signal", ha="center", va="center",
                      color="#94a3b8", transform=ax_b.transAxes)
        ax_b.spines[:].set_edgecolor("#334155")
        ax_b.grid(True, alpha=0.15, color="white", axis="x")

        path = str(REPORTS_DIR / f"{symbol}_summary_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return path

    def _news_sentiment_chart(self, symbol: str, news_list: List[Dict]) -> Optional[str]:
        """Horizontal bar + headline list — stock-specific news breakdown."""
        if not news_list:
            return None

        from collections import Counter
        counts = Counter(n.get("sentiment", "NEUTRAL") for n in news_list)

        fig, (ax_bar, ax_txt) = plt.subplots(
            1, 2, figsize=(11, max(3.5, 1 + len(news_list) * 0.55)),
            gridspec_kw={"width_ratios": [1, 2]},
            facecolor="#1a1a2e"
        )
        fig.suptitle(f"{symbol} — News Sentiment ({len(news_list)} articles)",
                     fontsize=12, fontweight="bold", color="#38bdf8")

        # Left: horizontal bars
        ax_bar.set_facecolor("#16213e")
        sent_order  = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
        sent_colors = {"POSITIVE": "#22c55e", "NEUTRAL": "#94a3b8", "NEGATIVE": "#ef4444"}
        vals   = [counts.get(s, 0) for s in sent_order]
        clrs   = [sent_colors[s] for s in sent_order]
        bars   = ax_bar.barh(sent_order, vals, color=clrs, alpha=0.85, height=0.45)
        for bar, val in zip(bars, vals):
            if val:
                ax_bar.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                            str(val), va="center", color="white", fontweight="bold")
        ax_bar.set_xlim(0, max(vals) + 1.5)
        ax_bar.tick_params(colors="white")
        ax_bar.spines[:].set_edgecolor("#334155")
        ax_bar.set_title("Breakdown", color="white", fontsize=10)

        # Right: top headlines
        ax_txt.set_facecolor("#16213e")
        ax_txt.axis("off")
        ax_txt.set_title("Top Headlines", color="white", fontsize=10)
        lines = []
        for n in news_list[:6]:
            sent  = n.get("sentiment", "NEUTRAL")
            icon  = {"POSITIVE": "▲", "NEGATIVE": "▼", "NEUTRAL": "–"}.get(sent, "–")
            clr   = sent_colors.get(sent, "#94a3b8")
            title = (n.get("title") or "")[:65]
            lines.append((f"{icon} {title}", clr))

        y = 0.97
        for text, color in lines:
            ax_txt.text(0.02, y, text, transform=ax_txt.transAxes,
                        va="top", ha="left", fontsize=8.5, color=color,
                        wrap=True)
            y -= 0.155

        path = str(REPORTS_DIR / f"{symbol}_news_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return path

    def _historical_signals_chart(self, symbol: str) -> Optional[str]:
        """Timeline of historical signals with confidence dots per stock."""
        history = self.db.get_signals_for_symbol(symbol, limit=20)
        if not history:
            return None

        fig, (ax_count, ax_timeline) = plt.subplots(
            1, 2, figsize=(11, 4), facecolor="#1a1a2e",
            gridspec_kw={"width_ratios": [1, 2]}
        )
        fig.suptitle(f"{symbol} — Signal History (last {len(history)})",
                     fontsize=12, fontweight="bold", color="#38bdf8")

        from collections import Counter
        counts   = Counter(r["signal_type"] for r in history)
        sig_clrs = {"BUY": "#22c55e", "SELL": "#ef4444", "HOLD": "#f59e0b"}

        # Left: counts
        ax_count.set_facecolor("#16213e")
        labels = ["BUY", "SELL", "HOLD"]
        vals   = [counts.get(l, 0) for l in labels]
        bars   = ax_count.bar(labels, vals,
                              color=[sig_clrs[l] for l in labels],
                              alpha=0.85, width=0.5)
        for bar, val in zip(bars, vals):
            if val:
                ax_count.text(bar.get_x() + bar.get_width() / 2,
                              bar.get_height() + 0.1, str(val),
                              ha="center", va="bottom",
                              fontsize=12, fontweight="bold", color="white")
        ax_count.set_title("Signal Counts", color="white", fontsize=10)
        ax_count.tick_params(colors="white")
        ax_count.spines[:].set_edgecolor("#334155")
        ax_count.grid(True, alpha=0.15, color="white", axis="y")

        # Right: confidence scatter over time
        ax_timeline.set_facecolor("#16213e")
        ax_timeline.set_title("Confidence over Time", color="white", fontsize=10)
        try:
            dates = [datetime.fromisoformat(str(r["signal_date"])[:19])
                     for r in reversed(history)]
            confs = [float(r["confidence"]) * 100 if r["confidence"] <= 1
                     else float(r["confidence"])
                     for r in reversed(history)]
            clrs  = [sig_clrs.get(r["signal_type"], "#94a3b8")
                     for r in reversed(history)]
            ax_timeline.scatter(dates, confs, c=clrs, s=70, zorder=3, edgecolors="white",
                                linewidths=0.5)
            ax_timeline.plot(dates, confs, color="#475569", linewidth=1, zorder=2)
            ax_timeline.set_ylim(0, 105)
            ax_timeline.set_ylabel("Confidence %", color="white", fontsize=9)
            ax_timeline.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            fig.autofmt_xdate(rotation=30)
        except Exception:
            ax_timeline.text(0.5, 0.5, "Insufficient data",
                             ha="center", va="center", color="#94a3b8",
                             transform=ax_timeline.transAxes)
        ax_timeline.tick_params(colors="white")
        ax_timeline.spines[:].set_edgecolor("#334155")
        ax_timeline.grid(True, alpha=0.15, color="white")

        path = str(REPORTS_DIR / f"{symbol}_history_{_ts()}.png")
        fig.savefig(path, dpi=120, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        return path


def _ts() -> str:
    """Timestamp with microseconds so rapid batch runs never share a filename."""
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

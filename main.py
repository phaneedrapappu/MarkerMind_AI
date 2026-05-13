"""
MarketMind AI - Main Entry Point
A financial intelligence agent system for retail investors
"""
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for credentials (SMTP_USER, SMTP_PASSWORD, OPENAI_API_KEY)
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator import AgentOrchestrator

_STAGE_LABELS = {
    "market_data_agent": "Market Data Agent",
    "news_agent": "News Agent",
    "ai_analysis_agent": "AI Analysis Agent",
    "signal_generator_agent": "Signal Generator Agent",
    "report_generator_agent": "Report Generator Agent",
    "email_alert_agent": "Email Alert Agent",
}

# Popular NSE stocks grouped by sector for easy discovery
_NSE_STOCK_CATALOG = {
    "IT": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "OFSS"],
    "Banking": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB"],
    "Finance": ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "LICHSGFIN", "RECLTD", "PFC"],
    "Auto": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR", "ASHOKLEY"],
    "Pharma": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "TORNTPHARM", "ALKEM", "BIOCON"],
    "FMCG": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR", "MARICO", "COLPAL", "GODREJCP"],
    "Energy": ["RELIANCE", "ONGC", "NTPC", "POWERGRID", "ADANIGREEN", "TATAPOWER", "ADANIPORTS", "COALINDIA"],
    "Retail/Consumer": ["DMART", "TITAN", "TRENT", "NYKAA", "ZOMATO", "PAYTM", "NAUKRI", "IRCTC"],
    "Metals": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL", "NMDC", "NATIONALUM"],
    "Infra/Cement": ["ULTRACEMCO", "GRASIM", "AMBUJACEM", "ACC", "SHREECEM", "DALMIACEMX", "LT", "SIEMENS"],
}


def _search_stocks(keyword: str) -> None:
    """Search stocks by name or sector keyword."""
    kw = keyword.strip().upper()
    print(f"\n🔍  Searching for stocks matching '{keyword}':\n")

    # Search sector names
    found_sectors = {s: tickers for s, tickers in _NSE_STOCK_CATALOG.items()
                     if kw in s.upper()}
    # Search ticker names
    found_tickers = []
    for sector, tickers in _NSE_STOCK_CATALOG.items():
        for t in tickers:
            if kw in t:
                found_tickers.append((t, sector))

    if found_sectors:
        for sector, tickers in found_sectors.items():
            print(f"  📂 {sector}: {', '.join(tickers)}")
    if found_tickers:
        for ticker, sector in found_tickers:
            print(f"  📈 {ticker}  ({sector})")
    if not found_sectors and not found_tickers:
        # Try live yfinance search
        try:
            import yfinance as yf
            # yfinance 0.2+ has Search
            results = yf.Search(keyword, max_results=10).quotes
            if results:
                print("  Live yfinance results:")
                for r in results:
                    sym = r.get("symbol", "")
                    name = r.get("longname") or r.get("shortname", "")
                    exch = r.get("exchange", "")
                    if sym:
                        # Strip .NS suffix for NSE display
                        nsym = sym.replace(".NS", "")
                        print(f"  📈 {nsym:15s} {name}  [{exch}]")
            else:
                print("  No matches found.")
        except Exception:
            print("  No matches found in catalog. Try a sector name or stock symbol.")
    print()


def _list_stocks() -> None:
    """Print the full stock catalog grouped by sector."""
    print("\n📋  Available NSE Stocks by Sector:\n")
    for sector, tickers in _NSE_STOCK_CATALOG.items():
        print(f"  📂 {sector}")
        print(f"     {', '.join(tickers)}")
    print()
    print("Usage: python3 main.py --stocks TCS,INFY,HDFC --email you@gmail.com\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MarketMind AI – Financial Intelligence Agent System",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  python3 main.py
  python3 main.py --stocks TCS,INFY,HDFCBANK --email you@gmail.com
  python3 main.py --stocks RELIANCE,ONGC --email a@x.com,b@x.com --schedule
  python3 main.py --list-stocks
  python3 main.py --search-stocks banking
"""
    )
    parser.add_argument(
        "--config", type=str, default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--stocks", type=str, default=None,
        metavar="SYM1,SYM2,...",
        help="Comma-separated NSE stock symbols to analyse (overrides config.yaml)"
    )
    parser.add_argument(
        "--email", type=str, default=None,
        metavar="EMAIL1,EMAIL2,...",
        help="Comma-separated recipient email addresses (overrides config.yaml)"
    )
    parser.add_argument(
        "--run-once", action="store_true",
        help="Run once and exit (default behaviour)"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run on a repeating schedule defined in config.yaml"
    )
    parser.add_argument(
        "--list-stocks", action="store_true",
        help="List all available NSE stocks grouped by sector and exit"
    )
    parser.add_argument(
        "--search-stocks", type=str, default=None,
        metavar="KEYWORD",
        help="Search for NSE stocks by name or sector keyword and exit"
    )
    args = parser.parse_args()

    # ── Informational commands (no pipeline needed) ────────────────────────────
    if args.list_stocks:
        _list_stocks()
        return

    if args.search_stocks:
        _search_stocks(args.search_stocks)
        return

    print("=" * 70)
    print(" " * 12 + "🤖  MarketMind AI – Financial Intelligence Agent")
    print("=" * 70)
    print()

    # ── Build runtime overrides from CLI ───────────────────────────────────────
    overrides = {}
    if args.stocks:
        stocks = [s.strip().upper() for s in args.stocks.split(",") if s.strip()]
        overrides["stocks"] = stocks
        print(f"📈 Tracking stocks : {', '.join(stocks)}")

    if args.email:
        recipients = [e.strip() for e in args.email.split(",") if e.strip()]
        overrides["recipients"] = recipients
        print(f"📧 Sending report to: {', '.join(recipients)}")

    if overrides:
        print()

    orchestrator = AgentOrchestrator(args.config)
    orchestrator.apply_overrides(overrides)
    orchestrator.initialize_agents()

    def run_once():
        print("\n🚀 Starting agent pipeline …\n")
        results = orchestrator.run_agents()

        print("\n" + "=" * 70)
        print(" " * 22 + "📊 Execution Summary")
        print("=" * 70)
        for agent_key, label in _STAGE_LABELS.items():
            if agent_key not in results:
                continue
            r = results[agent_key]
            status = r.get("status", "unknown")
            if status == "success":
                extras = ""
                if "data_count" in r:
                    extras = f"– {r['data_count']} stock(s)"
                elif "article_count" in r:
                    extras = f"– {r['article_count']} article(s)"
                elif "analysis_count" in r:
                    extras = f"– {r['analysis_count']} report(s)"
                elif "signal_count" in r:
                    extras = f"– {r['signal_count']} signal(s)"
                elif "chart_count" in r:
                    extras = f"– {r['chart_count']} chart(s)"
                elif "recipients" in r:
                    extras = f"– sent to {', '.join(r['recipients'])}"
                print(f"  ✅ {label}: SUCCESS {extras}")
            elif status == "skipped":
                print(f"  ⏭️  {label}: SKIPPED – {r.get('reason', '')}")
            else:
                print(f"  ❌ {label}: FAILED – {r.get('error', 'unknown error')}")
        print("=" * 70 + "\n")

    if args.schedule:
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            interval_min = (
                orchestrator.config.get("scheduler", {}).get("run_interval_minutes", 30)
            )
            scheduler = BlockingScheduler()
            scheduler.add_job(run_once, "interval", minutes=interval_min)
            print(f"⏰ Scheduler started – running every {interval_min} minutes. Ctrl+C to stop.\n")
            run_once()   # Run immediately on start
            scheduler.start()
        except KeyboardInterrupt:
            print("\n⚠️  Scheduler stopped.")
    else:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user.")
        finally:
            orchestrator.stop_agents()

    print("✅ MarketMind AI finished.\n")


if __name__ == "__main__":
    main()

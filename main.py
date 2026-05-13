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

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MarketMind AI – Financial Intelligence Agent System"
    )
    parser.add_argument(
        "--config", type=str, default="config/config.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--run-once", action="store_true",
        help="Run once and exit (default: run once)"
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Run on a repeating schedule defined in config.yaml"
    )
    args = parser.parse_args()

    print("=" * 70)
    print(" " * 12 + "🤖  MarketMind AI – Financial Intelligence Agent")
    print("=" * 70)
    print()

    orchestrator = AgentOrchestrator(args.config)
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

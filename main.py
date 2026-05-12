"""
MarketMind AI - Main Entry Point
A financial intelligence agent system for retail investors
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator import AgentOrchestrator


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MarketMind AI - Financial Intelligence Agent System'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run agents once and exit (default: continuous mode)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print(" "*15 + "🤖 MarketMind AI - Financial Intelligence Agent")
    print("="*70)
    print()
    
    try:
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(args.config)
        
        # Initialize agents
        orchestrator.initialize_agents()
        
        # Run agents
        print("\n🚀 Starting agent execution...\n")
        results = orchestrator.run_agents()
        
        # Print summary
        print("\n" + "="*70)
        print(" "*20 + "📊 Execution Summary")
        print("="*70)
        
        for agent_name, result in results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                if agent_name == 'market_data_agent':
                    data_count = result.get('data_count', 0)
                    print(f"✅ Market Data Agent: SUCCESS - Collected {data_count} stock(s)")
                elif agent_name == 'ai_analysis_agent':
                    analysis_count = result.get('analysis_count', 0)
                    print(f"🤖 AI Analysis Agent: SUCCESS - Generated {analysis_count} analysis report(s)")
                elif agent_name == 'signal_generator_agent':
                    signal_count = result.get('signal_count', 0)
                    print(f"🎯 Signal Generator Agent: SUCCESS - Generated {signal_count} trading signal(s)")
                else:
                    print(f"✅ {agent_name}: SUCCESS")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ {agent_name}: FAILED - {error}")
        
        print("="*70 + "\n")
        
        # Stop agents
        orchestrator.stop_agents()
        
        print("✅ MarketMind AI execution completed successfully!\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user. Shutting down gracefully...")
        orchestrator.stop_agents()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

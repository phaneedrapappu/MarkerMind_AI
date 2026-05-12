"""
Agent Orchestrator - Manages and coordinates all agents
"""
import logging
import yaml
from typing import Dict, List, Any
from pathlib import Path

from .agents.market_data_agent import MarketDataAgent
from .agents.ai_analysis_agent import AIAnalysisAgent
from .agents.signal_generator_agent import SignalGeneratorAgent


class AgentOrchestrator:
    """
    Orchestrator for managing multiple agents in the MarketMind AI ecosystem
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the orchestrator
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.agents: Dict[str, Any] = {}
        self.logger = logging.getLogger("MarketMindAI.Orchestrator")
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return {}
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        log_file = log_config.get('file', 'logs/marketmind.log')
        
        # Create logs directory if it doesn't exist
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger.info("Logging configured")
    
    def initialize_agents(self):
        """Initialize all enabled agents"""
        self._setup_logging()
        self.logger.info("Initializing agents...")
        
        agent_configs = self.config.get('agents', {})
        
        # Initialize Market Data Agent
        market_data_config = agent_configs.get('market_data_agent', {})
        if market_data_config.get('enabled', False):
            self.logger.info("Initializing Market Data Agent")
            agent = MarketDataAgent(market_data_config)
            if agent.initialize():
                self.agents['market_data_agent'] = agent
                self.logger.info("Market Data Agent initialized successfully")
            else:
                self.logger.error("Failed to initialize Market Data Agent")
        
        # Initialize AI Analysis Agent
        ai_analysis_config = agent_configs.get('ai_analysis_agent', {})
        if ai_analysis_config.get('enabled', False):
            self.logger.info("Initializing AI Analysis Agent")
            agent = AIAnalysisAgent(ai_analysis_config)
            if agent.initialize():
                self.agents['ai_analysis_agent'] = agent
                self.logger.info("AI Analysis Agent initialized successfully")
            else:
                self.logger.error("Failed to initialize AI Analysis Agent")
        
        # Initialize Signal Generator Agent
        signal_generator_config = agent_configs.get('signal_generator_agent', {})
        if signal_generator_config.get('enabled', False):
            self.logger.info("Initializing Signal Generator Agent")
            agent = SignalGeneratorAgent(signal_generator_config)
            if agent.initialize():
                self.agents['signal_generator_agent'] = agent
                self.logger.info("Signal Generator Agent initialized successfully")
            else:
                self.logger.error("Failed to initialize Signal Generator Agent")
        
        self.logger.info(f"Initialized {len(self.agents)} agent(s)")
    
    def run_agents(self):
        """Run all agents in coordinated sequence"""
        self.logger.info("Running all agents...")
        
        results = {}
        
        # Step 1: Run Market Data Agent
        market_data = []
        if 'market_data_agent' in self.agents:
            self.logger.info("Step 1/3: Executing Market Data Agent")
            agent = self.agents['market_data_agent']
            agent.start()
            
            try:
                market_data = agent.execute()
                results['market_data_agent'] = {
                    'status': 'success',
                    'data_count': len(market_data),
                    'data': market_data
                }
                self.logger.info(f"Market Data Agent completed - collected {len(market_data)} snapshots")
            except Exception as e:
                self.logger.error(f"Error executing Market Data Agent: {e}")
                results['market_data_agent'] = {
                    'status': 'error',
                    'error': str(e)
                }
                return results  # Stop if market data fails
        
        # Step 2: Run AI Analysis Agent (if market data was collected)
        analysis_reports = []
        if market_data and 'ai_analysis_agent' in self.agents:
            self.logger.info("Step 2/3: Executing AI Analysis Agent")
            agent = self.agents['ai_analysis_agent']
            agent.start()
            
            try:
                analysis_reports = agent.execute(market_data)
                results['ai_analysis_agent'] = {
                    'status': 'success',
                    'analysis_count': len(analysis_reports),
                    'reports': analysis_reports
                }
                self.logger.info(f"AI Analysis Agent completed - generated {len(analysis_reports)} analysis reports")
            except Exception as e:
                self.logger.error(f"Error executing AI Analysis Agent: {e}")
                results['ai_analysis_agent'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Step 3: Run Signal Generator Agent (if analysis was completed)
        signals = []
        if analysis_reports and 'signal_generator_agent' in self.agents:
            self.logger.info("Step 3/3: Executing Signal Generator Agent")
            agent = self.agents['signal_generator_agent']
            agent.start()
            
            try:
                signals = agent.execute(analysis_reports)
                results['signal_generator_agent'] = {
                    'status': 'success',
                    'signal_count': len(signals),
                    'signals': signals
                }
                self.logger.info(f"Signal Generator Agent completed - generated {len(signals)} trading signals")
            except Exception as e:
                self.logger.error(f"Error executing Signal Generator Agent: {e}")
                results['signal_generator_agent'] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
    
    def stop_agents(self):
        """Stop all agents"""
        self.logger.info("Stopping all agents...")
        
        for name, agent in self.agents.items():
            try:
                agent.stop()
                self.logger.info(f"Stopped {name}")
            except Exception as e:
                self.logger.error(f"Error stopping {name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {}
        for name, agent in self.agents.items():
            status[name] = agent.get_status()
        return status

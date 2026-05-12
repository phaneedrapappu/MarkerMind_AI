"""
Base Agent class for all agents in the MarketMind AI ecosystem
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize the base agent
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"MarketMindAI.{name}")
        self.is_running = False
        self.last_run = None
        
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the agent (setup connections, load models, etc.)
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def execute(self) -> Any:
        """
        Execute the agent's main task
        
        Returns:
            Result of the execution
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """
        Cleanup resources (close connections, save state, etc.)
        """
        pass
    
    def start(self):
        """Start the agent"""
        self.logger.info(f"Starting agent: {self.name}")
        self.is_running = True
        
    def stop(self):
        """Stop the agent"""
        self.logger.info(f"Stopping agent: {self.name}")
        self.is_running = False
        self.cleanup()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get agent status
        
        Returns:
            Status dictionary
        """
        return {
            'name': self.name,
            'is_running': self.is_running,
            'last_run': self.last_run.isoformat() if self.last_run else None
        }
    
    def log_execution(self):
        """Log execution timestamp"""
        self.last_run = datetime.now()
        self.logger.debug(f"Agent {self.name} executed at {self.last_run}")

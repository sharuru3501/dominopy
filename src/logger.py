"""
Logging configuration for PyDomino
Provides centralized logging system to replace debug print statements
"""
import logging
import os
from typing import Optional

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting across the application
    
    Args:
        name: Logger name (usually __name__)
        level: Log level override (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set default level from environment or INFO
    if level is None:
        level = os.getenv('PYDOMINO_LOG_LEVEL', 'INFO')
    
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Convenience function for quick logger creation
def get_logger(name: str) -> logging.Logger:
    """Get a logger with standard configuration"""
    return setup_logger(name)
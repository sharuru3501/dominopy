"""
Logging system for DominoPy
Provides centralized logging with configurable levels
"""
import logging
import os
import sys
from typing import Optional

# Configure logging levels based on environment
DEBUG_MODE = os.getenv('PYDOMINO_DEBUG', 'false').lower() in ('true', '1', 'yes')
LOG_LEVEL = os.getenv('PYDOMINO_LOG_LEVEL', 'INFO' if not DEBUG_MODE else 'DEBUG')

# Create root logger
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module name"""
    logger = logging.getLogger(name)
    
    # Set level based on environment
    if DEBUG_MODE:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    return logger

def set_debug_mode(enabled: bool):
    """Enable or disable debug mode globally"""
    global DEBUG_MODE
    DEBUG_MODE = enabled
    
    # Update all existing loggers
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        if enabled:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

# Legacy print replacement - can be used to quickly replace print() calls
def print_debug(*args, **kwargs):
    """Replacement for print() - only shows in debug mode"""
    if DEBUG_MODE:
        print(*args, **kwargs)

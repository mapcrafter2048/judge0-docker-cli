"""Utility functions for Judge0 Docker CLI."""

import logging
import sys
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Create console handler
        handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def format_execution_time(time_ms: Optional[int]) -> str:
    """Format execution time in human-readable format."""
    if time_ms is None:
        return "N/A"
    
    if time_ms < 1000:
        return f"{time_ms}ms"
    else:
        return f"{time_ms / 1000:.2f}s"


def format_memory_usage(memory_kb: Optional[int]) -> str:
    """Format memory usage in human-readable format."""
    if memory_kb is None:
        return "N/A"
    
    if memory_kb < 1024:
        return f"{memory_kb}KB"
    else:
        return f"{memory_kb / 1024:.2f}MB"
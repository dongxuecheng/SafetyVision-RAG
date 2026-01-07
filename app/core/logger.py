"""
Centralized logging configuration using loguru
"""

import sys
from pathlib import Path
from loguru import logger
from app.core.config import get_settings


def setup_logger():
    """
    Configure loguru logger with settings from config
    
    - Removes default handler
    - Adds console handler with color formatting
    - Adds file handler with rotation and retention
    """
    settings = get_settings()
    
    # Remove default handler
    logger.remove()
    
    # Add console handler (stdout) with color formatting
    logger.add(
        sys.stdout,
        format=settings.log_format,
        level=settings.log_level,
        colorize=True,
    )
    
    # Ensure log directory exists
    log_file = Path(settings.log_file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Add file handler with rotation and retention
    logger.add(
        settings.log_file_path,
        format=settings.log_format,
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",  # Compress rotated logs
        encoding="utf-8",
    )
    
    logger.info(f"Logger initialized - Level: {settings.log_level}, File: {settings.log_file_path}")
    logger.info(f"Deployment mode: {settings.deployment_mode}")
    
    return logger


# Initialize logger on import
setup_logger()

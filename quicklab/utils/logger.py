"""Logging utilities for QuickLab."""

import logging
import sys
from typing import Optional
from pathlib import Path


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a configured logger for QuickLab.
    
    Parameters
    ----------
    name : str
        Name of the logger (typically __name__).
    level : int, optional
        Logging level. If None, uses INFO for main modules and WARNING for others.
        
    Returns
    -------
    logging.Logger
        Configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set default level
    if level is None:
        if name.startswith('quicklab.'):
            level = logging.INFO
        else:
            level = logging.WARNING
    
    logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def setup_file_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """Set up file logging for QuickLab.
    
    Parameters
    ----------
    log_dir : Path
        Directory to store log files.
    level : int, optional
        Logging level for file logging. Default is INFO.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    
    # Create file handler
    log_file = log_dir / "quicklab.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger('quicklab')
    root_logger.addHandler(file_handler)
    root_logger.setLevel(level)
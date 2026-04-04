import logging
import sys
import os
from pathlib import Path

def setup_logger(name: str):
    """Setup logger with absolute path for log files."""
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler - output to stderr instead of stdout for MCP compatibility
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler with absolute path
    try:
        # Get absolute path to project root
        project_root = Path(__file__).resolve().parents[2]
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        fh = logging.FileHandler(logs_dir / f"{name}.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception:
        # If file logging fails, just use console
        pass
    
    return logger

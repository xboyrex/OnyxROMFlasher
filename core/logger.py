import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(logs_dir: Path) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        logs_dir: Directory to store log files
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("onyx_flasher")
    logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler - rotate when file reaches 5MB
    log_filename = logs_dir / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler - only INFO and above
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

class LogCapture:
    """Capture logs for display in UI"""
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.messages = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message"""
        self.messages.append(message)
        getattr(self.logger, level.lower())(message)
    
    def debug(self, message: str):
        self.log(message, "DEBUG")
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def warning(self, message: str):
        self.log(message, "WARNING")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def critical(self, message: str):
        self.log(message, "CRITICAL")
    
    def get_all(self) -> str:
        """Get all captured messages as string"""
        return "\n".join(self.messages)
    
    def clear(self):
        """Clear captured messages"""
        self.messages = []

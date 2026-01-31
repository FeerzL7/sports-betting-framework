"""
Centralized Logging System

FEATURES:
- Console + file logging with rotation
- Colored console output (optional)
- Structured logging with context
- Per-module loggers
- Performance tracking
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

USAGE:
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing game", game_id="123", league="PL")
    logger.warning("Low confidence", confidence=0.45)
    logger.error("API failed", error=str(e))

CONFIGURATION:
    - Logs to console (colored)
    - Logs to file: logs/app.log (with rotation)
    - File format: timestamp | level | module | message
    - Console format: level | module | message (colored)
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime


# ============================================================================
# CONFIGURATION
# ============================================================================

# Log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log files
MAIN_LOG_FILE = LOG_DIR / "app.log"
ERROR_LOG_FILE = LOG_DIR / "errors.log"

# Log levels
DEFAULT_LEVEL = logging.INFO
FILE_LEVEL = logging.DEBUG  # File gets more detail
CONSOLE_LEVEL = logging.INFO

# Rotation
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5  # Keep 5 backup files

# Format strings
FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
CONSOLE_FORMAT = "%(levelname)-8s | %(name)-30s | %(message)s"

# Date format
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================================
# COLOR CODES (for console)
# ============================================================================

class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Levels
    DEBUG = "\033[36m"      # Cyan
    INFO = "\033[32m"       # Green
    WARNING = "\033[33m"    # Yellow
    ERROR = "\033[31m"      # Red
    CRITICAL = "\033[35m"   # Magenta
    
    # Components
    TIMESTAMP = "\033[90m"  # Gray
    MODULE = "\033[94m"     # Light Blue


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter with colors for console output
    
    Only adds colors to console, not to file logs
    """
    
    COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }
    
    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if record.levelno in self.COLORS:
            colored_level = f"{self.COLORS[record.levelno]}{levelname}{Colors.RESET}"
            record.levelname = colored_level
        
        # Format the message
        result = super().format(record)
        
        # Reset levelname for other handlers
        record.levelname = levelname
        
        return result


# ============================================================================
# LOGGER SETUP
# ============================================================================

def setup_logger(
    name: str,
    level: int = DEFAULT_LEVEL,
    log_file: Optional[Path] = None,
    console: bool = True,
    colors: bool = True
) -> logging.Logger:
    """
    Create and configure a logger
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = use default)
        console: Whether to log to console
        colors: Whether to use colors in console (Windows may need colorama)
    
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Starting analysis")
        INFO     | my_module | Starting analysis
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # ========================================================================
    # CONSOLE HANDLER
    # ========================================================================
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(CONSOLE_LEVEL)
        
        if colors:
            console_formatter = ColoredFormatter(CONSOLE_FORMAT)
        else:
            console_formatter = logging.Formatter(CONSOLE_FORMAT)
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # ========================================================================
    # FILE HANDLER (with rotation)
    # ========================================================================
    if log_file is None:
        log_file = MAIN_LOG_FILE
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(FILE_LEVEL)
    file_formatter = logging.Formatter(FILE_FORMAT, datefmt=DATE_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # ========================================================================
    # ERROR FILE HANDLER (errors only)
    # ========================================================================
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger with default configuration
    
    This is the main function to use throughout the codebase.
    
    Args:
        name: Logger name (use __name__ in modules)
    
    Returns:
        Configured logger
    
    Example:
        # In your module
        from utils.logger import get_logger
        
        logger = get_logger(__name__)
        logger.info("Module started")
    """
    return setup_logger(name)


# ============================================================================
# STRUCTURED LOGGING HELPERS
# ============================================================================

class LogContext:
    """
    Context manager for structured logging
    
    Adds context to all log messages within the block.
    
    Usage:
        with LogContext(logger, game_id="123", league="PL"):
            logger.info("Processing game")
            # Logs: "Processing game | game_id=123 league=PL"
    """
    
    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.original_factory = None
    
    def __enter__(self):
        # Save original record factory
        self.original_factory = logging.getLogRecordFactory()
        
        # Create new factory that adds context
        context = self.context
        
        def record_factory(*args, **kwargs):
            record = self.original_factory(*args, **kwargs)
            # Add context to message
            if context:
                context_str = " | ".join(f"{k}={v}" for k, v in context.items())
                record.msg = f"{record.msg} | {context_str}"
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, *args):
        # Restore original factory
        logging.setLogRecordFactory(self.original_factory)


def log_execution_time(logger: logging.Logger, operation: str):
    """
    Decorator to log execution time of functions
    
    Usage:
        @log_execution_time(logger, "xG calculation")
        def calculate_xg(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = datetime.now()
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start).total_seconds()
                logger.debug(
                    f"{operation} completed",
                    extra={"duration": f"{duration:.3f}s"}
                )
                return result
            except Exception as e:
                duration = (datetime.now() - start).total_seconds()
                logger.error(
                    f"{operation} failed after {duration:.3f}s",
                    extra={"error": str(e)}
                )
                raise
        return wrapper
    return decorator


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

class PerformanceLogger:
    """
    Track performance metrics for operations
    
    Usage:
        perf = PerformanceLogger(logger, "API Fetch")
        
        with perf.track():
            # Do work
            pass
        
        # Automatically logs duration
    """
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def track(self):
        """Context manager for tracking"""
        return self
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"{self.operation} started")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"{self.operation} failed after {duration:.3f}s",
                extra={"error": str(exc_val)}
            )
        else:
            self.logger.info(f"{self.operation} completed in {duration:.3f}s")
        
        return False  # Don't suppress exceptions


# ============================================================================
# SYSTEM LOGGER
# ============================================================================

# Create a system-wide logger for framework messages
system_logger = get_logger("betting_system")


def log_startup():
    """Log system startup information"""
    system_logger.info("="*80)
    system_logger.info("BETTING SYSTEM STARTING")
    system_logger.info("="*80)
    system_logger.info(f"Log directory: {LOG_DIR.absolute()}")
    system_logger.info(f"Main log: {MAIN_LOG_FILE.name}")
    system_logger.info(f"Error log: {ERROR_LOG_FILE.name}")
    system_logger.info("="*80)


def log_shutdown():
    """Log system shutdown"""
    system_logger.info("="*80)
    system_logger.info("BETTING SYSTEM SHUTTING DOWN")
    system_logger.info("="*80)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Test the logging system"""
    
    print("Testing logging system...\n")
    
    # Create test logger
    test_logger = get_logger("test_module")
    
    # Test all levels
    test_logger.debug("This is a DEBUG message")
    test_logger.info("This is an INFO message")
    test_logger.warning("This is a WARNING message")
    test_logger.error("This is an ERROR message")
    test_logger.critical("This is a CRITICAL message")
    
    print()
    
    # Test structured logging
    test_logger.info("Processing game", extra={"game_id": "123", "league": "PL"})
    
    # Test context manager
    with LogContext(test_logger, game_id="456", team="Real Madrid"):
        test_logger.info("Calculating xG")
        test_logger.warning("Low confidence")
    
    # Test performance tracking
    perf = PerformanceLogger(test_logger, "Test Operation")
    with perf.track():
        import time
        time.sleep(0.1)
    
    print(f"\n✅ Logging tests completed")
    print(f"Check logs at: {MAIN_LOG_FILE.absolute()}")
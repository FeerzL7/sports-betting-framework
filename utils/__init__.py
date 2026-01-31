"""
Utils Package - Shared Utilities

MODULES:
- logger: Centralized logging system
- exceptions: Custom exception hierarchy

USAGE:
    from utils import get_logger, DataFetchError
    
    logger = get_logger(__name__)
    
    try:
        data = fetch_data()
    except DataFetchError as e:
        logger.error("Fetch failed", extra={"error": str(e)})
"""

from utils.logger import (
    get_logger,
    setup_logger,
    LogContext,
    PerformanceLogger,
    log_execution_time,
    log_startup,
    log_shutdown
)

from utils.exceptions import (
    # Base
    BettingSystemError,
    
    # Data errors
    DataError,
    DataFetchError,
    DataValidationError,
    InsufficientDataError,
    
    # Config errors
    ConfigurationError,
    InvalidConfigError,
    MissingConfigError,
    
    # Analysis errors
    AnalysisError,
    ModelError,
    CalculationError,
    
    # API errors
    APIError,
    RateLimitError,
    AuthenticationError,
    APIResponseError,
    
    # Helpers
    validate_or_raise,
    ErrorContext
)

__all__ = [
    # Logging
    'get_logger',
    'setup_logger',
    'LogContext',
    'PerformanceLogger',
    'log_execution_time',
    'log_startup',
    'log_shutdown',
    
    # Exceptions - Base
    'BettingSystemError',
    
    # Exceptions - Data
    'DataError',
    'DataFetchError',
    'DataValidationError',
    'InsufficientDataError',
    
    # Exceptions - Config
    'ConfigurationError',
    'InvalidConfigError',
    'MissingConfigError',
    
    # Exceptions - Analysis
    'AnalysisError',
    'ModelError',
    'CalculationError',
    
    # Exceptions - API
    'APIError',
    'RateLimitError',
    'AuthenticationError',
    'APIResponseError',
    
    # Helpers
    'validate_or_raise',
    'ErrorContext'
]
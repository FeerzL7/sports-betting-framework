"""
Custom Exceptions - Hierarchical Error Types

PHILOSOPHY:
- Specific exceptions for different failure modes
- Clear error messages with context
- Easy to catch and handle granularly
- Helps with debugging and monitoring

HIERARCHY:
    BettingSystemError (base)
    ├── DataError
    │   ├── DataFetchError
    │   ├── DataValidationError
    │   └── InsufficientDataError
    ├── ConfigurationError
    │   ├── InvalidConfigError
    │   └── MissingConfigError
    ├── AnalysisError
    │   ├── ModelError
    │   └── CalculationError
    └── APIError
        ├── RateLimitError
        ├── AuthenticationError
        └── APIResponseError

USAGE:
    from utils.exceptions import DataFetchError
    
    if not data:
        raise DataFetchError(
            "Failed to fetch team stats",
            provider="api_football",
            team_id=123
        )
"""
import requests

class BettingSystemError(Exception):
    """
    Base exception for all betting system errors
    
    All custom exceptions inherit from this.
    Allows catching all system errors with one except clause.
    """
    
    def __init__(self, message: str, **context):
        """
        Args:
            message: Human-readable error description
            **context: Additional context (provider, team_id, etc.)
        """
        self.message = message
        self.context = context
        super().__init__(self.message)
    
    def __str__(self):
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


# ============================================================================
# DATA ERRORS - Problems fetching or processing data
# ============================================================================

class DataError(BettingSystemError):
    """Base class for data-related errors"""
    pass


class DataFetchError(DataError):
    """
    Failed to fetch data from external source
    
    Examples:
    - API timeout
    - API returns error
    - Network connection failed
    """
    pass


class DataValidationError(DataError):
    """
    Data validation failed
    
    Examples:
    - Probabilities don't sum to 1.0
    - Odds are negative
    - Missing required fields
    """
    pass


class InsufficientDataError(DataError):
    """
    Not enough data to perform analysis
    
    Examples:
    - Team has < 5 games played
    - No historical H2H data
    - Missing critical stats
    """
    pass


# ============================================================================
# CONFIGURATION ERRORS - Problems with system configuration
# ============================================================================

class ConfigurationError(BettingSystemError):
    """Base class for configuration errors"""
    pass


class InvalidConfigError(ConfigurationError):
    """
    Configuration values are invalid
    
    Examples:
    - Kelly fraction > 1.0
    - Negative risk limits
    - Invalid league code
    """
    pass


class MissingConfigError(ConfigurationError):
    """
    Required configuration is missing
    
    Examples:
    - API key not set
    - Required config parameter missing
    - League not in supported leagues
    """
    pass


# ============================================================================
# ANALYSIS ERRORS - Problems during game analysis
# ============================================================================

class AnalysisError(BettingSystemError):
    """Base class for analysis errors"""
    pass


class ModelError(AnalysisError):
    """
    Model calculation failed
    
    Examples:
    - xG calculation error
    - Probability conversion failed
    - Monte Carlo simulation error
    """
    pass


class CalculationError(AnalysisError):
    """
    Mathematical calculation failed
    
    Examples:
    - Division by zero
    - Invalid input to math function
    - Convergence failure
    """
    pass


# ============================================================================
# API ERRORS - Problems with external APIs
# ============================================================================

class APIError(BettingSystemError):
    """Base class for API-related errors"""
    pass


class RateLimitError(APIError):
    """
    API rate limit exceeded
    
    Should trigger exponential backoff or warning
    """
    pass


class AuthenticationError(APIError):
    """
    API authentication failed
    
    Examples:
    - Invalid API key
    - Expired token
    - Insufficient permissions
    """
    pass


class APIResponseError(APIError):
    """
    API returned unexpected response
    
    Examples:
    - Malformed JSON
    - Missing expected fields
    - HTTP error status
    """
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def validate_or_raise(condition: bool, error_class: type, message: str, **context):
    """
    Validate condition or raise specific exception
    
    Args:
        condition: Condition to check (should be True)
        error_class: Exception class to raise if False
        message: Error message
        **context: Additional context
    
    Example:
        >>> validate_or_raise(
        ...     odds > 1.0,
        ...     DataValidationError,
        ...     "Odds must be > 1.0",
        ...     odds=odds,
        ...     market="moneyline"
        ... )
    """
    if not condition:
        raise error_class(message, **context)


def wrap_api_errors(func):
    """
    Decorator to wrap API calls and convert to APIError
    
    Usage:
        @wrap_api_errors
        def fetch_data(self):
            response = requests.get(...)
            return response.json()
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            raise APIError(f"API timeout in {func.__name__}")
        except requests.exceptions.ConnectionError:
            raise APIError(f"Connection error in {func.__name__}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"Rate limit in {func.__name__}")
            elif e.response.status_code == 401:
                raise AuthenticationError(f"Auth failed in {func.__name__}")
            else:
                raise APIResponseError(f"HTTP {e.response.status_code} in {func.__name__}")
        except Exception as e:
            # Re-raise if already our exception
            if isinstance(e, BettingSystemError):
                raise
            # Wrap unknown exceptions
            raise APIError(f"Unexpected error in {func.__name__}: {e}")
    
    return wrapper


# ============================================================================
# ERROR CONTEXT HELPERS
# ============================================================================

class ErrorContext:
    """
    Context manager for adding context to exceptions
    
    Usage:
        with ErrorContext(game_id="123", team="Real Madrid"):
            calculate_xg(...)
        
        # If error occurs, context is automatically added
    """
    
    def __init__(self, **context):
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, BettingSystemError):
            # Add our context to the exception
            exc_val.context.update(self.context)
        return False  # Don't suppress the exception


# ============================================================================
# TESTING HELPERS
# ============================================================================

if __name__ == "__main__":
    """Self-test of exception hierarchy"""
    
    print("Testing exception hierarchy...\n")
    
    # Test basic exception
    try:
        raise BettingSystemError("Base error", component="test")
    except BettingSystemError as e:
        print(f"✅ BettingSystemError: {e}")
    
    # Test data error
    try:
        raise DataFetchError(
            "Failed to fetch odds",
            provider="odds_api",
            game_id="12345"
        )
    except DataError as e:
        print(f"✅ DataFetchError (caught as DataError): {e}")
    
    # Test validation helper
    try:
        odds = -1.5
        validate_or_raise(
            odds > 1.0,
            DataValidationError,
            "Odds must be positive",
            odds=odds
        )
    except DataValidationError as e:
        print(f"✅ validate_or_raise: {e}")
    
    # Test error context
    try:
        with ErrorContext(game_id="99", league="PL"):
            raise ModelError("xG calculation failed")
    except ModelError as e:
        print(f"✅ ErrorContext: {e}")
        print(f"   Context: {e.context}")
    
    print("\n✅ All exception tests passed")
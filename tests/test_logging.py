"""
Logging System Tests

EJECUTAR:
    python -m tests.test_logging
    
O desde raíz:
    python tests/test_logging.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils import (
    get_logger,
    LogContext,
    PerformanceLogger,
    DataFetchError,
    AuthenticationError,
    validate_or_raise,
    DataValidationError,
    log_startup,
    log_shutdown
)
import time


def test_basic_logging():
    """Test basic logging levels"""
    print("\n" + "="*60)
    print("TEST 1: Basic Logging Levels")
    print("="*60)
    
    logger = get_logger("test.basic")
    
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
    
    print("✅ All log levels tested")


def test_structured_logging():
    """Test structured logging with context"""
    print("\n" + "="*60)
    print("TEST 2: Structured Logging")
    print("="*60)
    
    logger = get_logger("test.structured")
    
    # Log with extra context
    logger.info(
        "Processing game",
        extra={
            "game_id": "123",
            "league": "PL",
            "teams": "Arsenal vs Chelsea"
        }
    )
    
    # Log with performance data
    logger.info(
        "API call completed",
        extra={
            "endpoint": "/fixtures",
            "duration": "0.245s",
            "status": 200
        }
    )
    
    print("✅ Structured logging tested")


def test_log_context():
    """Test LogContext manager"""
    print("\n" + "="*60)
    print("TEST 3: Log Context Manager")
    print("="*60)
    
    logger = get_logger("test.context")
    
    with LogContext(logger, game_id="456", league="PD"):
        logger.info("Starting analysis")
        logger.debug("Calculating xG")
        logger.warning("Low confidence detected")
    
    # Outside context - no extra fields
    logger.info("Analysis complete")
    
    print("✅ LogContext tested")


def test_performance_tracking():
    """Test PerformanceLogger"""
    print("\n" + "="*60)
    print("TEST 4: Performance Tracking")
    print("="*60)
    
    logger = get_logger("test.performance")
    
    perf = PerformanceLogger(logger, "xG Calculation")
    
    with perf.track():
        # Simulate work
        time.sleep(0.1)
    
    print("✅ Performance tracking tested")


def test_exception_logging():
    """Test logging with custom exceptions"""
    print("\n" + "="*60)
    print("TEST 5: Exception Logging")
    print("="*60)
    
    logger = get_logger("test.exceptions")
    
    # Test DataFetchError
    try:
        raise DataFetchError(
            "Failed to fetch odds",
            provider="odds_api",
            game_id="789"
        )
    except DataFetchError as e:
        logger.error(f"Data fetch failed: {e}", extra={"error_type": type(e).__name__})
    
    # Test AuthenticationError
    try:
        raise AuthenticationError(
            "Invalid API key",
            provider="api_football"
        )
    except AuthenticationError as e:
        logger.error(f"Auth error: {e}", extra={"error_type": type(e).__name__})
    
    # Test validate_or_raise
    try:
        odds = -1.5
        validate_or_raise(
            odds > 1.0,
            DataValidationError,
            "Odds must be > 1.0",
            odds=odds,
            market="moneyline"
        )
    except DataValidationError as e:
        logger.error(f"Validation failed: {e}", extra={"error_type": type(e).__name__})
    
    print("✅ Exception logging tested")


def test_real_world_scenario():
    """Test realistic usage scenario"""
    print("\n" + "="*60)
    print("TEST 6: Real-World Scenario")
    print("="*60)
    
    logger = get_logger("soccer.analysis")
    
    # Simulate analyzing a game
    logger.info("="*60)
    logger.info("Starting game analysis")
    logger.info("="*60)
    
    with LogContext(logger, game_id="PL_12345", league="Premier League"):
        logger.info("Fetching team stats")
        
        # Simulate API call
        perf = PerformanceLogger(logger, "API: Team Stats")
        with perf.track():
            time.sleep(0.05)
        
        logger.debug("Arsenal: 2.1 goals/game, Chelsea: 1.8 goals/game")
        
        logger.info("Calculating xG")
        logger.debug("Home xG: 1.85, Away xG: 1.42")
        
        logger.info("Calculating probabilities")
        logger.debug("Home: 45%, Draw: 28%, Away: 27%")
        
        logger.warning("Low confidence due to missing H2H data", extra={"confidence": 0.65})
        
        logger.info("Analysis complete")
    
    logger.info("="*60)
    
    print("✅ Real-world scenario tested")


def test_log_files_created():
    """Verify log files are created"""
    print("\n" + "="*60)
    print("TEST 7: Log Files Creation")
    print("="*60)
    
    logs_dir = Path("logs")
    
    if logs_dir.exists():
        print(f"✅ Logs directory exists: {logs_dir.absolute()}")
        
        app_log = logs_dir / "app.log"
        error_log = logs_dir / "errors.log"
        
        if app_log.exists():
            print(f"✅ Main log file: {app_log.name} ({app_log.stat().st_size} bytes)")
        else:
            print(f"⚠️  Main log file not created yet")
        
        if error_log.exists():
            print(f"✅ Error log file: {error_log.name} ({error_log.stat().st_size} bytes)")
        else:
            print(f"ℹ️  Error log file not created (no errors yet)")
    else:
        print(f"⚠️  Logs directory not found")


def run_all_tests():
    """Execute all logging tests"""
    print("\n" + "🧪 "*30)
    print("LOGGING SYSTEM TESTS")
    print("🧪 "*30)
    
    # System startup
    log_startup()
    
    try:
        test_basic_logging()
        test_structured_logging()
        test_log_context()
        test_performance_tracking()
        test_exception_logging()
        test_real_world_scenario()
        test_log_files_created()
        
        print("\n" + "="*60)
        print("✅ ALL LOGGING TESTS PASSED")
        print("="*60)
        
        # Show log location
        log_file = Path("logs/app.log")
        if log_file.exists():
            print(f"\nLog file location: {log_file.absolute()}")
            print("View logs with:")
            print(f"  Windows: type {log_file}")
            print(f"  Linux/Mac: cat {log_file}")
        
        print("\n" + "="*60)
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TESTS FAILED: {e}")
        print("="*60)
        raise
    finally:
        # System shutdown
        log_shutdown()


if __name__ == "__main__":
    run_all_tests()
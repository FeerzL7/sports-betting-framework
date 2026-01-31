"""
Configuration Validation Test

Verifica que todas las configuraciones sean válidas y consistentes.

EJECUTAR:
    python -m tests.test_config
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import (
    DEFAULT_KELLY_CONFIG,
    DEFAULT_RISK_CONFIG,
    DEFAULT_SOCCER_CONFIG,
    SUPPORTED_SOCCER_LEAGUES,
    API_KEYS,
    validate_api_keys
)
from config.core_config import validate_all_configs
from config.soccer_config import validate_soccer_config


def test_core_configs():
    """Test core configurations"""
    print("\n" + "="*60)
    print("TEST: Core Configurations")
    print("="*60)
    
    # Validate all predefined configs
    validate_all_configs()
    print("✅ All core configs validated")
    
    # Test Kelly config
    print(f"\nDefault Kelly Config:")
    print(f"  Fraction: {DEFAULT_KELLY_CONFIG.fraction} (Quarter Kelly)")
    print(f"  Max Stake: {DEFAULT_KELLY_CONFIG.max_stake_pct}%")
    print(f"  Min Edge: {DEFAULT_KELLY_CONFIG.min_edge:.2%}")
    
    # Test Risk config
    print(f"\nDefault Risk Config:")
    print(f"  Max Total Exposure: {DEFAULT_RISK_CONFIG.max_total_exposure}%")
    print(f"  Max Single Pick: {DEFAULT_RISK_CONFIG.max_single_pick}%")
    print(f"  Max Picks Per Game: {DEFAULT_RISK_CONFIG.max_picks_per_game}")


def test_soccer_configs():
    """Test soccer configurations"""
    print("\n" + "="*60)
    print("TEST: Soccer Configurations")
    print("="*60)
    
    validate_soccer_config()
    
    print(f"\nSupported Leagues: {len(SUPPORTED_SOCCER_LEAGUES)}")
    for code, league in SUPPORTED_SOCCER_LEAGUES.items():
        print(f"  {code}: {league.name:20s} (baseline: {league.baseline_goals} goals)")
    
    print(f"\nDefault Soccer Config:")
    print(f"  Form Window: {DEFAULT_SOCCER_CONFIG.form_window} games")
    print(f"  Home Advantage: {DEFAULT_SOCCER_CONFIG.home_advantage:.2f}x")
    print(f"  Max Score Simulation: {DEFAULT_SOCCER_CONFIG.max_score_simulation}")


def test_api_keys():
    """Test API keys configuration"""
    print("\n" + "="*60)
    print("TEST: API Keys Configuration")
    print("="*60)
    
    validation = validate_api_keys()
    
    for provider, status in validation.items():
        configured = "✅" if status["configured"] else "❌"
        status_text = status["status"].replace("_", " ").title()
        print(f"{configured} {provider:20s} - {status_text}")
    
    configured_count = sum(1 for s in validation.values() if s["configured"])
    total_count = len(validation)
    
    print(f"\nConfigured: {configured_count}/{total_count} providers")
    
    if configured_count < total_count:
        print("\n⚠️  Some providers need configuration")
        print("Run: python config/api_keys.py for setup instructions")


def test_imports():
    """Test that all modules can be imported"""
    print("\n" + "="*60)
    print("TEST: Module Imports")
    print("="*60)
    
    try:
        from config.soccer_config import get_league_baseline, get_home_advantage
        print("✅ Soccer config helpers imported")
        
        # Test helper functions
        baseline = get_league_baseline("PL")
        assert baseline == 2.72
        print(f"✅ get_league_baseline('PL') = {baseline}")
        
        home_adv = get_home_advantage("BL1")
        assert home_adv == 1.15
        print(f"✅ get_home_advantage('BL1') = {home_adv}")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        raise


def run_all_tests():
    """Execute all configuration tests"""
    print("\n" + "🧪 "*30)
    print("CONFIGURATION TESTS")
    print("🧪 "*30)
    
    try:
        test_core_configs()
        test_soccer_configs()
        test_api_keys()
        test_imports()
        
        print("\n" + "="*60)
        print("✅ ALL CONFIGURATION TESTS PASSED")
        print("="*60 + "\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TESTS FAILED: {e}")
        print("="*60 + "\n")
        raise


if __name__ == "__main__":
    run_all_tests()